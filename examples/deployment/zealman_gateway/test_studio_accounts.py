"""CPU-only transactional and HTTP authorization tests, no GPU/payment calls."""
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
import studio_accounts as module


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'password_hash', lambda password: 'test:' + password)
    monkeypatch.setattr(module, 'password_valid', lambda password, stored: stored == 'test:' + password)
    return module.Accounts(tmp_path)


def test_first_100_concurrent_registrations_and_no_recycled_slots(accounts):
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        users = list(pool.map(lambda n: accounts.register('member' + str(n), 'long-password-123'), range(105)))
    assert sorted(user['signup_seq'] for user in users) == list(range(1, 106))
    assert sum(user['credits'] == 1_000_000 for user in users) == 100
    assert sum(user['credits'] for user in users) == 100_000_000
    assert len(accounts.rows("SELECT * FROM ledger WHERE kind='signup_bonus'")) == 100
    with pytest.raises(module.HTTPException):
        accounts.register('MEMBER0', 'long-password-123')
    admin = accounts.register('operator', 'long-password-123', admin=True)
    assert admin['signup_seq'] is None and admin['credits'] == 0
    assert accounts.rows("SELECT value FROM counters WHERE name='registrations'")[0]['value'] == 105


def job_body(key='request-123'):
    return {'workflow_id': 'safe-h3', 'idempotency_key': key, 'prompt': 'A slow camera orbit', 'seconds': 5}


def test_atomic_debit_idempotency_and_single_refund(accounts):
    user = accounts.register('customer', 'long-password-123', admin=True)
    with accounts.transaction() as db:
        accounts.change(db, user['id'], 10, 'test', 'fund', 'Funding')
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        jobs = list(pool.map(lambda _: accounts.create_job(user, job_body(), {}, 5), range(10)))
    assert len({job['id'] for job in jobs}) == 1
    assert accounts.rows('SELECT credits FROM users WHERE id=?', (user['id'],))[0]['credits'] == 0
    with pytest.raises(module.HTTPException) as error:
        accounts.create_job(user, job_body('second-job'), {}, 1)
    assert error.value.status_code == 402
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(lambda _: accounts.finish(jobs[0]['id'], False), range(10)))
    assert accounts.rows('SELECT credits FROM users WHERE id=?', (user['id'],))[0]['credits'] == 10
    assert len(accounts.rows("SELECT * FROM ledger WHERE kind='refund'")) == 1
    changed = job_body(); changed['prompt'] = 'Other prompt'
    with pytest.raises(module.HTTPException) as error:
        accounts.create_job(user, changed, {}, 5)
    assert error.value.status_code == 409


def test_paid_order_once_and_duplicate_receipt_rolls_back(accounts):
    admin = accounts.register('operator', 'long-password-123', admin=True)
    user = accounts.register('customer', 'long-password-123', admin=True)
    with accounts.transaction() as db:
        for order_id in ('order1', 'order2'):
            db.execute("INSERT INTO orders(id,user_id,package,credits,price_cents,status,created_at) VALUES(?,?,'p100',100,950,'pending',1)", (order_id, user['id']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: accounts.confirm_order(admin, 'order1', 'bank-receipt-123'), range(8)))
    with pytest.raises(module.HTTPException):
        accounts.confirm_order(admin, 'order2', 'bank-receipt-123')
    assert accounts.rows('SELECT credits FROM users WHERE id=?', (user['id'],))[0]['credits'] == 100
    assert accounts.rows("SELECT status FROM orders WHERE id='order2'")[0]['status'] == 'pending'


def template():
    return {'id':'safe-h3','category':'H3视频','duration_key':'1:seconds','input_values':{'seconds':5,'prompt':'','ref_image_0':None},
            'workflow_template':{'1':{'class_type':'Pick','inputs':{'seconds':5,'prompt':'','ref_image_0':None}},
            '_api_config':{'enabledParams':{'1:seconds':True,'1:prompt':True,'1:ref_image_0':True},
                           'apiNames':{'1:seconds':'seconds','1:prompt':'prompt','1:ref_image_0':'ref_image_0'},'formValues':{}}}}


@pytest.fixture
def clients(accounts):
    path=accounts.root/'catalog.json';path.write_text(json.dumps([template()]))
    app=FastAPI()
    module.install(app,accounts.root,'http://unused',path,start_worker=False)
    one,two=TestClient(app),TestClient(app)
    for client,name in ((one,'member-one'),(two,'member-two')):
        response=client.post('/accounts/register',json={'username':name,'password':'long-password-123'})
        assert response.status_code==200
        client.headers['X-LichTV-CSRF']=response.json()['csrf']
    return one,two,app


def test_ownership_csrf_logout_and_raw_prompt_bypass(clients):
    one,two,app=clients
    job=one.post('/accounts/jobs',json=job_body()|{'workflow_id':'safe-h3'})
    assert job.status_code==200 and job.json()['cost']==10
    assert len(two.get('/accounts/jobs').json()['items'])==0
    assert two.post('/accounts/jobs/'+job.json()['id']+'/cancel',json={}).status_code==404
    assert two.get('/gateway/api/workflow/result?prompt_id='+job.json()['id']).status_code==404
    assert one.get('/accounts/admin').status_code==403
    assert one.post('/accounts/admin/orders/foo/confirm',json={'receipt':'fake','verified_received':True}).status_code==403
    assert one.post('/gateway/api/comfy/proxy/prompt',json={}).status_code==403
    assert one.post('/gateway/api/concurrent/generate',json={}).status_code==403
    assert one.post('/gateway/api/workflow/generate',json={'workflow_id':'safe-h3','workflow_template':{'malicious':True}}).status_code==422
    assert one.post('/accounts/jobs',json=job_body()|{'workflow_id':'safe-h3','seconds':1.5}).status_code==422
    token=one.headers.pop('X-LichTV-CSRF')
    assert one.post('/accounts/orders',json={'package_id':'p20'}).status_code==403
    one.headers['X-LichTV-CSRF']=token
    assert one.post('/accounts/orders',headers={'Origin':'https://evil.example'},json={'package_id':'p20'}).status_code==403
    assert one.post('/accounts/logout',json={}).status_code==200
    assert one.get('/accounts/me').status_code==401


def test_price_is_server_owned_and_no_automatic_topup(clients):
    one,_,app=clients
    start=one.get('/accounts/me').json()['user']['credits']
    assert one.post('/accounts/orders',json={'package_id':'p100','price_cents':1}).status_code==422
    for package in module.PACKAGES:
        response=one.post('/accounts/orders',json={'package_id':package['id']})
        assert response.status_code==200
        assert response.json()['price_cents']==package['price_cents']
        assert response.json()['credits']==package['credits']
        assert response.json()['status']=='pending'
    assert one.get('/accounts/me').json()['user']['credits']==start


def test_cancel_refunds_once_and_foreign_reference_rejected(clients):
    one,two,app=clients
    body=job_body()|{'workflow_id':'safe-h3'}
    job=one.post('/accounts/jobs',json=body).json()
    for _ in range(2):
        assert one.post('/accounts/jobs/'+job['id']+'/cancel',json={}).status_code==200
    assert one.get('/accounts/me').json()['user']['credits']==1_000_000
    body|={'idempotency_key':'other-request','image':'someone-else.png'}
    assert one.post('/accounts/jobs',json=body).status_code==403
    assert one.get('/accounts/media/'+'1'*32).status_code==404


def test_canonical_duration_overrides_template_and_input(accounts):
    path=accounts.root/'catalog.json';path.write_text(json.dumps([template()]))
    runtime=module.Runtime(accounts,'http://unused',path)
    user=accounts.register('customer','long-password-123')
    body=module.Generation(**job_body()|{'workflow_id':'safe-h3','seconds':7})
    payload,seconds=runtime.prepare(body,user)
    assert seconds==7
    assert payload['workflow_template']['1']['inputs']['seconds']==7
    assert payload['workflow_template']['_api_config']['formValues']['1:seconds']==7
    assert payload['input_values']['seconds']==7


def test_production_password_hash():
    value=module.password_hash('a-long-real-password')
    assert 'a-long-real-password' not in value
    assert module.password_valid('a-long-real-password',value)
    assert not module.password_valid('another-long-password',value)


def test_workspace_documents_are_separated_by_user(accounts, monkeypatch):
    spec=importlib.util.spec_from_file_location('isolated_studio',Path(__file__).with_name('studio_api.py'))
    studio=importlib.util.module_from_spec(spec);spec.loader.exec_module(studio)
    studio.ROOT=accounts.root
    module.install(studio.app,accounts.root,'http://unused',start_worker=False)
    one,two=TestClient(studio.app),TestClient(studio.app)
    for client,name in ((one,'alice-user'),(two,'bobby-user')):
        result=client.post('/accounts/register',json={'username':name,'password':'long-password-123'})
        client.headers['X-LichTV-CSRF']=result.json()['csrf']
    response=one.post('/novels/import',files={'file':('story.txt','Only Alice sees this'.encode())})
    assert response.status_code==200
    novel_id=response.json()['id']
    assert one.get('/library').json()['novels'][0]['id']==novel_id
    assert two.get('/library').json()['novels']==[]
    assert two.get('/novels/'+novel_id).status_code==404
    assert two.post('/drafts',json={'title':'Foreign','urls':['/output/other.mp4'],'draft_root':'C:/Drafts'}).status_code==403


def test_nginx_bridge_has_no_raw_gpu_fallback():
    from configure_account_gateway import configure
    source=Path(__file__).with_name('liancheng-panel.conf').read_text()
    config=configure(source)
    assert 'location @gpu_panel { return 403; }' in config
    assert 'proxy_pass http://127.0.0.1:16008' not in config
    assert 'proxy_pass http://127.0.0.1:16128/gateway/api/' in config
    assert configure(config)==config
    assert 'proxy_pass http://127.0.0.1:16138/gateway/api/' in configure(config,api_port=16138)


def test_password_change_revokes_existing_sessions(clients):
    one,_,app=clients
    assert one.post('/accounts/password',json={'current_password':'wrong-password','new_password':'new-long-password'}).status_code==401
    assert one.post('/accounts/password',json={'current_password':'long-password-123','new_password':'new-long-password'}).status_code==200
    assert one.get('/accounts/me').status_code==401
    assert one.post('/accounts/login',json={'username':'member-one','password':'long-password-123'}).status_code==401
    assert one.post('/accounts/login',json={'username':'member-one','password':'new-long-password'}).status_code==200


def test_optional_reference_slots_are_empty_strings(accounts):
    path=accounts.root/'catalog.json';path.write_text(json.dumps([template()]))
    runtime=module.Runtime(accounts,'http://unused',path)
    user=accounts.register('customer','long-password-123')
    payload,_=runtime.prepare(module.Generation(**job_body()|{'workflow_id':'safe-h3'}),user)
    assert payload['input_values']['ref_image_0']==''
    assert payload['workflow_template']['1']['inputs']['ref_image_0']==''

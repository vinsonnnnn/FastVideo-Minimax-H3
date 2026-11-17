"""Payment crypto/ledger integration using locally signed provider fixtures.

These tests never contact either payment provider or create a real charge.
"""
import base64
import concurrent.futures
import json
from pathlib import Path
import re
import sys
import time
import urllib.parse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import studio_accounts as accounts_module
import studio_payments as pay


@pytest.fixture(scope='session')
def keys():
    return {name: rsa.generate_private_key(public_exponent=65537, key_size=2048)
            for name in ('alipay_merchant', 'alipay_provider', 'wechat_merchant', 'wechat_provider')}


def dump_private(path, key):
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


def dump_public(path, key):
    path.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))


@pytest.fixture
def setup(tmp_path, monkeypatch, keys):
    private=tmp_path/'private';private.mkdir()
    dump_private(private/'alipay_private.pem',keys['alipay_merchant'])
    dump_public(private/'alipay_public.pem',keys['alipay_provider'])
    dump_private(private/'wechat_private.pem',keys['wechat_merchant'])
    dump_public(private/'wechat_public.pem',keys['wechat_provider'])
    (private/'api_key.txt').write_text('k'*32)
    config={'public_base_url':'https://payments.example.test/lichtv',
      'alipay':{'enabled':True,'app_id':'2026000012345678','seller_id':'2088000012345678','private_key_file':'alipay_private.pem','alipay_public_key_file':'alipay_public.pem'},
      'wechatpay':{'enabled':True,'app_id':'wx1234567890abcdef','mch_id':'1900000001','merchant_serial':'ABCDEF0123456789',
                   'private_key_file':'wechat_private.pem','api_v3_key_file':'api_key.txt',
                   'platform_public_keys':{'PUB_KEY_ID_1234567890':'wechat_public.pem'}}}
    (private/'payments.json').write_text(json.dumps(config))
    monkeypatch.setattr(accounts_module,'password_hash',lambda value:'test:'+value)
    monkeypatch.setattr(accounts_module,'password_valid',lambda value,encoded:encoded=='test:'+value)
    app=FastAPI();accounts=accounts_module.install(app,tmp_path/'data','http://unused',start_worker=False)
    client,other=TestClient(app),TestClient(app)
    for test_client,name in [(client,'paying-user'),(other,'other-user')]:
        result=test_client.post('/accounts/register',json={'username':name,'password':'long-password-123'})
        test_client.headers['X-LichTV-CSRF']=result.json()['csrf']
    queries={};captured=[]

    def signed_alipay(response, method):
        # Intentionally preserve Unicode, whitespace and escaped delimiters.
        raw=json.dumps(response,ensure_ascii=False,indent=2).encode()
        return 200,{},b'{"'+(method.replace('.','_')+'_response').encode()+b'":'+raw+b',"sign":'+json.dumps(pay.sign(keys['alipay_provider'],raw)).encode()+b'}'

    def signed_wechat(response,status=200,timestamp=None):
        raw=json.dumps(response,ensure_ascii=False).encode()
        timestamp=str(timestamp if timestamp is not None else int(time.time()));nonce='provider-nonce'
        signature=pay.sign(keys['wechat_provider'],f'{timestamp}\n{nonce}\n'.encode()+raw+b'\n')
        return status,{'Wechatpay-Serial':'PUB_KEY_ID_1234567890','Wechatpay-Timestamp':timestamp,'Wechatpay-Nonce':nonce,'Wechatpay-Signature':signature},raw

    def exchange(request):
        captured.append(request)
        if request.full_url.startswith('https://openapi.alipay.com/'):
            parameters=dict(urllib.parse.parse_qsl(request.data.decode()))
            pay.verify(keys['alipay_merchant'].public_key(),pay.alipay_content(parameters),parameters['sign'])
            assert parameters['app_id']==config['alipay']['app_id']
            business=json.loads(parameters['biz_content']);method=parameters['method']
            assert 'sign_type=RSA2' in request.data.decode()
            if method=='alipay.trade.precreate':
                assert parameters['notify_url']=='https://payments.example.test/lichtv/studio-api/payments/notify/alipay'
                assert business['total_amount']=='9.50'
                return signed_alipay({'code':'10000','out_trade_no':business['out_trade_no'],'qr_code':'https://qr.alipay.com/test-order'},method)
            return signed_alipay({'code':'10000','trade_status':'WAIT_BUYER_PAY','out_trade_no':business['out_trade_no']}|queries.get(business['out_trade_no'],{}),method)
        assert request.full_url.startswith('https://api.mch.weixin.qq.com/')
        authorization=request.headers['Authorization'];parts=dict(re.findall(r'(\w+)="([^"]*)"',authorization))
        parsed=urllib.parse.urlsplit(request.full_url);path=parsed.path+('?' + parsed.query if parsed.query else '')
        content=f'{request.get_method()}\n{path}\n{parts["timestamp"]}\n{parts["nonce_str"]}\n'.encode()+(request.data or b'')+b'\n'
        pay.verify(keys['wechat_merchant'].public_key(),content,parts['signature'])
        assert parts['mchid']==config['wechatpay']['mch_id']
        if request.get_method()=='POST':
            business=json.loads(request.data);assert business['amount']=={'total':950,'currency':'CNY'}
            assert business['notify_url']=='https://payments.example.test/lichtv/studio-api/payments/notify/wechatpay'
            return signed_wechat({'code_url':'weixin://wxpay/bizpayurl?pr=test-order'})
        order_id=parsed.path.rsplit('/',1)[1]
        return signed_wechat({'trade_state':'NOTPAY','out_trade_no':order_id,'appid':config['wechatpay']['app_id'],'mchid':config['wechatpay']['mch_id']}|queries.get(order_id,{}))
    monkeypatch.setattr(pay,'exchange',exchange)
    return {'app':app,'accounts':accounts,'payments':app.state.payments,'client':client,'other':other,
            'config':config,'keys':keys,'queries':queries,'captured':captured,'signed_wechat':signed_wechat,'signed_alipay':signed_alipay}


def order(setup,channel,key='checkout-request-123'):
    response=setup['client'].post('/accounts/orders',json={'package_id':'p100','channel':channel,'idempotency_key':key})
    assert response.status_code==200,response.text
    assert response.json()['status']=='pending'
    return response.json()


def alipay_notification(setup,order_id,**changes):
    values={'app_id':setup['config']['alipay']['app_id'],'seller_id':setup['config']['alipay']['seller_id'],
            'out_trade_no':order_id,'total_amount':'9.50','trade_status':'TRADE_SUCCESS','trade_no':'20261116000000123456789','sign_type':'RSA2'}|changes
    values['sign']=pay.sign(setup['keys']['alipay_provider'],pay.alipay_content(values,callback=True))
    return urllib.parse.urlencode(values)


def wechat_transaction(setup,order_id,**changes):
    return {'appid':setup['config']['wechatpay']['app_id'],'mchid':setup['config']['wechatpay']['mch_id'],
            'out_trade_no':order_id,'transaction_id':'42000000000000123456','trade_state':'SUCCESS','amount':{'total':950,'payer_total':900,'currency':'CNY'}}|changes


def wechat_notification(setup,transaction):
    nonce='nonce-123456';aad='transaction'
    ciphertext=AESGCM(b'k'*32).encrypt(nonce.encode(),json.dumps(transaction).encode(),aad.encode())
    envelope={'id':'notification-123','event_type':'TRANSACTION.SUCCESS','resource_type':'encrypt-resource',
              'resource':{'original_type':'transaction','algorithm':'AEAD_AES_256_GCM','nonce':nonce,
                          'associated_data':aad,'ciphertext':base64.b64encode(ciphertext).decode()}}
    _,headers,raw=setup['signed_wechat'](envelope)
    return headers,raw


def balance(setup):
    return setup['client'].get('/accounts/me').json()['user']['credits']


@pytest.mark.parametrize('channel',['alipay','wechatpay'])
def test_qr_preorder_signature_and_idempotency(setup,channel):
    first=order(setup,channel);second=order(setup,channel)
    assert first['id']==second['id'] and len(setup['captured'])==1
    assert len(setup['accounts'].rows('SELECT * FROM orders'))==1
    assert balance(setup)==1_000_000
    assert setup['client'].get(first['qr_url'].removeprefix('/studio-api')).content.startswith(b'\x89PNG')
    assert setup['other'].get('/payments/orders/'+first['id']).status_code==404
    assert setup['other'].get(first['qr_url'].removeprefix('/studio-api')).status_code==404
    assert setup['client'].post('/accounts/orders',json={'package_id':'p20','channel':channel,'idempotency_key':'checkout-request-123'}).status_code==409


def test_alipay_verified_callback_is_public_and_exactly_once(setup):
    created=order(setup,'alipay');body=alipay_notification(setup,created['id'])
    anonymous=TestClient(setup['app'])
    for _ in range(3):
        result=anonymous.post('/payments/notify/alipay',content=body,headers={'Content-Type':'application/x-www-form-urlencoded','Origin':'https://openapi.alipay.com'})
        assert result.status_code==200 and result.text=='success'
    assert balance(setup)==1_000_100
    assert len(setup['accounts'].rows('SELECT * FROM payment_receipts'))==1
    assert len(setup['accounts'].rows("SELECT * FROM ledger WHERE kind='topup'"))==1
    assert setup['client'].get('/payments/orders/'+created['id']).json()['status']=='paid'
    assert setup['client'].get(created['qr_url'].removeprefix('/studio-api')).status_code==409


@pytest.mark.parametrize('changes',[{'total_amount':'0.01'},{'total_amount':'9.501'},{'app_id':'2026000099999999'},
                                     {'seller_id':'2088000099999999'},{'out_trade_no':'a'*32}])
def test_alipay_wrong_amount_app_merchant_or_order_rejected(setup,changes):
    created=order(setup,'alipay')
    result=setup['client'].post('/payments/notify/alipay',content=alipay_notification(setup,created['id'],**changes))
    assert result.status_code==400
    assert balance(setup)==1_000_000
    assert setup['accounts'].rows('SELECT * FROM payment_receipts')==[]


def test_alipay_tamper_and_duplicate_form_fields_rejected(setup):
    created=order(setup,'alipay');body=alipay_notification(setup,created['id'])
    assert setup['client'].post('/payments/notify/alipay',content=body.replace('9.50','0.01')).status_code==400
    assert setup['client'].post('/payments/notify/alipay',content=body+'&total_amount=0.01').status_code==400
    assert setup['client'].post('/payments/notify/alipay',content=body.replace('RSA2','RSA')).status_code==400
    assert balance(setup)==1_000_000


def test_wechat_aes_gcm_verified_notification_and_replay(setup):
    created=order(setup,'wechatpay');headers,raw=wechat_notification(setup,wechat_transaction(setup,created['id']))
    anonymous=TestClient(setup['app'])
    for _ in range(3):
        assert anonymous.post('/payments/notify/wechatpay',content=raw,headers=headers).status_code==204
    assert balance(setup)==1_000_100
    assert len(setup['accounts'].rows('SELECT * FROM payment_receipts'))==1


@pytest.mark.parametrize('changes',[{'appid':'wx9999999999999999'},{'mchid':'1999999999'},
    {'amount':{'total':1,'currency':'CNY'}},{'amount':{'total':950,'currency':'USD'}},
    {'amount':{'total':950.0,'currency':'CNY'}},{'trade_state':'NOTPAY'}])
def test_wechat_wrong_identity_amount_currency_or_state_rejected(setup,changes):
    created=order(setup,'wechatpay');headers,raw=wechat_notification(setup,wechat_transaction(setup,created['id'],**changes))
    assert setup['client'].post('/payments/notify/wechatpay',content=raw,headers=headers).status_code==400
    assert balance(setup)==1_000_000


def test_wechat_stale_unknown_key_bad_signature_or_ciphertext(setup):
    created=order(setup,'wechatpay');headers,raw=wechat_notification(setup,wechat_transaction(setup,created['id']))
    for field,value in [('Wechatpay-Timestamp',str(int(time.time())-400)),('Wechatpay-Serial','PUB_KEY_ID_9999'),('Wechatpay-Signature','WECHATPAY/SIGNTEST/not-valid')]:
        assert setup['client'].post('/payments/notify/wechatpay',content=raw,headers=headers|{field:value}).status_code==400
    envelope=json.loads(raw);envelope['resource']['ciphertext']='broken'
    _,valid_headers,corrupt=setup['signed_wechat'](envelope)
    assert setup['client'].post('/payments/notify/wechatpay',content=corrupt,headers=valid_headers).status_code==400
    assert balance(setup)==1_000_000


@pytest.mark.parametrize('channel',['alipay','wechatpay'])
def test_signed_query_recovers_missed_notification(setup,channel):
    created=order(setup,channel)
    setup['queries'][created['id']]=({'trade_status':'TRADE_SUCCESS','trade_no':'20261116000000011111','total_amount':'9.50'} if channel=='alipay' else wechat_transaction(setup,created['id']))
    with setup['accounts'].transaction() as db:db.execute('UPDATE orders SET query_after=0')
    result=setup['client'].post('/payments/orders/'+created['id']+'/refresh',json={})
    assert result.status_code==200 and result.json()['status']=='paid'
    assert balance(setup)==1_000_100
    assert len(setup['captured'])==2


def test_same_provider_receipt_cannot_pay_two_orders(setup):
    one=order(setup,'alipay');two=order(setup,'alipay','another-request-key')
    for created,code in [(one,200),(two,400)]:
        assert setup['client'].post('/payments/notify/alipay',content=alipay_notification(setup,created['id'])).status_code==code
    assert balance(setup)==1_000_100
    assert setup['payments'].order(two['id'])['status']=='pending'


def test_concurrent_callback_and_query_credits_once(setup):
    created=order(setup,'wechatpay')
    transaction=setup['payments'].providers['wechatpay'].transaction(wechat_transaction(setup,created['id']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(lambda _: setup['payments'].settle(transaction),range(40)))
    assert balance(setup)==1_000_100
    assert len(setup['accounts'].rows("SELECT * FROM ledger WHERE kind='topup'"))==1


def test_cross_channel_and_manual_confirmation_cannot_bypass(setup):
    created=order(setup,'alipay')
    headers,raw=wechat_notification(setup,wechat_transaction(setup,created['id']))
    assert setup['client'].post('/payments/notify/wechatpay',content=raw,headers=headers).status_code==400
    admin=setup['accounts'].register('operator','long-password-123',admin=True)
    with pytest.raises(accounts_module.HTTPException) as error:
        setup['accounts'].confirm_order(admin,created['id'],'fake-bank-receipt')
    assert error.value.status_code==409
    assert setup['other'].post('/payments/orders/'+created['id']+'/refresh',json={}).status_code==404
    assert balance(setup)==1_000_000


def test_expired_qr_still_accepts_late_verified_payment(setup):
    created=order(setup,'alipay')
    with setup['accounts'].transaction() as db:db.execute('UPDATE orders SET expires_at=1')
    assert setup['client'].get(created['qr_url'].removeprefix('/studio-api')).status_code==409
    assert setup['client'].post('/payments/notify/alipay',content=alipay_notification(setup,created['id'])).status_code==200
    assert balance(setup)==1_000_100


def test_provider_response_signature_mandatory(setup,monkeypatch):
    def unsigned(request):return 200,{},b'{"code_url":"weixin://bad"}'
    monkeypatch.setattr(pay,'exchange',unsigned)
    created=order(setup,'wechatpay')
    assert created['qr_url'] is None and created['payment_state']=='create_unknown'
    assert balance(setup)==1_000_000


def test_alipay_exact_raw_response_signature_not_reserialized(setup,monkeypatch):
    provider=setup['payments'].providers['alipay']
    # Preserve whitespace and escaped slashes in the signed object.
    raw=b'{ "code": "10000", "text": "https:\\/\\/example.test", "list": [1, 2] }'
    signed=b'{"alipay_trade_query_response":'+raw+b',"sign":'+json.dumps(pay.sign(setup['keys']['alipay_provider'],raw)).encode()+b'}'
    monkeypatch.setattr(pay,'exchange',lambda request:(200,{},signed))
    assert provider.call('alipay.trade.query',{'out_trade_no':'unused'})['text']=='https://example.test'
    tampered=signed.replace(b'[1, 2]',b'[1,2]')
    monkeypatch.setattr(pay,'exchange',lambda request:(200,{},tampered))
    with pytest.raises(pay.SignatureError):provider.call('alipay.trade.query',{'out_trade_no':'unused'})


def test_no_keys_means_no_qr_or_automatic_credit(tmp_path,monkeypatch):
    monkeypatch.setattr(accounts_module,'password_hash',lambda value:'test:'+value)
    accounts=accounts_module.Accounts(tmp_path/'data');payments=pay.Payments(accounts)
    user=accounts.register('customer','long-password-123')
    for channel in ['alipay','wechatpay']:
        with pytest.raises(accounts_module.HTTPException) as error:payments.create(user['id'],accounts_module.PACKAGES[1],channel)
        assert error.value.status_code==503
    assert all(not item['enabled'] for item in payments.channels())
    assert accounts.rows('SELECT * FROM orders')==[]


@pytest.mark.parametrize('channel',['alipay','wechatpay'])
def test_signed_query_for_another_order_never_credits(setup,channel):
    created=order(setup,channel)
    setup['queries'][created['id']]=({'out_trade_no':'f'*32,'trade_status':'TRADE_SUCCESS','trade_no':'20261116000000011111','total_amount':'9.50'} if channel=='alipay' else wechat_transaction(setup,'f'*32))
    with setup['accounts'].transaction() as db:db.execute('UPDATE orders SET query_after=0')
    assert setup['client'].post('/payments/orders/'+created['id']+'/refresh',json={}).json()['status']=='pending'
    assert balance(setup)==1_000_000


def test_lost_precreate_response_recovers_same_order_without_second_credit(setup,monkeypatch):
    exchange=pay.exchange
    def lost_response(request):
        response=exchange(request)
        if request.get_method()=='POST':raise pay.PaymentError('Response lost')
        return response
    monkeypatch.setattr(pay,'exchange',lost_response)
    created=order(setup,'wechatpay');assert created['payment_state']=='create_unknown'
    setup['queries'][created['id']]=wechat_transaction(setup,created['id'])
    with setup['accounts'].transaction() as db:db.execute('UPDATE orders SET query_after=0')
    result=setup['client'].post('/payments/orders/'+created['id']+'/retry',json={})
    assert result.json()['status']=='paid'
    assert len(setup['captured'])==2 and balance(setup)==1_000_100


def test_signed_pending_and_closed_notifications_do_not_credit(setup):
    created=order(setup,'alipay')
    for state in ['WAIT_BUYER_PAY','TRADE_CLOSED']:
        result=setup['client'].post('/payments/notify/alipay',content=alipay_notification(setup,created['id'],trade_status=state))
        assert result.status_code==200
    assert balance(setup)==1_000_000
    assert setup['payments'].order(created['id'])['status']=='closed'


def test_oversized_notification_rejected_without_credit(setup):
    order(setup,'alipay')
    assert setup['client'].post('/payments/notify/alipay',content=b'x'*(pay.MAX_BODY+1)).status_code==413
    assert balance(setup)==1_000_000


def test_old_manual_order_migration_preserves_balance_and_order(tmp_path,monkeypatch):
    monkeypatch.setattr(accounts_module,'password_hash',lambda value:'test:'+value)
    accounts=accounts_module.Accounts(tmp_path/'data');user=accounts.register('customer','long-password-123')
    with accounts.transaction() as db:
        db.execute("INSERT INTO orders(id,user_id,package,credits,price_cents,status,created_at) VALUES('legacy',?,'p100',100,950,'pending',1)",(user['id'],))
    payments=pay.Payments(accounts)
    assert payments.order('legacy')['channel']=='manual'
    assert payments.order('legacy')['price_cents']==950
    assert accounts.rows('SELECT credits FROM users')[0]['credits']==1_000_000
    assert accounts.rows('SELECT * FROM payment_receipts')==[]


def test_online_create_requires_idempotency_key(setup):
    result=setup['client'].post('/accounts/orders',json={'package_id':'p100','channel':'alipay'})
    assert result.status_code==422
    assert setup['accounts'].rows('SELECT * FROM orders')==[]


def test_http_callback_base_disables_both_channels(setup):
    path=setup['payments'].config_path
    config=json.loads(path.read_text());config['public_base_url']='http://payments.example.test'
    path.write_text(json.dumps(config))
    reloaded=pay.Payments(setup['accounts'],path)
    assert reloaded.providers=={}
    assert all('HTTPS' in channel['message'] for channel in reloaded.channels())
    assert setup['client'].get('/payments/admin/configuration').status_code==403

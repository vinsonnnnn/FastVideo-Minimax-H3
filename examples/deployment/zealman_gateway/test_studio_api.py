"""Regression checks for document persistence, secrets and portable drafts."""
import importlib.util
import io
import json
from pathlib import Path
import zipfile

from fastapi.testclient import TestClient
import pytest


SPEC = importlib.util.spec_from_file_location('lichtv_studio_api', Path(__file__).with_name('studio_api.py'))
studio = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(studio)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, 'ROOT', tmp_path)
    return TestClient(studio.app)


def test_novel_and_script_are_separate_persistent_documents(client):
    content = '第一章 雨夜\n\n林夏收到一封信。\n第二章 来客\n\n门被敲响。'
    imported = client.post('/novels/import', files={'file': ('story.txt', content.encode(), 'text/plain')})
    assert imported.status_code == 200
    novel = imported.json()
    assert novel['chapters'] == 2
    library = client.get('/library').json()
    assert not library['scripts']
    assert 'text' not in library['novels'][0]
    created = client.post('/scripts', json={'title':'改编', 'text':'第一场：雨夜', 'novel_id':novel['id']}).json()
    updated = client.put('/scripts/'+created['id'], json={'title':'改编第二稿','text':'第一场：门被敲响','novel_id':novel['id']})
    assert updated.status_code == 200
    assert client.get('/novels/'+novel['id']).json()['text'] == content
    assert client.get('/library').json()['scripts'][0]['text'] == '第一场：门被敲响'


def test_provider_keys_are_never_returned_and_defaults_require_real_models(client):
    response = client.post('/providers', json={'name':'测试分组','kind':'image','base_url':'https://example.com/v1','api_key':'private-test-value','models':['model-a']})
    assert response.status_code == 200
    assert response.json()['configured']
    assert 'private-test-value' not in response.text
    assert 'private-test-value' not in client.get('/library').text
    provider_id = response.json()['id']
    assert client.put('/defaults', json={'kind':'image','provider_id':provider_id,'model':'missing'}).status_code == 400
    assert client.put('/defaults', json={'kind':'image','provider_id':provider_id,'model':'model-a'}).status_code == 200


def test_import_does_not_extract_docx_archive_paths(client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>原著正文</w:t></w:r></w:p></w:body></w:document>')
        archive.writestr('../../outside.txt','do not extract')
    response = client.post('/novels/import', files={'file':('story.docx',buffer.getvalue())})
    assert response.json()['text'] == '原著正文'
    assert not (studio.ROOT.parent / 'outside.txt').exists()


def test_draft_contains_media_real_timeline_and_windows_material_paths(client, monkeypatch):
    sample = Path(__file__).resolve().parents[3] / 'assets/benchmarks/lichtv-2026-11-15/samples/home-u00.mp4'
    if not sample.is_file():
        pytest.skip('Requires the saved H3 validation sample')
    monkeypatch.setattr(studio.urllib.request, 'urlopen', lambda *args, **kwargs: sample.open('rb'))
    response = client.post('/drafts', json={'title':'短剧测试','urls':['/output/clip.mp4'],'draft_root':'C:\\Drafts','width':1080,'height':1920})
    assert response.status_code == 200, response.text
    data = response.json()
    archive = client.get('/downloads/'+data['id'])
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
        folder = data['project_folder']
        script = json.loads(bundle.read(folder+'/draft_content.json'))
        assert script['duration'] > 5_000_000
        assert len(script['tracks'][0]['segments']) == 1
        assert 'C:/Drafts/' in json.dumps(script)
        assert str(studio.ROOT) not in json.dumps(script)
        assert folder+'/materials/clip-001.mp4' in bundle.namelist()


def test_draft_rejects_remote_urls_and_input_files(client):
    for url in ['http://169.254.169.254/', '/api/comfy/view?filename=secret&type=input', '/output/../private']:
        response = client.post('/drafts', json={'urls':[url],'draft_root':'C:\\Drafts'})
        assert response.status_code == 400


def test_model_connector_rejects_private_network_destinations():
    with pytest.raises(studio.HTTPException) as error:
        studio.remote_json({'base_url':'https://127.0.0.1/v1'}, '/models')
    assert error.value.status_code == 400

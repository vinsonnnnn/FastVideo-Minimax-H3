"""LichTV document workspace, compatible model connectors, and draft export.

Run behind the existing gateway, bound to localhost. Data and provider keys
live outside the web root; GPU execution stays in the existing ComfyUI panel.
"""
import argparse
import base64
import datetime
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from xml.etree import ElementTree

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


ROOT = Path('/data/lichtv-studio')
PANEL = 'http://127.0.0.1:16008'
LOCK = threading.RLock()
app = FastAPI(title='LichTV Studio', docs_url=None, redoc_url=None)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def identifier():
    return uuid.uuid4().hex


def workspace_root():
    from studio_accounts import CURRENT_USER
    user = CURRENT_USER.get()
    if user is None:  # Standalone component tests install no account middleware.
        return ROOT
    path = ROOT / 'users' / user['id']
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def read_store():
    path = workspace_root() / 'workspace.json'
    if path.exists():
        return json.loads(path.read_text())
    return {'novels': [], 'scripts': [], 'providers': [], 'defaults': {}}


def save_store(data):
    workspace_root().mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = workspace_root() / ('workspace-' + identifier() + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temporary.chmod(0o600)
    temporary.replace(workspace_root() / 'workspace.json')


def public_provider(provider):
    return {**{key: value for key, value in provider.items() if key != 'api_key'},
            'configured': bool(provider.get('api_key'))}


def local_json(path):
    try:
        with urllib.request.urlopen(PANEL + path, timeout=30) as response:
            return json.load(response)
    except Exception:
        raise HTTPException(502, '生成服务暂不可用，请检查5090连接') from None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def remote_json(provider, suffix, payload=None):
    base = provider['base_url'].rstrip('/')
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.query or parsed.fragment:
        raise HTTPException(400, 'API地址须为不含账号、查询参数的HTTPS地址')
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError:
        raise HTTPException(400, 'API域名无法解析') from None
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise HTTPException(400, '外部API不能指向本机、内网或云元数据地址')
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    if provider.get('api_key'):
        headers['Authorization'] = 'Bearer ' + provider['api_key']
    request = urllib.request.Request(base + suffix, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=180) as response:
            raw = response.read(30 * 1024 * 1024 + 1)
            if len(raw) > 30 * 1024 * 1024:
                raise HTTPException(502, 'API响应超过30MiB限制')
            return json.loads(raw)
    except urllib.error.HTTPError as error:
        raise HTTPException(502, f'模型服务返回HTTP {error.code}，请检查地址、模型与密钥') from None
    except (OSError, ValueError):
        raise HTTPException(502, '模型服务连接或响应格式异常') from None


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'LichTV Studio'}


@app.get('/library')
def library():
    with LOCK:
        data = read_store()
    return {'novels': [{key: value for key, value in item.items() if key != 'text'} for item in data['novels']],
            'scripts': data['scripts'], 'providers': [public_provider(item) for item in data['providers']],
            'defaults': data['defaults']}


def decode_document(filename, content):
    extension = Path(filename).suffix.lower()
    if extension in ('.txt', '.md'):
        for encoding in ('utf-8-sig', 'gb18030'):
            try:
                return content.decode(encoding).strip()
            except UnicodeDecodeError:
                pass
        raise HTTPException(400, '请将文本另存为UTF-8后上传')
    if extension == '.docx':
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                info = archive.getinfo('word/document.xml')
                if info.file_size > 40 * 1024 * 1024:
                    raise HTTPException(400, 'Word正文过大')
                xml = ElementTree.fromstring(archive.read(info))
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            return '\n'.join(''.join(node.itertext()) for node in xml.findall('.//w:p', ns)).strip()
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError):
            raise HTTPException(400, '无法读取DOCX，请确认文件有效') from None
    if extension == '.pdf':
        from pypdf import PdfReader
        try:
            document = PdfReader(io.BytesIO(content))
            if len(document.pages) > 500:
                raise HTTPException(400, 'PDF不能超过500页')
            return '\n'.join(page.extract_text() or '' for page in document.pages).strip()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(400, 'PDF解析失败；加密或扫描文件请先转换为文本') from None
    raise HTTPException(400, '支持TXT、MD、DOCX和可提取文字的PDF')


@app.post('/novels/import')
async def import_novel(file: UploadFile = File(...)):
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, '单份文档不能超过20MiB')
    filename = Path((file.filename or 'novel.txt').replace('\\', '/')).name
    text = decode_document(filename, content)
    if not text:
        raise HTTPException(400, '没有提取到正文；扫描PDF请先完成OCR')
    if len(text) > 2_000_000:
        raise HTTPException(400, '正文不能超过200万字，请分卷上传')
    chapters = len(re.findall(r'(?m)^\s*第[零一二三四五六七八九十百千万\d]+[章回卷节]', text)) or 1
    novel = {'id': identifier(), 'title': Path(filename).stem[:120], 'filename': filename,
             'text': text, 'characters': len(text), 'chapters': chapters, 'created_at': now()}
    with LOCK:
        data = read_store()
        data['novels'].insert(0, novel)
        save_store(data)
    return novel


@app.get('/novels/{novel_id}')
def get_novel(novel_id: str):
    for item in read_store()['novels']:
        if item['id'] == novel_id:
            return item
    raise HTTPException(404, '小说不存在')


@app.delete('/novels/{novel_id}')
def delete_novel(novel_id: str):
    with LOCK:
        data = read_store()
        data['novels'] = [item for item in data['novels'] if item['id'] != novel_id]
        save_store(data)
    return {'success': True}


class ScriptInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(default='', max_length=500_000)
    novel_id: str | None = None


@app.post('/scripts')
def create_script(body: ScriptInput):
    item = {**body.model_dump(), 'id': identifier(), 'updated_at': now()}
    with LOCK:
        data = read_store()
        data['scripts'].insert(0, item)
        save_store(data)
    return item


@app.put('/scripts/{script_id}')
def update_script(script_id: str, body: ScriptInput):
    with LOCK:
        data = read_store()
        for item in data['scripts']:
            if item['id'] == script_id:
                item.update(body.model_dump(), updated_at=now())
                save_store(data)
                return item
    raise HTTPException(404, '剧本不存在')


@app.delete('/scripts/{script_id}')
def delete_script(script_id: str):
    with LOCK:
        data = read_store()
        data['scripts'] = [item for item in data['scripts'] if item['id'] != script_id]
        save_store(data)
    return {'success': True}


class ProviderInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    kind: str = Field(pattern='^(text|image)$')
    base_url: str = Field(max_length=500)
    api_key: str = Field(default='', max_length=2000)
    models: list[str] = Field(default_factory=list, max_length=100)


@app.post('/providers')
def add_provider(body: ProviderInput):
    value = body.model_dump()
    parsed = urllib.parse.urlsplit(value['base_url'])
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(400, '请输入不含密钥、账号和查询参数的HTTPS API基础地址')
    item = {**value, 'id': identifier(), 'created_at': now()}
    with LOCK:
        data = read_store()
        data['providers'].append(item)
        save_store(data)
    return public_provider(item)


def provider_by_id(provider_id):
    for item in read_store()['providers']:
        if item['id'] == provider_id:
            return item
    raise HTTPException(404, 'API分组不存在')


@app.delete('/providers/{provider_id}')
def delete_provider(provider_id: str):
    with LOCK:
        data = read_store()
        data['providers'] = [item for item in data['providers'] if item['id'] != provider_id]
        data['defaults'] = {key: value for key, value in data['defaults'].items() if value.get('provider_id') != provider_id}
        save_store(data)
    return {'success': True}


@app.post('/providers/{provider_id}/models')
def provider_models(provider_id: str):
    response = remote_json(provider_by_id(provider_id), '/models')
    models = [str(item['id']) for item in response.get('data', []) if isinstance(item, dict) and item.get('id')]
    with LOCK:
        data = read_store()
        for item in data['providers']:
            if item['id'] == provider_id:
                item['models'] = models[:100]
        save_store(data)
    return {'models': models[:100]}


class DefaultInput(BaseModel):
    kind: str = Field(pattern='^(text|image)$')
    provider_id: str
    model: str = Field(min_length=1, max_length=300)


@app.put('/defaults')
def set_default(body: DefaultInput):
    if body.provider_id != 'comfyui':
        provider = provider_by_id(body.provider_id)
        if provider['kind'] != body.kind or body.model not in provider['models']:
            raise HTTPException(400, '请选择该分组中已配置的模型')
    elif body.kind != 'image':
        raise HTTPException(400, '本机工作流仅用于图像入口')
    with LOCK:
        data = read_store()
        data['defaults'][body.kind] = body.model_dump()
        save_store(data)
    return body.model_dump()


class AdaptInput(BaseModel):
    novel_id: str
    provider_id: str
    model: str
    instructions: str = Field(default='', max_length=4000)


@app.post('/adapt')
def adapt_script(body: AdaptInput):
    novel = get_novel(body.novel_id)
    provider = provider_by_id(body.provider_id)
    if provider['kind'] != 'text' or body.model not in provider['models']:
        raise HTTPException(400, '请选择已配置的文本模型')
    if len(novel['text']) > 30_000:
        raise HTTPException(400, '单次AI改编限3万字，请先按章节拆分上传，避免超出模型上下文')
    response = remote_json(provider, '/chat/completions', {'model': body.model, 'messages': [
        {'role': 'system', 'content': '你是短剧编剧。根据用户原文改编剧本。用中文输出：剧名、人物、场次、内外景、时间、动作、对白和镜头建议。不得声称已经生成视频。'},
        {'role': 'user', 'content': body.instructions + '\n\n小说原文：\n' + novel['text']}], 'stream': False})
    try:
        text = response['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        raise HTTPException(502, '文本API未返回可读取的剧本正文') from None
    return create_script(ScriptInput(title=novel['title'] + ' · 改编剧本', text=text, novel_id=novel['id']))


class ImageInput(BaseModel):
    provider_id: str
    model: str
    prompt: str = Field(min_length=1, max_length=10_000)
    size: str = Field(default='1024x1024', pattern=r'^\d{3,4}x\d{3,4}$')


@app.post('/image')
def api_image(body: ImageInput):
    provider = provider_by_id(body.provider_id)
    if provider['kind'] != 'image' or body.model not in provider['models']:
        raise HTTPException(400, '请选择已配置的图像模型')
    response = remote_json(provider, '/images/generations', {'model': body.model, 'prompt': body.prompt, 'size': body.size, 'n': 1})
    result = response.get('data', [])
    if not result:
        raise HTTPException(502, '图像API未返回图片')
    item = result[0]
    if item.get('b64_json'):
        try:
            content = base64.b64decode(item['b64_json'], validate=True)
        except ValueError:
            raise HTTPException(502, '图像API返回了无效的图片编码') from None
        if len(content) > 24 * 1024 * 1024:
            raise HTTPException(502, '返回图片过大')
        from PIL import Image
        try:
            image = Image.open(io.BytesIO(content))
            image.verify()
        except Exception:
            raise HTTPException(502, '返回内容不是可读取图片') from None
        token = identifier() + '.png'
        folder = workspace_root() / 'images'
        folder.mkdir(parents=True, exist_ok=True)
        with Image.open(io.BytesIO(content)) as image:
            image.save(folder / token, format='PNG')
        return {'url': '/studio-api/images/' + token}
    url = item.get('url', '')
    if not url.startswith('https://'):
        raise HTTPException(502, '图像API未返回HTTPS图片地址或base64图片')
    return {'url': url}


@app.get('/images/{filename}')
def image_file(filename: str):
    if not re.fullmatch(r'[a-f0-9]{32}\.png', filename):
        raise HTTPException(404)
    path = workspace_root() / 'images' / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


@app.get('/videos')
def videos():
    from studio_accounts import CURRENT_USER
    user = CURRENT_USER.get()
    if user is not None:
        items = app.state.accounts.rows("SELECT * FROM media WHERE user_id=? AND kind='output' ORDER BY rowid DESC", (user['id'],))
        return {'items': [{'url': '/studio-api/accounts/media/' + item['id'],
                           'filename': Path(urllib.parse.urlsplit(item['path']).path).name,
                           'title': '我的视频', 'created_at': None} for item in items
                          if re.search(r'\.(mp4|mov|webm|mkv)(\?|$)', item['path'], re.I)]}
    response = local_json('/api/tasks?status=done&limit=100')
    found = []
    seen = set()
    for task in response.get('items', []):
        if str(task.get('title', '')).startswith('API-Z-连通测试'):
            continue
        for output in task.get('outputs') or []:
            if not isinstance(output, dict):
                continue
            url = output.get('url', '')
            parsed = urllib.parse.urlsplit(url)
            filename = output.get('filename') or urllib.parse.parse_qs(parsed.query).get('filename', [''])[0]
            filename = filename or urllib.parse.unquote(parsed.path.rsplit('/', 1)[-1])
            if not str(filename).lower().endswith(('.mp4', '.mov', '.webm', '.mkv')) or not url:
                continue
            if url in seen:
                continue
            seen.add(url)
            found.append({'url': url, 'filename': filename, 'title': task.get('title', filename), 'created_at': task.get('finished_at')})
    return {'items': found}


def panel_media_path(url):
    from studio_accounts import CURRENT_USER
    user = CURRENT_USER.get()
    if user is not None:
        token = url.removeprefix('/lichtv').removeprefix('/studio-api/accounts/media/')
        rows = app.state.accounts.rows("SELECT * FROM media WHERE id=? AND user_id=? AND kind='output'", (token, user['id']))
        if not rows:
            raise HTTPException(403, '只能导出当前账号的成片')
        url = rows[0]['path']
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme or parsed.netloc or '..' in urllib.parse.unquote(parsed.path).split('/'):
        raise HTTPException(400, '只能导出当前面板的生成视频')
    path = parsed.path.removeprefix('/lichtv')
    if not path.startswith('/output/') and path != '/api/comfy/view':
        raise HTTPException(400, '请选择当前面板的产出视频')
    query = urllib.parse.parse_qs(parsed.query)
    if path == '/api/comfy/view' and query.get('type', ['output'])[0] != 'output':
        raise HTTPException(400, '不能把输入文件作为成片导出')
    return path + ('?' + parsed.query if parsed.query else '')


class DraftInput(BaseModel):
    title: str = Field(default='LichTV短剧', min_length=1, max_length=80)
    urls: list[str] = Field(min_length=1, max_length=12)
    draft_root: str = Field(min_length=4, max_length=400)
    width: int = Field(default=1080, ge=256, le=4096)
    height: int = Field(default=1920, ge=256, le=4096)


@app.post('/drafts')
def create_draft(body: DraftInput):
    if not re.match(r'^[a-zA-Z]:[\\/]', body.draft_root) or any(part == '..' for part in body.draft_root.replace('\\', '/').split('/')):
        raise HTTPException(400, '请填写本机剪映草稿目录的完整Windows路径')
    import pyJianYingDraft as draft
    workspace_root().mkdir(parents=True, exist_ok=True, mode=0o700)
    token = identifier()
    name = 'LichTV_' + datetime.datetime.now().strftime('%Y%m%d') + '_' + token[:8]
    target_root = re.sub('/+', '/', body.draft_root.replace('\\', '/')).rstrip('/')
    destination = target_root + '/' + name
    downloads = workspace_root() / 'downloads'
    downloads.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=workspace_root()) as temporary:
        workspace = Path(temporary)
        script = draft.DraftFolder(str(workspace)).create_draft(name, body.width, body.height, fps=24)
        if hasattr(script, 'append_track'):
            script.append_track(draft.TrackSpec(draft.TrackType.video, 'main_video'))
        else:
            script.add_track(draft.TrackType.video, 'main_video')
        project = workspace / name
        materials = project / 'materials'
        materials.mkdir()
        duration = 0
        replacements = {}
        for index, url in enumerate(body.urls, 1):
            source = panel_media_path(url)
            suffix = Path(urllib.parse.urlsplit(source).path).suffix.lower()
            if suffix not in ('.mp4', '.mov', '.webm', '.mkv'):
                suffix = '.mp4'
            filename = f'clip-{index:03d}' + suffix
            local = materials / filename
            try:
                with urllib.request.urlopen(PANEL + source, timeout=120) as response, local.open('wb') as output:
                    total = 0
                    while block := response.read(1024 * 1024):
                        total += len(block)
                        if total > 200 * 1024 * 1024:
                            raise HTTPException(400, '单个导出视频不能超过200MiB')
                        output.write(block)
                material = draft.VideoMaterial(str(local))
                if material.duration <= 0:
                    raise ValueError('empty media')
                segment = draft.VideoSegment(material, draft.trange(duration, material.duration))
                script.add_segment(segment, 'main_video')
                duration += material.duration
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(422, f'第{index}个视频无法读取或下载，请确认成片仍在服务器') from None
            replacements[str(local)] = destination + '/materials/' + filename
        script.save()
        content_path = project / 'draft_content.json'
        content = content_path.read_text()
        for source, target in replacements.items():
            content = content.replace(source, target)
        content_path.write_text(content)
        meta_path = project / 'draft_meta_info.json'
        meta = json.loads(meta_path.read_text())
        meta.update(draft_id=token.upper(), draft_name=body.title, draft_fold_path=destination,
                    draft_root_path=target_root, tm_duration=duration,
                    tm_draft_create=int(datetime.datetime.now().timestamp() * 1_000_000),
                    tm_draft_modified=int(datetime.datetime.now().timestamp() * 1_000_000))
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        instructions = f'目标剪映草稿目录：{body.draft_root}\n\n把本压缩包中的 {name} 文件夹完整复制到上面的目录，然后在剪映专业版刷新草稿列表或重启。\n请勿只复制JSON，materials目录包含视频及原音轨。\n若本机草稿目录不同，请在网页更正目录后重新导出，否则素材绝对路径无法匹配。\n此包是可编辑草稿，不是最终成片；当前未在你的剪映版本中验收。\n'
        (workspace / '导入说明.txt').write_text(instructions)
        archive = downloads / (token + '.zip')
        with zipfile.ZipFile(archive, 'w') as bundle:
            for path in workspace.rglob('*'):
                if path.is_file():
                    bundle.write(path, str(path.relative_to(workspace)), compress_type=zipfile.ZIP_DEFLATED if path.suffix in ('.json', '.txt') else zipfile.ZIP_STORED)
    return {'id': token, 'download_url': '/studio-api/downloads/' + token,
            'project_folder': name, 'target_directory': body.draft_root,
            'clips': len(body.urls), 'duration_seconds': duration / 1_000_000}


@app.get('/downloads/{token}')
def download_draft(token: str):
    if not re.fullmatch(r'[0-9a-f]{32}', token):
        raise HTTPException(404)
    path = workspace_root() / 'downloads' / (token + '.zip')
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, filename='LichTV-draft-' + token[:8] + '.zip')


if __name__ == '__main__':
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=ROOT)
    parser.add_argument('--panel-url', default=PANEL)
    parser.add_argument('--port', type=int, default=16128)
    parser.add_argument('--no-worker', action='store_true', help='Disable GPU dispatcher for isolated HTTP tests')
    args = parser.parse_args()
    ROOT = args.data_dir
    PANEL = args.panel_url.rstrip('/')
    os.umask(0o077)
    from studio_accounts import install
    install(app, ROOT, PANEL, start_worker=not args.no_worker)
    uvicorn.run(app, host='127.0.0.1', port=args.port)

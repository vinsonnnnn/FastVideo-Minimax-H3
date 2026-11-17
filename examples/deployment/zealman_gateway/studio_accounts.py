"""Local account ledger and a single durable, metered GPU queue.

Mount through install() in studio_api. No payment success is inferred from a
browser return URL: verified provider transactions or verified manual receipts credit an order.
"""
import argparse
import contextlib
import contextvars
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt

CURRENT_USER = contextvars.ContextVar('lichtv_user', default=None)
PACKAGES = [{'id': 'p20', 'credits': 20, 'price_cents': 200},
            {'id': 'p100', 'credits': 100, 'price_cents': 950},
            {'id': 'p1000', 'credits': 1000, 'price_cents': 9300},
            {'id': 'p10000', 'credits': 10000, 'price_cents': 92000}]
SESSION_SECONDS = 7 * 86400
COOKIE = 'lichtv_session'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password):
    salt = secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600_000).hex()
    return f'pbkdf2_sha256$600000${salt}${value}'


def password_valid(password, stored):
    _, count, salt, expected = stored.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(count)).hex()
    return hmac.compare_digest(actual, expected)


class Accounts:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / 'accounts.sqlite3'
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS counters(name TEXT PRIMARY KEY,value INTEGER NOT NULL);
                INSERT OR IGNORE INTO counters VALUES('registrations',0);
                CREATE TABLE IF NOT EXISTS users(
                    id TEXT PRIMARY KEY,username TEXT NOT NULL,normalized TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'member',
                    status TEXT NOT NULL DEFAULT 'active',signup_seq INTEGER UNIQUE,
                    credits INTEGER NOT NULL DEFAULT 0 CHECK(credits>=0),created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(
                    token TEXT PRIMARY KEY,user_id TEXT NOT NULL,csrf TEXT NOT NULL,expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS ledger(
                    id INTEGER PRIMARY KEY,user_id TEXT NOT NULL,delta INTEGER NOT NULL,
                    balance INTEGER NOT NULL,kind TEXT NOT NULL,reference TEXT UNIQUE NOT NULL,
                    reason TEXT NOT NULL,actor TEXT,created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS orders(
                    id TEXT PRIMARY KEY,user_id TEXT NOT NULL,package TEXT NOT NULL,
                    credits INTEGER NOT NULL,price_cents INTEGER NOT NULL,status TEXT NOT NULL,
                    receipt TEXT UNIQUE,actor TEXT,created_at REAL NOT NULL,paid_at REAL);
                CREATE TABLE IF NOT EXISTS jobs(
                    id TEXT PRIMARY KEY,user_id TEXT NOT NULL,idem TEXT NOT NULL,body_hash TEXT NOT NULL,
                    workflow TEXT NOT NULL,seconds INTEGER NOT NULL,cost INTEGER NOT NULL,
                    payload TEXT NOT NULL,status TEXT NOT NULL,prompt_id TEXT,result TEXT,
                    error TEXT,created_at REAL NOT NULL,updated_at REAL NOT NULL,
                    UNIQUE(user_id,idem));
                CREATE TABLE IF NOT EXISTS media(
                    id TEXT PRIMARY KEY,user_id TEXT NOT NULL,path TEXT NOT NULL,kind TEXT NOT NULL,
                    job_id TEXT,UNIQUE(user_id,path));
                CREATE INDEX IF NOT EXISTS jobs_queue ON jobs(status,created_at);
                CREATE TABLE IF NOT EXISTS rate_limits(key TEXT PRIMARY KEY,count INTEGER NOT NULL,until REAL NOT NULL);
            ''')
        self.path.chmod(0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=30000')
        return db

    @contextlib.contextmanager
    def transaction(self):
        with contextlib.closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def rows(self, sql, args=()):
        with contextlib.closing(self.connect()) as db:
            return [dict(row) for row in db.execute(sql, args)]

    @staticmethod
    def public(user):
        return {key: user[key] for key in ('id', 'username', 'role', 'status', 'signup_seq', 'credits', 'created_at')}

    def limit(self, key, maximum, window):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM rate_limits WHERE key=?', (key,)).fetchone()
            count = row['count'] + 1 if row and row['until'] > time.time() else 1
            until = row['until'] if row and row['until'] > time.time() else time.time() + window
            if count > maximum:
                raise HTTPException(429, '操作太频繁，请稍后重试')
            db.execute('INSERT OR REPLACE INTO rate_limits VALUES(?,?,?)', (key, count, until))

    def change(self, db, user_id, delta, kind, reference, reason, actor=None):
        if db.execute('SELECT 1 FROM ledger WHERE reference=?', (reference,)).fetchone():
            return False
        row = db.execute('UPDATE users SET credits=credits+? WHERE id=? AND credits+?>=0 RETURNING credits',
                         (delta, user_id, delta)).fetchone()
        if not row:
            raise HTTPException(402, '积分不足，请先充值')
        db.execute('INSERT INTO ledger(user_id,delta,balance,kind,reference,reason,actor,created_at) VALUES(?,?,?,?,?,?,?,?)',
                   (user_id, delta, row['credits'], kind, reference, reason, actor, time.time()))
        return True

    def register(self, username, password, admin=False):
        username = username.strip()
        if not re.fullmatch(r'[\w\-\u4e00-\u9fff]{3,32}', username) or not 10 <= len(password) <= 128:
            raise HTTPException(422, '账号须为3–32位字母、数字、中文或下划线；密码须为10–128位')
        encoded = password_hash(password)
        user_id = secrets.token_hex(16)
        try:
            with self.transaction() as db:
                sequence = None
                if not admin:
                    sequence = db.execute("UPDATE counters SET value=value+1 WHERE name='registrations' RETURNING value").fetchone()[0]
                db.execute('INSERT INTO users(id,username,normalized,password,role,signup_seq,created_at) VALUES(?,?,?,?,?,?,?)',
                           (user_id, username, username.casefold(), encoded, 'admin' if admin else 'member', sequence, time.time()))
                if sequence and sequence <= 100:
                    self.change(db, user_id, 1_000_000, 'signup_bonus', 'signup:' + user_id, f'前100名注册奖励，第{sequence}名')
        except sqlite3.IntegrityError:
            raise HTTPException(409, '该账号已注册') from None
        return self.public(self.rows('SELECT * FROM users WHERE id=?', (user_id,))[0])

    def authenticate(self, token):
        if not token:
            return None
        rows = self.rows('SELECT u.*,s.csrf FROM users u JOIN sessions s ON s.user_id=u.id '
                         "WHERE s.token=? AND s.expires>? AND u.status='active'", (digest(token), time.time()))
        return rows[0] if rows else None

    def new_session(self, user_id):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        with self.transaction() as db:
            db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?)', (digest(token), user_id, csrf, time.time() + SESSION_SECONDS))
        return token, csrf

    def create_job(self, user, body, payload, seconds):
        content = json.dumps(body, sort_keys=True, ensure_ascii=False)
        body_hash = digest(content)
        cost = seconds * 2
        with self.transaction() as db:
            existing = db.execute('SELECT * FROM jobs WHERE user_id=? AND idem=?', (user['id'], body['idempotency_key'])).fetchone()
            if existing:
                if existing['body_hash'] != body_hash:
                    raise HTTPException(409, '重复提交标识对应的内容不同，请重新提交')
                return self.job_public(dict(existing))
            active = db.execute("SELECT COUNT(*) FROM jobs WHERE user_id=? AND status IN ('queued','submitting','running','review')", (user['id'],)).fetchone()[0]
            if active >= 30:
                raise HTTPException(429, '待处理任务最多30个，请等待完成')
            job_id = secrets.token_hex(16)
            self.change(db, user['id'], -cost, 'generation', 'job:' + job_id, f'视频{seconds}秒 × 2积分' if cost else '图像生成（暂不扣视频积分）')
            stamp = time.time()
            db.execute('INSERT INTO jobs(id,user_id,idem,body_hash,workflow,seconds,cost,payload,status,created_at,updated_at) '
                       "VALUES(?,?,?,?,?,?,?,?, 'queued',?,?)", (job_id, user['id'], body['idempotency_key'], body_hash,
                        body['workflow_id'], seconds, cost, json.dumps(payload, ensure_ascii=False), stamp, stamp))
            return self.job_public(dict(db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()))

    @staticmethod
    def job_public(row):
        return {key: (json.loads(row[key]) if key == 'result' and row[key] else row[key]) for key in
                ('id', 'workflow', 'seconds', 'cost', 'status', 'prompt_id', 'result', 'error', 'created_at', 'updated_at')}

    def finish(self, job_id, success, result=None, error=None):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not row or row['status'] in ('done', 'failed', 'cancelled'):
                return
            if not success:
                self.change(db, row['user_id'], row['cost'], 'refund', 'refund:' + job_id, '任务失败，积分退回')
            db.execute('UPDATE jobs SET status=?,result=?,error=?,updated_at=? WHERE id=?',
                       ('done' if success else 'failed', json.dumps(result) if result else None, error, time.time(), job_id))

    def confirm_order(self, actor, order_id, receipt):
        if actor['role'] != 'admin':
            raise HTTPException(403, '需要管理员权限')
        if len(receipt.strip()) < 4:
            raise HTTPException(422, '请填写核验过的收款流水号')
        try:
            with self.transaction() as db:
                row = db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
                if not row:
                    raise HTTPException(404, '订单不存在')
                if 'channel' in row.keys() and row['channel'] != 'manual':
                    raise HTTPException(409, '在线支付订单只能由支付平台验签确认，请查询支付状态')
                if row['status'] == 'paid':
                    if row['receipt'] != receipt.strip():
                        raise HTTPException(409, '订单已使用另一流水入账')
                    return
                self.change(db, row['user_id'], row['credits'], 'topup', 'order:' + order_id,
                            f'充值订单{order_id}', actor['id'])
                db.execute("UPDATE orders SET status='paid',receipt=?,actor=?,paid_at=? WHERE id=?",
                           (receipt.strip(), actor['id'], time.time(), order_id))
        except sqlite3.IntegrityError:
            raise HTTPException(409, '该收款流水已经用于其他订单') from None

    def media(self, user_id, path, kind, job_id=None):
        path = media_path(path)
        with self.transaction() as db:
            db.execute('INSERT OR IGNORE INTO media VALUES(?,?,?,?,?)', (secrets.token_hex(16), user_id, path, kind, job_id))
            return dict(db.execute('SELECT * FROM media WHERE user_id=? AND path=?', (user_id, path)).fetchone())


def media_path(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme or parsed.netloc:
        raise HTTPException(400, '只允许当前生成服务的文件')
    path = urllib.parse.unquote(parsed.path).removeprefix('/lichtv')
    if '..' in path.split('/') or not (path.startswith('/output/') or path == '/api/comfy/view'):
        raise HTTPException(400, '文件路径不合法')
    query = urllib.parse.parse_qs(parsed.query)
    if path == '/api/comfy/view' and query.get('type', ['output'])[0] not in ('input', 'output'):
        raise HTTPException(400, '文件类别不合法')
    return path + ('?' + urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(parsed.query))) if parsed.query else '')


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Credentials(Input):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=10, max_length=128)


class PasswordChange(Input):
    current_password: str = Field(min_length=10, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class OrderInput(Input):
    package_id: str
    channel: str = Field(default='manual', pattern=r'^(manual|alipay|wechatpay)$')
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=100)


class ConfirmInput(Input):
    receipt: str = Field(min_length=4, max_length=120)
    verified_received: bool


class Adjustment(Input):
    delta: StrictInt = Field(ge=-100_000_000, le=100_000_000)
    reason: str = Field(min_length=4, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=100)


class StatusInput(Input):
    status: str


class Generation(Input):
    workflow_id: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=20000)
    seconds: StrictInt = Field(default=5, ge=1, le=15)
    image: str | None = None
    aspect_ratio: str | None = Field(default=None, pattern=r'^(16:9 \(Widescreen\)|9:16 \(Portrait Widescreen\)|1:1 \(Square\))$')
    megapixels: float | None = Field(default=None, ge=0.15, le=2)
    idempotency_key: str = Field(min_length=8, max_length=100)


class Runtime:
    def __init__(self, accounts, panel, catalog):
        self.accounts, self.panel = accounts, panel.rstrip('/')
        self.catalog = json.loads(Path(catalog).read_text()) if Path(catalog).exists() else []
        self.wake = threading.Event()
        self.stop = threading.Event()

    def upstream(self, path, payload=None, timeout=60):
        request = urllib.request.Request(self.panel + path,
                  data=json.dumps(payload).encode() if payload is not None else None,
                  headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)

    def prepare(self, body, user):
        plan = next((item for item in self.catalog if item['id'] == body.workflow_id), None)
        if not plan:
            raise HTTPException(422, '该工作流尚未开放积分生成，请选择已接入的工作流')
        if plan.get('reference_required') and not body.image:
            raise HTTPException(422, '此工作流需要参考图，请先上传或选择U03文生视频')
        template = json.loads(json.dumps(plan['workflow_template']))
        config = template['_api_config']
        values = dict(plan['input_values'])
        refs = []
        prompt_set = False
        for key, enabled in config.get('enabledParams', {}).items():
            if not enabled:
                continue
            node, field = key.split(':', 1)
            alias = config.get('apiNames', {}).get(key, field)
            value = values.get(alias, config.get('formValues', {}).get(key))
            if field.startswith('ref_') or field in ('image', 'video', 'audio', 'image_path', 'video_path'):
                value = (body.image or '') if ('image' in field and not refs) else ''
                refs.append(key)
                if value and not self.accounts.rows("SELECT 1 FROM media WHERE user_id=? AND path=? AND kind='input'", (user['id'], value)):
                    raise HTTPException(403, '参考素材不属于当前账号，请重新上传')
                if not value and not field.startswith('ref_'):
                    raise HTTPException(422, '此工作流需要参考图，请先上传')
            elif field in ('prompt', 'text', 'positive') and not prompt_set:
                value, prompt_set = body.prompt, True
            if not plan.get('duration_key') and field in ('aspect_ratio', 'megapixels'):
                value = getattr(body, field) if getattr(body, field) is not None else value
            if plan.get('duration_key') == key:
                value = str(body.seconds) if isinstance(value, str) else body.seconds
            values[alias] = value
            template[node]['inputs'][field] = value
            config.setdefault('formValues', {})[key] = value
        if not prompt_set:
            raise HTTPException(422, '此工作流的提示词字段尚未接入')
        for key in plan.get('image_slots', []):
            if not body.image:
                raise HTTPException(422, '此工作流需要参考图，请先上传')
            if not self.accounts.rows("SELECT 1 FROM media WHERE user_id=? AND path=? AND kind='input'", (user['id'], body.image)):
                raise HTTPException(403, '参考图不属于当前账号')
            node, field = key.split(':', 1)
            template[node]['inputs'][field] = body.image
            config.setdefault('formValues', {})[key] = body.image
        duration = plan.get('duration_key')
        if duration:
            node, field = duration.split(':', 1)
            value = str(body.seconds) if isinstance(template[node]['inputs'][field], str) else body.seconds
            template[node]['inputs'][field] = value
            config['formValues'][duration] = value
            values[config.get('apiNames', {}).get(duration, field)] = value
        seconds = body.seconds if duration else 0
        return {'workflow_id': plan.get('submit_workflow_id', plan['id']), 'workflow_template': template,
                'input_values': values, 'source': 'api', 'client_id': 'lichtv-' + user['id']}, seconds

    def publish(self, job, result):
        def transform(value):
            if isinstance(value, list):
                return [transform(item) for item in value]
            if isinstance(value, dict):
                return {key: transform(item) for key, item in value.items()}
            if isinstance(value, str) and (value.startswith('/output/') or value.startswith('/api/comfy/view')):
                media = self.accounts.media(job['user_id'], value, 'output', job['id'])
                return '/studio-api/accounts/media/' + media['id']
            return value
        return transform(result)

    def worker(self):
        # A crash between submission and storing prompt_id is deliberately held
        # for review; replaying would risk a second paid GPU execution.
        with self.accounts.transaction() as db:
            db.execute("UPDATE jobs SET status='review',error='提交时服务重启，需管理员核对GPU任务后处理' WHERE status='submitting'")
        while not self.stop.is_set():
            try:
                rows = self.accounts.rows("SELECT * FROM jobs WHERE status='running' ORDER BY created_at LIMIT 1")
                if not rows:
                    queue = self.upstream('/api/comfy/proxy/queue')
                    if queue.get('queue_running') or queue.get('queue_pending'):
                        self.stop.wait(3)
                        continue
                    # Review holds block later work until the ambiguous GPU
                    # submission is reconciled, preventing duplicate dispatch.
                    with self.accounts.transaction() as db:
                        if db.execute("SELECT 1 FROM jobs WHERE status IN ('submitting','review')").fetchone():
                            job = None
                        else:
                            row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
                            job = dict(row) if row else None
                            if job:
                                db.execute("UPDATE jobs SET status='submitting',updated_at=? WHERE id=?", (time.time(), job['id']))
                    if job:
                        try:
                            response = self.upstream('/api/workflow/generate', json.loads(job['payload']), timeout=180)
                            prompt_id = response.get('prompt_id')
                            if not prompt_id:
                                if response.get('error') or response.get('success') is False:
                                    self.accounts.finish(job['id'], False, error='生成服务拒绝了任务')
                                else:
                                    self.review(job['id'], '生成服务未返回任务号，需核对GPU队列')
                            else:
                                with self.accounts.transaction() as db:
                                    db.execute("UPDATE jobs SET status='running',prompt_id=?,updated_at=? WHERE id=?", (prompt_id, time.time(), job['id']))
                        except urllib.error.HTTPError as error:
                            if 400 <= error.code < 500:
                                self.accounts.finish(job['id'], False, error=f'生成服务拒绝请求（HTTP {error.code}），积分已退回')
                            else:
                                self.review(job['id'], '提交响应异常，需核对GPU队列')
                        except Exception:
                            self.review(job['id'], '提交连接中断，需核对GPU队列；积分暂保留')
                else:
                    job = rows[0]
                    result = self.upstream('/api/workflow/result?prompt_id=' + urllib.parse.quote(job['prompt_id']))
                    if result.get('error') or result.get('status') in ('failed', 'error'):
                        self.accounts.finish(job['id'], False, error='工作流执行失败，积分已退回')
                    elif result.get('pending') is False:
                        outputs = result.get('results') or result.get('outputs')
                        if outputs:
                            self.accounts.finish(job['id'], True, self.publish(job, result))
                        else:
                            self.accounts.finish(job['id'], False, error='任务没有产出文件，积分已退回')
            except Exception:
                # Transient tunnel/poll errors do not cancel a running GPU task.
                pass
            self.wake.wait(3)
            self.wake.clear()

    def review(self, job_id, reason):
        with self.accounts.transaction() as db:
            db.execute("UPDATE jobs SET status='review',error=?,updated_at=? WHERE id=?", (reason, time.time(), job_id))


def install(app, root, panel, catalog=None, start_worker=True):
    accounts = Accounts(root)
    runtime = Runtime(accounts, panel, catalog or Path(root) / 'workflow-catalog.json')
    app.state.accounts, app.state.account_runtime = accounts, runtime

    def user(request):
        result = accounts.authenticate(request.cookies.get(COOKIE))
        if not result:
            raise HTTPException(401, '请先登录或注册')
        return result

    def admin(request):
        result = user(request)
        if result['role'] != 'admin':
            raise HTTPException(403, '需要管理员权限')
        return result

    @app.middleware('http')
    async def identity(request: Request, call_next):
        notification = request.url.path in ('/payments/notify/alipay', '/payments/notify/wechatpay')
        public = notification or request.url.path in ('/health', '/accounts/login', '/accounts/register', '/accounts/public')
        identity = accounts.authenticate(request.cookies.get(COOKIE))
        if not public and not request.url.path.startswith('/gateway/') and not identity:
            return JSONResponse({'detail': '请先登录或注册'}, status_code=401)
        if not notification and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            host = request.headers.get('x-forwarded-host') or request.headers.get('host')
            if origin and urllib.parse.urlsplit(origin).netloc != host:
                return JSONResponse({'detail': '请求来源不匹配，请刷新页面'}, status_code=403)
            if not public and (not identity or not hmac.compare_digest(identity['csrf'], request.headers.get('x-lichtv-csrf', ''))):
                return JSONResponse({'detail': '登录状态已变化，请刷新页面'}, status_code=403)
        token = CURRENT_USER.set(identity)
        try:
            response = await call_next(request)
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response
        finally:
            CURRENT_USER.reset(token)

    @app.get('/accounts/public')
    def public():
        count = accounts.rows("SELECT value FROM counters WHERE name='registrations'")[0]['value']
        return {'packages': PACKAGES, 'credits_per_second': 2, 'bonus_credits': 1_000_000,
                'bonus_places_remaining': max(0, 100 - count),
                'payment_mode': 'online_and_manual' if app.state.payments.providers else 'manual_confirmation',
                'payment_channels': app.state.payments.channels()}

    def session_response(request, account):
        token, csrf = accounts.new_session(account['id'])
        response = JSONResponse({'user': accounts.public(account), 'csrf': csrf})
        secure = (request.headers.get('x-forwarded-proto') or request.url.scheme) == 'https'
        response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, secure=secure, samesite='lax', path='/')
        return response

    @app.post('/accounts/register')
    def register(body: Credentials, request: Request):
        accounts.limit('register:' + (request.headers.get('x-real-ip') or request.client.host), 10, 3600)
        return session_response(request, accounts.register(body.username, body.password))

    @app.post('/accounts/login')
    def login(body: Credentials, request: Request):
        key = body.username.strip().casefold()
        accounts.limit('login:' + key, 20, 900)
        accounts.limit('login-ip:' + (request.headers.get('x-real-ip') or request.client.host), 100, 900)
        found = accounts.rows('SELECT * FROM users WHERE normalized=?', (key,))
        if not found or not password_valid(body.password, found[0]['password']) or found[0]['status'] != 'active':
            raise HTTPException(401, '账号或密码错误，或账号已停用')
        return session_response(request, found[0])

    @app.get('/accounts/me')
    def me(request: Request):
        account = user(request)
        return {'user': accounts.public(account), 'csrf': account['csrf']}

    @app.post('/accounts/logout')
    def logout(request: Request):
        with accounts.transaction() as db:
            db.execute('DELETE FROM sessions WHERE token=?', (digest(request.cookies.get(COOKIE, '')),))
        response = JSONResponse({'ok': True})
        response.delete_cookie(COOKIE, path='/')
        return response

    @app.post('/accounts/password')
    def change_password(body: PasswordChange, request: Request):
        account = user(request)
        accounts.limit('password:' + account['id'], 10, 900)
        if not password_valid(body.current_password, account['password']):
            raise HTTPException(401, '当前密码不正确')
        encoded = password_hash(body.new_password)
        with accounts.transaction() as db:
            db.execute('UPDATE users SET password=? WHERE id=?', (encoded, account['id']))
            db.execute('DELETE FROM sessions WHERE user_id=?', (account['id'],))
        response = JSONResponse({'ok': True, 'message': '密码已修改，请重新登录'})
        response.delete_cookie(COOKIE, path='/')
        return response

    @app.get('/accounts/wallet')
    def wallet(request: Request):
        account = user(request)
        return {'user': accounts.public(account), 'packages': PACKAGES,
                'ledger': accounts.rows('SELECT * FROM ledger WHERE user_id=? ORDER BY id DESC LIMIT 100', (account['id'],)),
                'orders': [app.state.payments.public_order(row) for row in accounts.rows('SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 100', (account['id'],))],
                'payment_channels': app.state.payments.channels()}

    @app.post('/accounts/orders')
    def create_order(body: OrderInput, request: Request):
        account = user(request)
        package = next((item for item in PACKAGES if item['id'] == body.package_id), None)
        if not package:
            raise HTTPException(422, '套餐不存在')
        accounts.limit('orders:' + account['id'], 20, 3600)
        return app.state.payments.create(account['id'], package, body.channel, body.idempotency_key)

    @app.get('/accounts/admin')
    def dashboard(request: Request):
        admin(request)
        return {'users': [accounts.public(row) for row in accounts.rows('SELECT * FROM users ORDER BY created_at DESC')],
                'orders': accounts.rows('SELECT o.*,u.username FROM orders o JOIN users u ON o.user_id=u.id ORDER BY o.created_at DESC LIMIT 200'),
                'review_jobs': [accounts.job_public(row) for row in accounts.rows("SELECT * FROM jobs WHERE status='review'")],
                'ledger': accounts.rows('SELECT l.*,u.username FROM ledger l JOIN users u ON l.user_id=u.id ORDER BY l.id DESC LIMIT 200')}

    @app.post('/accounts/admin/orders/{order_id}/confirm')
    def confirm_order(order_id: str, body: ConfirmInput, request: Request):
        actor = admin(request)
        if not body.verified_received:
            raise HTTPException(422, '必须先核实实际收款')
        accounts.confirm_order(actor, order_id, body.receipt)
        return {'ok': True}

    @app.post('/accounts/admin/users/{user_id}/adjust')
    def adjust(user_id: str, body: Adjustment, request: Request):
        actor = admin(request)
        with accounts.transaction() as db:
            if not db.execute('SELECT 1 FROM users WHERE id=?', (user_id,)).fetchone():
                raise HTTPException(404, '账号不存在')
            reference = 'adjust:' + actor['id'] + ':' + body.idempotency_key
            old = db.execute('SELECT * FROM ledger WHERE reference=?', (reference,)).fetchone()
            if old and (old['user_id'] != user_id or old['delta'] != body.delta or old['reason'] != body.reason):
                raise HTTPException(409, '调整标识与之前操作不一致')
            accounts.change(db, user_id, body.delta, 'admin_adjustment', reference, body.reason, actor['id'])
        return {'ok': True}

    @app.post('/accounts/admin/users/{user_id}/status')
    def status(user_id: str, body: StatusInput, request: Request):
        actor = admin(request)
        if actor['id'] == user_id or body.status not in ('active', 'disabled'):
            raise HTTPException(422, '不能停用当前管理员；状态只能是active或disabled')
        with accounts.transaction() as db:
            if not db.execute("UPDATE users SET status=? WHERE id=? AND role='member' RETURNING id", (body.status, user_id)).fetchone():
                raise HTTPException(404, '普通账号不存在')
            if body.status == 'disabled':
                db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
                for job in db.execute("SELECT * FROM jobs WHERE user_id=? AND status='queued'", (user_id,)).fetchall():
                    accounts.change(db, user_id, job['cost'], 'refund', 'refund:' + job['id'], '账号停用，未开始任务取消')
                    db.execute("UPDATE jobs SET status='cancelled',updated_at=? WHERE id=?", (time.time(), job['id']))
        return {'ok': True}

    @app.get('/accounts/workflows')
    def workflows(request: Request):
        user(request)
        return {'items': [{'id': item['id'], 'category': item['category'], 'credits_per_second': 2 if item.get('duration_key') else 0,
                           'reference_required': item.get('reference_required', False)} for item in runtime.catalog]}

    @app.post('/accounts/jobs')
    def generate(body: Generation, request: Request):
        account = user(request)
        payload, seconds = runtime.prepare(body, account)
        job = accounts.create_job(account, body.model_dump(), payload, seconds)
        runtime.wake.set()
        return job

    @app.get('/accounts/jobs')
    def jobs(request: Request):
        account = user(request)
        return {'items': [accounts.job_public(row) for row in accounts.rows('SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC LIMIT 100', (account['id'],))],
                'queue_size': accounts.rows("SELECT count(*) AS n FROM jobs WHERE status IN ('queued','running','submitting','review')")[0]['n']}

    @app.post('/accounts/jobs/{job_id}/cancel')
    def cancel(job_id: str, request: Request):
        account = user(request)
        with accounts.transaction() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=? AND user_id=?', (job_id, account['id'])).fetchone()
            if not row:
                raise HTTPException(404, '任务不存在')
            if row['status'] == 'cancelled':
                return {'ok': True}
            if row['status'] != 'queued':
                raise HTTPException(409, '任务已开始，不能取消其他用户共用的GPU进程')
            accounts.change(db, account['id'], row['cost'], 'refund', 'refund:' + job_id, '排队任务取消')
            db.execute("UPDATE jobs SET status='cancelled',updated_at=? WHERE id=?", (time.time(), job_id))
        return {'ok': True}

    @app.post('/accounts/admin/jobs/{job_id}/resolve')
    async def resolve(job_id: str, request: Request):
        admin(request)
        body = await request.json()
        rows = accounts.rows("SELECT * FROM jobs WHERE id=? AND status='review'", (job_id,))
        if not rows:
            raise HTTPException(409, '该任务不处于待核对状态')
        if body.get('prompt_id') and re.fullmatch(r'[\w-]{16,80}', body['prompt_id']):
            with accounts.transaction() as db:
                db.execute("UPDATE jobs SET status='running',prompt_id=?,error=NULL,updated_at=? WHERE id=?", (body['prompt_id'], time.time(), job_id))
        elif body.get('confirmed_not_running') is True:
            accounts.finish(job_id, False, error='管理员核实未执行，积分已退回')
        else:
            raise HTTPException(422, '请提供GPU任务号，或核实任务没有运行后退款')
        return {'ok': True}

    @app.post('/accounts/upload')
    async def upload(request: Request, file: UploadFile = File(...)):
        account = user(request)
        content = await file.read(20 * 1024 * 1024 + 1)
        extension = Path(file.filename or '').suffix.lower()
        if len(content) > 20 * 1024 * 1024 or extension not in ('.png', '.jpg', '.jpeg', '.webp'):
            raise HTTPException(422, '请上传20MiB以内的PNG、JPG或WebP参考图')
        from PIL import Image
        import io
        try:
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
        except Exception:
            raise HTTPException(422, '无法读取该图片') from None
        filename = 'lichtv_' + account['id'] + '_' + secrets.token_hex(12) + extension
        boundary = 'LichTV' + secrets.token_hex(16)
        data = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
                + content + f'\r\n--{boundary}--\r\n'.encode())
        req = urllib.request.Request(runtime.panel + '/api/comfy/upload/file', data=data,
                                     headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.load(response)
        except Exception:
            raise HTTPException(502, '参考图上传失败，请检查GPU连接') from None
        name = (result.get('subfolder', '').strip('/') + '/' + result['name']).lstrip('/')
        # Input references are intentionally stored as the exact Comfy filename.
        with accounts.transaction() as db:
            db.execute("INSERT INTO media VALUES(?,?,?,'input',NULL)", (secrets.token_hex(16), account['id'], name))
        return {'name': name}

    @app.get('/accounts/media/{media_id}')
    def download_media(media_id: str, request: Request):
        account = user(request)
        rows = accounts.rows("SELECT * FROM media WHERE id=? AND user_id=? AND kind='output'", (media_id, account['id']))
        if not rows:
            raise HTTPException(404, '文件不存在')
        req = urllib.request.Request(runtime.panel + media_path(rows[0]['path']), headers={key: request.headers[key] for key in ('range',) if key in request.headers})
        try:
            response = urllib.request.urlopen(req, timeout=120)
        except Exception:
            raise HTTPException(502, '文件读取失败，请检查GPU连接') from None
        def chunks():
            try:
                while block := response.read(256 * 1024):
                    yield block
            finally:
                response.close()
        headers = {key: response.headers[key] for key in ('Content-Length', 'Content-Range', 'Accept-Ranges') if response.headers.get(key)}
        return StreamingResponse(chunks(), status_code=response.status, media_type=response.headers.get('Content-Type', 'application/octet-stream'), headers=headers)

    @app.api_route('/gateway/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD'])
    async def gateway(path: str, request: Request):
        # This is the only public bridge to the original panel. Graph submission,
        # concurrent/mirror APIs and raw Comfy prompt endpoints are never exposed.
        path = '/' + path
        if request.method == 'POST' and path == '/api/workflow/generate':
            account = user(request)
            body = await request.json()
            if set(body) - {'workflow_id', 'input_values', 'source', 'client_id', 'idempotency_key'}:
                raise HTTPException(422, '不接受客户端工作流模板，请使用服务端预设')
            plan = next((item for item in runtime.catalog if item['id'] == body.get('workflow_id')), None)
            if not plan:
                raise HTTPException(422, '工作流未开放')
            values = body.get('input_values') or {}
            if not isinstance(values, dict):
                raise HTTPException(422, '工作流参数必须为对象')
            config = plan['workflow_template']['_api_config']
            allowed = {config.get('apiNames', {}).get(key, key) for key, on in config['enabledParams'].items() if on}
            if set(values) - allowed:
                raise HTTPException(422, '包含未开放的工作流参数')
            prompt, image, seconds = '', None, 5
            options = {}
            for key, enabled in config['enabledParams'].items():
                if not enabled:
                    continue
                field = key.split(':', 1)[1]
                alias = config.get('apiNames', {}).get(key, key)
                if alias not in values:
                    continue
                if field in ('prompt', 'text', 'positive') and not prompt:
                    prompt = values[alias]
                if field.startswith('ref_image_') or field == 'image':
                    if values[alias]:
                        if image:
                            raise HTTPException(422, '当前账号入口一次支持一张参考图')
                        image = values[alias]
                if not plan.get('duration_key') and field in ('aspect_ratio', 'megapixels'):
                    options[field] = values[alias]
                if key == plan.get('duration_key'):
                    seconds = values[alias]
            try:
                model = Generation(workflow_id=plan['id'], prompt=prompt, image=image, seconds=seconds, **options,
                                   idempotency_key=body.get('idempotency_key') or body.get('client_id') or secrets.token_hex(16))
            except ValueError:
                raise HTTPException(422, '请检查提示词、秒数与参考图') from None
            payload, seconds = runtime.prepare(model, account)
            job = accounts.create_job(account, model.model_dump(), payload, seconds)
            runtime.wake.set()
            return {'prompt_id': job['id'], 'metered': True, 'cost': job['cost']}
        if request.method != 'GET':
            raise HTTPException(403, '请使用积分生成入口，旧任务写入接口已关闭')
        if path == '/config.json':
            return {'appName': 'LichTV', 'qqGroups': []}
        if path == '/api/comfy/status':
            try:
                result = runtime.upstream(path)
                return {'running': bool(result.get('running'))}
            except Exception:
                return {'running': False}
        account = user(request)
        if path == '/api/workflow/result':
            job_id = request.query_params.get('prompt_id')
            rows = accounts.rows('SELECT * FROM jobs WHERE id=? AND user_id=?', (job_id, account['id']))
            if not rows:
                raise HTTPException(404, '任务不存在')
            job = rows[0]
            if job['status'] == 'done':
                return json.loads(job['result'])
            if job['status'] in ('failed', 'cancelled'):
                return {'pending': False, 'error': job['error'] or '任务已取消'}
            return {'pending': True, 'status': job['status']}
        if path == '/api/h3-canvas':
            store = Path(root) / 'users' / account['id'] / 'canvas.json'
            return json.loads(store.read_text()) if store.exists() else {'files': {'canvas': {'projects': []}}}
        if path == '/api/workflow/list':
            return {'workflows': [{'id': item['id'], 'name': item['id'], 'category': item['category']} for item in runtime.catalog]}
        if path.startswith('/api/workflow/config/'):
            workflow_id = urllib.parse.unquote(path.removeprefix('/api/workflow/config/'))
            plan = next((item for item in runtime.catalog if item['id'] == workflow_id), None)
            if plan:
                return {'api_config': plan['workflow_template']['_api_config'] | {'formValues': {}}, 'requires_metered_queue': True}
        if path in ('/api/tasks', '/api/images'):
            return {'items': []}
        raise HTTPException(403, '该接口未向用户开放，请使用账号内的创作入口')

    from studio_payments import install as install_payments
    install_payments(app, accounts, user, admin, start_worker=start_worker)

    if start_worker:
        @app.on_event('startup')
        def start():
            threading.Thread(target=runtime.worker, name='lichtv-metered-gpu', daemon=True).start()

        @app.on_event('shutdown')
        def stop():
            runtime.stop.set()
            runtime.wake.set()
    return accounts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bootstrap one operator account (excluded from first-100 promotion).')
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--username', default='admin')
    parser.add_argument('--credential-file', type=Path, required=True)
    args = parser.parse_args()
    accounts = Accounts(args.data_dir)
    if accounts.rows("SELECT 1 FROM users WHERE role='admin'"):
        raise SystemExit('An administrator already exists; no changes made')
    password = secrets.token_urlsafe(18)
    account = accounts.register(args.username, password, admin=True)
    args.credential_file.write_text(json.dumps({'username': args.username, 'password': password, 'user_id': account['id']}, indent=2))
    args.credential_file.chmod(0o600)
    print('Administrator created. Credentials written to the private file.')

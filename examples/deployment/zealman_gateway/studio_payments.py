"""Alipay RSA2 and WeChat Pay APIv3 Native payments for the credit ledger.

Merchant keys are loaded from a private server file, never a web request.
Provider responses and callbacks are verified before business data is used.
"""
import base64
import datetime
from decimal import Decimal, InvalidOperation
import io
import ipaddress
import json
import logging
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from starlette.concurrency import run_in_threadpool
import qrcode

LOGGER = logging.getLogger('lichtv.payments')
CHANNEL_NAMES = {'alipay': '支付宝', 'wechatpay': '微信支付', 'manual': '人工核实收款'}
NOTIFY_PATHS = {'/payments/notify/alipay', '/payments/notify/wechatpay'}
MAX_BODY = 128 * 1024


class PaymentError(Exception):
    """A deliberately generic, non-secret-bearing provider error."""


class SignatureError(PaymentError):
    pass


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PaymentError('Duplicate JSON field')
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise PaymentError('Invalid JSON') from None


def cents(value):
    try:
        amount = Decimal(str(value)) * 100
        if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
            raise ValueError()
        return int(amount)
    except (ValueError, InvalidOperation):
        raise PaymentError('Invalid payment amount') from None


def sign(key, content):
    return base64.b64encode(key.sign(content, padding.PKCS1v15(), hashes.SHA256())).decode()


def verify(key, content, signature):
    try:
        key.verify(base64.b64decode(signature, validate=True), content, padding.PKCS1v15(), hashes.SHA256())
    except Exception:
        raise SignatureError('Payment signature rejected') from None


def read_key(config, name, directory, private=False):
    path = Path(config[name])
    if not path.is_absolute():
        path = directory / path
    raw = path.read_bytes()
    if private:
        key = serialization.load_pem_private_key(raw, password=None)
    elif b'BEGIN CERTIFICATE' in raw:
        certificate = x509.load_pem_x509_certificate(raw)
        now = datetime.datetime.now(datetime.timezone.utc)
        if not certificate.not_valid_before_utc <= now <= certificate.not_valid_after_utc:
            raise ValueError('Expired payment certificate')
        key = certificate.public_key()
    else:
        key = serialization.load_pem_public_key(raw)
    if not isinstance(key, rsa.RSAPrivateKey if private else rsa.RSAPublicKey) or key.key_size < 2048:
        raise ValueError('Payment keys must be RSA 2048 bits or stronger')
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def exchange(request):
    """Keep HTTP error bodies for signature checking; never follow redirects."""
    try:
        response = urllib.request.build_opener(NoRedirect).open(request, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    except OSError:
        raise PaymentError('Payment connection failed; query before retrying') from None
    with response:
        body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise PaymentError('Payment response too large')
        return response.status, dict(response.headers), body


def alipay_content(parameters, callback=False):
    excluded = {'sign', 'sign_type'} if callback else {'sign'}
    return '&'.join(f'{key}={parameters[key]}' for key in sorted(parameters)
                    if key not in excluded and parameters[key] not in (None, '')).encode()


def raw_json_member(raw, wanted):
    """Extract the exact signed response object without re-serializing JSON."""
    text = raw.decode('utf-8')
    decoder = json.JSONDecoder()
    index = 0
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != '{':
        raise PaymentError('Invalid Alipay response')
    index += 1
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if text[index:index+1] == '}':
            break
        key, index = decoder.raw_decode(text, index)
        while index < len(text) and text[index].isspace():
            index += 1
        if text[index:index+1] != ':':
            raise PaymentError('Invalid Alipay response')
        index += 1
        while index < len(text) and text[index].isspace():
            index += 1
        start = index
        _, index = decoder.raw_decode(text, index)
        if key == wanted:
            return text[start:index].encode()
        while index < len(text) and text[index].isspace():
            index += 1
        if text[index:index+1] != ',':
            break
        index += 1
    raise PaymentError('Missing Alipay response object')


class Alipay:
    channel = 'alipay'

    def __init__(self, config, directory, base_url):
        self.app_id, self.seller_id = config['app_id'], config['seller_id']
        if not re.fullmatch(r'\d{8,32}', self.app_id) or not re.fullmatch(r'\d{8,32}', self.seller_id):
            raise ValueError('Invalid Alipay identifiers')
        self.private = read_key(config, 'private_key_file', directory, private=True)
        self.public = read_key(config, 'alipay_public_key_file', directory)
        self.notify_url = base_url + '/studio-api/payments/notify/alipay'

    def call(self, method, business):
        parameters = {'app_id': self.app_id, 'method': method, 'format': 'JSON', 'charset': 'utf-8',
                      'sign_type': 'RSA2', 'timestamp': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
                      'version': '1.0', 'biz_content': json.dumps(business, ensure_ascii=False, separators=(',', ':'))}
        if method == 'alipay.trade.precreate':
            parameters['notify_url'] = self.notify_url
        parameters['sign'] = sign(self.private, alipay_content(parameters))
        status, _, raw = exchange(urllib.request.Request('https://openapi.alipay.com/gateway.do',
                      data=urllib.parse.urlencode(parameters).encode(), headers={'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'}))
        result = strict_json(raw)
        key = method.replace('.', '_') + '_response'
        verify(self.public, raw_json_member(raw, key), result.get('sign', ''))
        response = result[key]
        if status != 200 or response.get('code') != '10000':
            if method == 'alipay.trade.query' and response.get('sub_code') == 'ACQ.TRADE_NOT_EXIST':
                return {'trade_status': 'NOT_EXIST'}
            raise PaymentError('Alipay rejected this request')
        return response

    def create(self, order):
        response = self.call('alipay.trade.precreate', {'out_trade_no': order['id'],
                    'total_amount': f"{order['price_cents'] // 100}.{order['price_cents'] % 100:02d}",
                    'subject': f"LichTV {order['credits']}积分", 'timeout_express': '30m'})
        if response.get('out_trade_no') != order['id']:
            raise PaymentError('Alipay order mismatch')
        url = response['qr_code']
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or not (parsed.hostname == 'alipay.com' or parsed.hostname.endswith('.alipay.com')):
            raise PaymentError('Invalid Alipay QR URL')
        return url

    def transaction(self, result, notification=False):
        if notification:
            if result.get('app_id') != self.app_id or result.get('seller_id') != self.seller_id:
                raise PaymentError('Alipay merchant mismatch')
        elif result.get('seller_id', self.seller_id) != self.seller_id:
            raise PaymentError('Alipay merchant mismatch')
        state = result.get('trade_status')
        return {'channel': self.channel, 'order_id': result.get('out_trade_no'),
                'paid': state in ('TRADE_SUCCESS', 'TRADE_FINISHED'), 'state': state,
                'transaction_id': result.get('trade_no'), 'price_cents': cents(result['total_amount']) if state in ('TRADE_SUCCESS', 'TRADE_FINISHED') else None,
                'currency': 'CNY', 'merchant': self.seller_id}

    def query(self, order):
        return self.transaction(self.call('alipay.trade.query', {'out_trade_no': order['id']}))

    def notify(self, headers, body):
        try:
            pairs = urllib.parse.parse_qsl(body.decode('utf-8'), keep_blank_values=True, max_num_fields=100, errors='strict')
        except (ValueError, UnicodeError):
            raise PaymentError('Invalid Alipay notification') from None
        parameters = dict(pairs)
        if len(parameters) != len(pairs) or parameters.get('sign_type') != 'RSA2':
            raise SignatureError('Invalid Alipay signing parameters')
        verify(self.public, alipay_content(parameters, callback=True), parameters.get('sign', ''))
        return self.transaction(parameters, notification=True)


class Wechatpay:
    channel = 'wechatpay'

    def __init__(self, config, directory, base_url):
        self.app_id, self.mch_id, self.serial = config['app_id'], config['mch_id'], config['merchant_serial']
        if not re.fullmatch(r'wx[\w]{8,32}', self.app_id) or not re.fullmatch(r'\d{6,32}', self.mch_id) or not re.fullmatch(r'[\da-fA-F]{16,64}', self.serial):
            raise ValueError('Invalid WeChat Pay identifiers')
        self.private = read_key(config, 'private_key_file', directory, private=True)
        key_file = Path(config['api_v3_key_file'])
        self.api_key = (key_file if key_file.is_absolute() else directory / key_file).read_bytes().strip()
        if len(self.api_key) != 32:
            raise ValueError('WeChat APIv3 key must contain exactly 32 bytes')
        self.public_keys = {}
        for serial, path in config['platform_public_keys'].items():
            if not re.fullmatch(r'(?:PUB_KEY_ID_\d+|[\da-fA-F]{16,64})', serial):
                raise ValueError('Invalid WeChat public key identifier')
            self.public_keys[serial] = read_key({'path': path}, 'path', directory)
        if not self.public_keys:
            raise ValueError('Missing WeChat verification keys')
        self.notify_url = base_url + '/studio-api/payments/notify/wechatpay'

    def verify_response(self, headers, body):
        headers = {key.lower(): value for key, value in headers.items()}
        try:
            timestamp, nonce = headers['wechatpay-timestamp'], headers['wechatpay-nonce']
            key = self.public_keys[headers['wechatpay-serial']]
            if abs(time.time() - int(timestamp)) > 300:
                raise ValueError()
            content = timestamp.encode() + b'\n' + nonce.encode() + b'\n' + body + b'\n'
            verify(key, content, headers['wechatpay-signature'])
        except (KeyError, ValueError, UnicodeError):
            raise SignatureError('WeChat timestamp or key rejected') from None

    def call(self, method, path, payload=None):
        body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode() if payload is not None else b''
        timestamp, nonce = str(int(time.time())), secrets.token_hex(16)
        content = f'{method}\n{path}\n{timestamp}\n{nonce}\n'.encode() + body + b'\n'
        signature = sign(self.private, content)
        authorization = f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mch_id}",nonce_str="{nonce}",timestamp="{timestamp}",serial_no="{self.serial}",signature="{signature}"'
        status, headers, raw = exchange(urllib.request.Request('https://api.mch.weixin.qq.com' + path,
                  data=body if payload is not None else None, method=method,
                  headers={'Authorization': authorization, 'Content-Type': 'application/json', 'Accept': 'application/json',
                           'Wechatpay-Serial': next(iter(self.public_keys))}))
        self.verify_response(headers, raw)
        result = strict_json(raw)
        if not 200 <= status < 300:
            if status == 404 and result.get('code') == 'ORDER_NOT_EXIST':
                return {'trade_state': 'NOT_EXIST'}
            raise PaymentError('WeChat Pay rejected this request')
        return result

    def create(self, order):
        expiry = datetime.datetime.fromtimestamp(order['expires_at'], datetime.timezone.utc).isoformat(timespec='seconds')
        result = self.call('POST', '/v3/pay/transactions/native', {'appid': self.app_id, 'mchid': self.mch_id,
                    'description': f"LichTV {order['credits']}积分", 'out_trade_no': order['id'],
                    'time_expire': expiry, 'notify_url': self.notify_url, 'amount': {'total': order['price_cents'], 'currency': 'CNY'}})
        url = result['code_url']
        if not isinstance(url, str) or not url.startswith('weixin://') or len(url) > 2048:
            raise PaymentError('Invalid WeChat Pay QR URL')
        return url

    def transaction(self, result):
        state = result.get('trade_state')
        if state != 'NOT_EXIST' and (result.get('appid') != self.app_id or result.get('mchid') != self.mch_id):
            raise PaymentError('WeChat merchant mismatch')
        amount = result.get('amount', {})
        total = amount.get('total')
        if state == 'SUCCESS' and (type(total) is not int or total < 0):
            raise PaymentError('Invalid WeChat amount')
        return {'channel': self.channel, 'order_id': result.get('out_trade_no'), 'paid': state == 'SUCCESS',
                'state': state, 'transaction_id': result.get('transaction_id'), 'price_cents': total,
                'currency': amount.get('currency'), 'merchant': self.mch_id}

    def query(self, order):
        result = self.call('GET', '/v3/pay/transactions/out-trade-no/' + urllib.parse.quote(order['id'], safe='') + '?mchid=' + self.mch_id)
        return self.transaction(result)

    def notify(self, headers, body):
        self.verify_response(headers, body)
        try:
            envelope = strict_json(body)
            resource = envelope['resource']
            if envelope['event_type'] != 'TRANSACTION.SUCCESS' or resource['algorithm'] != 'AEAD_AES_256_GCM' or resource.get('original_type') != 'transaction':
                raise PaymentError('Unexpected WeChat notification')
            plain = AESGCM(self.api_key).decrypt(resource['nonce'].encode(),
                       base64.b64decode(resource['ciphertext'], validate=True), resource.get('associated_data', '').encode())
            transaction = self.transaction(strict_json(plain))
            if not transaction['paid']:
                raise PaymentError('Unexpected WeChat payment state')
            return transaction
        except PaymentError:
            raise
        except Exception:
            raise PaymentError('WeChat notification decryption failed') from None


class Payments:
    def __init__(self, accounts, config_path=None):
        self.accounts = accounts
        self.config_path = Path(config_path or accounts.root.parent / 'private' / 'payments.json')
        self.providers = {}
        self.configuration = {}
        self.stop = threading.Event()
        self.migrate()
        self.load()

    def migrate(self):
        with self.accounts.transaction() as db:
            columns = {row['name'] for row in db.execute('PRAGMA table_info(orders)')}
            for name, definition in {'channel': "TEXT NOT NULL DEFAULT 'manual'", 'payment_request_key': 'TEXT',
                    'expires_at': 'REAL', 'payment_url': 'TEXT', 'payment_state': 'TEXT', 'payment_error': 'TEXT',
                    'payment_lock_until': 'REAL NOT NULL DEFAULT 0', 'query_after': 'REAL NOT NULL DEFAULT 0'}.items():
                if name not in columns:
                    db.execute(f'ALTER TABLE orders ADD COLUMN {name} {definition}')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS payment_request_key ON orders(user_id,payment_request_key) WHERE payment_request_key IS NOT NULL')
            db.execute('''CREATE TABLE IF NOT EXISTS payment_receipts(
                channel TEXT NOT NULL,transaction_id TEXT NOT NULL,order_id TEXT UNIQUE NOT NULL,
                price_cents INTEGER NOT NULL,currency TEXT NOT NULL,merchant TEXT NOT NULL,
                verified_at REAL NOT NULL,PRIMARY KEY(channel,transaction_id))''')

    def load(self):
        try:
            config = strict_json(self.config_path.read_bytes()) if self.config_path.exists() else {}
        except (OSError, PaymentError):
            config = {}
        if not isinstance(config, dict):
            config = {}
        base = config.get('public_base_url', '')
        base = base.rstrip('/') if isinstance(base, str) else ''
        parsed = urllib.parse.urlsplit(base)
        valid_base = parsed.scheme == 'https' and parsed.hostname and not (parsed.username or parsed.query or parsed.fragment)
        try:
            ipaddress.ip_address(parsed.hostname or '')
            valid_base = False
        except ValueError:
            pass
        for name, factory in [('alipay', Alipay), ('wechatpay', Wechatpay)]:
            entry = config.get(name, {})
            if not isinstance(entry, dict) or entry.get('enabled') is not True:
                self.configuration[name] = '待配置商户资料'
                continue
            if not valid_base:
                self.configuration[name] = '需要可公开访问的HTTPS域名与回调地址'
                continue
            try:
                self.providers[name] = factory(entry, self.config_path.parent, base)
                self.configuration[name] = '已配置；以支付平台实际权限为准'
            except Exception:
                self.configuration[name] = '商户资料或密钥未配置完整，请联系管理员'

    def channels(self):
        return [{'id': name, 'name': CHANNEL_NAMES[name], 'enabled': name in self.providers,
                 'message': self.configuration.get(name, '待配置商户资料')} for name in ('alipay', 'wechatpay')]

    def order(self, order_id, user_id=None):
        rows = self.accounts.rows('SELECT * FROM orders WHERE id=?' + (' AND user_id=?' if user_id else ''),
                                  (order_id, user_id) if user_id else (order_id,))
        if not rows:
            raise HTTPException(404, '充值订单不存在')
        return rows[0]

    @staticmethod
    def public_order(order):
        fields = ('id', 'package', 'credits', 'price_cents', 'status', 'channel', 'expires_at', 'created_at', 'paid_at', 'payment_state', 'payment_error')
        result = {key: order.get(key) for key in fields}
        result['expired'] = bool(order.get('expires_at') and order['expires_at'] <= time.time() and order['status'] != 'paid')
        result['qr_url'] = '/studio-api/payments/orders/' + order['id'] + '/qr.png' if order.get('payment_url') and order['status'] == 'pending' and not result['expired'] else None
        return result

    def create(self, user_id, package, channel, request_key=None):
        if channel != 'manual' and channel not in self.providers:
            raise HTTPException(503, CHANNEL_NAMES.get(channel, '支付渠道') + '商户配置尚未完成，暂不可付款')
        if channel != 'manual' and not request_key:
            raise HTTPException(422, '在线支付下单需要幂等标识，请刷新后重试')
        with self.accounts.transaction() as db:
            old = db.execute('SELECT * FROM orders WHERE user_id=? AND payment_request_key=?', (user_id, request_key)).fetchone() if request_key else None
            if old:
                if old['package'] != package['id'] or old['channel'] != channel:
                    raise HTTPException(409, '重复下单标识与之前套餐或支付渠道不同')
                order_id = old['id']
            else:
                order_id = secrets.token_hex(16)
                db.execute("INSERT INTO orders(id,user_id,package,credits,price_cents,status,channel,payment_request_key,expires_at,created_at) VALUES(?,?,?,?,?,'pending',?,?,?,?)",
                    (order_id, user_id, package['id'], package['credits'], package['price_cents'], channel, request_key,
                     time.time() + 1800 if channel != 'manual' else None, time.time()))
        if channel != 'manual':
            self.prepare(order_id)
        result = self.public_order(self.order(order_id))
        result['message'] = '请扫码付款；支付平台确认后积分自动到账。' if channel != 'manual' else '订单已创建，请联系管理员核实实际收款后入账。此时尚未扣款或增加积分。'
        return result

    def prepare(self, order_id):
        with self.accounts.transaction() as db:
            order = dict(db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone())
            if order['channel'] not in self.providers or order['status'] != 'pending' or order.get('payment_url') or (order['expires_at'] and order['expires_at'] <= time.time()) or order['payment_lock_until'] > time.time():
                return
            db.execute("UPDATE orders SET payment_state='creating',payment_lock_until=? WHERE id=?", (time.time() + 45, order_id))
        try:
            url = self.providers[order['channel']].create(order)
            with self.accounts.transaction() as db:
                db.execute("UPDATE orders SET payment_url=?,payment_state='NOTPAY',payment_error=NULL,payment_lock_until=0,query_after=? WHERE id=? AND status='pending'",
                           (url, time.time() + 20, order_id))
        except Exception:
            with self.accounts.transaction() as db:
                db.execute("UPDATE orders SET payment_state='create_unknown',payment_error=?,payment_lock_until=0,query_after=? WHERE id=? AND status='pending'",
                           ('暂未取得付款二维码，请稍后查询或重试。请勿重复付款。', time.time() + 10, order_id))
            LOGGER.warning('Payment QR creation requires reconciliation: %s', order_id)

    def settle(self, transaction, expected_order=None):
        order_id = transaction.get('order_id')
        if expected_order and order_id != expected_order:
            # NOT_EXIST does not carry out_trade_no in either provider API.
            if transaction.get('state') == 'NOT_EXIST' and not transaction.get('paid'):
                return
            raise PaymentError('Payment query returned another order')
        if not isinstance(order_id, str) or not re.fullmatch(r'[0-9a-f]{32}', order_id):
            raise PaymentError('Invalid payment order identifier')
        try:
            with self.accounts.transaction() as db:
                row = db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
                if not row or row['channel'] != transaction['channel'] or row['channel'] == 'manual':
                    raise PaymentError('Payment channel or order mismatch')
                if not transaction['paid']:
                    if row['status'] != 'paid':
                        closed = transaction.get('state') in ('TRADE_CLOSED', 'CLOSED', 'REVOKED')
                        db.execute('UPDATE orders SET payment_state=?,status=? WHERE id=?',
                                   (transaction.get('state'), 'closed' if closed else row['status'], order_id))
                    return
                if transaction.get('currency') != 'CNY' or type(transaction.get('price_cents')) is not int or transaction['price_cents'] != row['price_cents']:
                    raise PaymentError('Payment amount or currency mismatch')
                receipt = transaction.get('transaction_id')
                if not isinstance(receipt, str) or not re.fullmatch(r'[\w-]{8,128}', receipt):
                    raise PaymentError('Invalid provider transaction identifier')
                existing = db.execute('SELECT * FROM payment_receipts WHERE order_id=?', (order_id,)).fetchone()
                if existing:
                    if existing['transaction_id'] != receipt or existing['channel'] != transaction['channel']:
                        raise PaymentError('Order already settled with another transaction')
                    return
                if row['status'] == 'paid':
                    raise PaymentError('Order was already credited by another path')
                db.execute('INSERT INTO payment_receipts VALUES(?,?,?,?,?,?,?)',
                           (transaction['channel'], receipt, order_id, transaction['price_cents'], 'CNY', transaction['merchant'], time.time()))
                self.accounts.change(db, row['user_id'], row['credits'], 'topup', 'order:' + order_id,
                                     f"{CHANNEL_NAMES[row['channel']]}充值{row['credits']}积分", 'payment:' + row['channel'])
                db.execute("UPDATE orders SET status='paid',receipt=?,paid_at=?,actor=?,payment_state='SUCCESS',payment_error=NULL WHERE id=?",
                           (transaction['channel'] + ':' + receipt, time.time(), 'payment:' + row['channel'], order_id))
        except sqlite3.IntegrityError:
            raise PaymentError('Provider transaction already used by another order') from None

    def refresh(self, order_id):
        with self.accounts.transaction() as db:
            order = dict(db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone())
            if order['status'] != 'pending' or order['channel'] not in self.providers or order['payment_lock_until'] > time.time() or order['query_after'] > time.time():
                return self.public_order(order)
            db.execute('UPDATE orders SET payment_lock_until=?,query_after=? WHERE id=?', (time.time() + 45, time.time() + 10, order_id))
        try:
            transaction = self.providers[order['channel']].query(order)
            self.settle(transaction, expected_order=order_id)
        except Exception:
            LOGGER.warning('Payment query not confirmed: %s', order_id)
        finally:
            with self.accounts.transaction() as db:
                db.execute('UPDATE orders SET payment_lock_until=0 WHERE id=?', (order_id,))
        return self.public_order(self.order(order_id))

    def reconcile(self):
        while not self.stop.wait(15):
            if not self.providers:
                continue
            rows = self.accounts.rows("SELECT id FROM orders WHERE channel<>'manual' AND status='pending' AND created_at>? AND query_after<? AND payment_lock_until<? ORDER BY query_after LIMIT 20",
                                      (time.time() - 7 * 86400, time.time(), time.time()))
            for row in rows:
                if self.stop.is_set():
                    return
                self.refresh(row['id'])
                with self.accounts.transaction() as db:
                    db.execute('UPDATE orders SET query_after=? WHERE id=?', (time.time() + 60, row['id']))


async def notification_body(request):
    content = bytearray()
    async for block in request.stream():
        content.extend(block)
        if len(content) > MAX_BODY:
            raise HTTPException(413, '支付通知过大')
    return bytes(content)


def install(app, accounts, user, admin, start_worker=True, config_path=None):
    payments = Payments(accounts, config_path)
    app.state.payments = payments

    @app.get('/payments/channels')
    def channels(request: Request):
        user(request)
        return {'items': payments.channels(), 'manual_enabled': True}

    @app.get('/payments/admin/configuration')
    def configuration(request: Request):
        admin(request)
        return {'channels': payments.channels(), 'config_file': str(payments.config_path),
                'instructions': '在服务器私有目录配置商户号、AppID及密钥，并重启服务。未配置渠道不能收款。'}

    @app.get('/payments/orders/{order_id}')
    def order(order_id: str, request: Request):
        return payments.public_order(payments.order(order_id, user(request)['id']))

    @app.post('/payments/orders/{order_id}/refresh')
    def refresh(order_id: str, request: Request):
        payments.order(order_id, user(request)['id'])
        return payments.refresh(order_id)

    @app.post('/payments/orders/{order_id}/retry')
    def retry(order_id: str, request: Request):
        account = user(request)
        payments.order(order_id, account['id'])
        accounts.limit('pay-retry:' + account['id'], 30, 3600)
        payments.refresh(order_id)
        payments.prepare(order_id)
        return payments.public_order(payments.order(order_id))

    @app.post('/payments/admin/orders/{order_id}/refresh')
    def admin_refresh(order_id: str, request: Request):
        admin(request)
        payments.order(order_id)
        return payments.refresh(order_id)

    @app.get('/payments/orders/{order_id}/qr.png')
    def qr(order_id: str, request: Request):
        order = payments.order(order_id, user(request)['id'])
        if order['status'] != 'pending' or not order['payment_url'] or order['expires_at'] <= time.time():
            raise HTTPException(409, '二维码不可用或已过期，请查询订单状态')
        output = io.BytesIO()
        qrcode.make(order['payment_url']).save(output, format='PNG')
        return Response(output.getvalue(), media_type='image/png')

    async def notify(channel, request):
        provider = payments.providers.get(channel)
        if not provider:
            raise HTTPException(503, '支付渠道未配置')
        body = await notification_body(request)
        try:
            transaction = await run_in_threadpool(provider.notify, dict(request.headers), body)
            await run_in_threadpool(payments.settle, transaction)
        except (PaymentError, ValueError, KeyError, TypeError):
            LOGGER.warning('Payment notification rejected for %s', channel)
            if channel == 'alipay':
                return PlainTextResponse('failure', status_code=400)
            return Response(status_code=400)
        return PlainTextResponse('success') if channel == 'alipay' else Response(status_code=204)

    @app.post('/payments/notify/alipay')
    async def alipay_notify(request: Request):
        return await notify('alipay', request)

    @app.post('/payments/notify/wechatpay')
    async def wechat_notify(request: Request):
        return await notify('wechatpay', request)

    if start_worker:
        @app.on_event('startup')
        def start():
            threading.Thread(target=payments.reconcile, name='lichtv-payments', daemon=True).start()

        @app.on_event('shutdown')
        def stop():
            payments.stop.set()
    return payments

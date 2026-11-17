"""Activate uploaded LichTV account release on the existing cloud gateway.

Run as root on the web server. Bundles must already be inspected and uploaded;
this never installs packages, touches other sites, or changes GPU model files.
"""
import argparse
import datetime
import json
import grp
import os
import re
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import time
import urllib.request

from configure_account_gateway import configure


def switch(link, target):
    temporary = link.with_name(link.name + '.accounts-next')
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    temporary.replace(link)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-dir', type=Path, default=Path('/tmp'))
    parser.add_argument('--https-config', type=Path, help='Existing LichTV HTTPS site; replace legacy Basic Auth with account login')
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base = Path('/data/lichtv-studio')
    backup = Path('/data/zealman-gateway/backups') / ('accounts-' + stamp)
    backup.mkdir(mode=0o700)
    data, app = base / 'data', base / 'app'
    modules = ['studio_api.py', 'studio_accounts.py', 'studio_payments.py', 'configure_account_gateway.py']
    for name in modules:
        if (app / name).exists():
            shutil.copy2(app / name, backup / name)
    if (data / 'accounts.sqlite3').exists():
        with sqlite3.connect(data / 'accounts.sqlite3') as source, sqlite3.connect(backup / 'accounts.sqlite3') as target:
            source.backup(target)
    for name in ['workspace.json', 'workflow-catalog.json']:
        if (data / name).exists():
            shutil.copy2(data / name, backup / name)
    links = [Path('/data/liancheng-panel/current'), Path('/data/www/lichtv/current')]
    previous = [str(link.resolve()) for link in links]
    releases = [Path('/data/liancheng-panel/releases') / ('accounts-' + stamp),
                Path('/data/www/lichtv/releases') / ('accounts-' + stamp)]
    for kind, target, old in zip(['root', 'ip'], releases, previous):
        target.mkdir(mode=0o755)
        with tarfile.open(args.bundle_dir / ('lichtv-members-' + kind + '.tgz')) as archive:
            archive.extractall(target, filter='data')
        for path in (Path(old) / 'assets').iterdir():
            if path.is_file() and not (target / 'assets' / path.name).exists():
                shutil.copy2(path, target / 'assets' / path.name)
    with tarfile.open(args.bundle_dir / 'lichtv-members-api.tgz') as archive:
        archive.extractall(app, filter='data')
    shutil.copy2(args.bundle_dir / 'lichtv-account-catalog.json', data / 'workflow-catalog.json')
    python = '/data/lichtv-studio/venv/bin/python'
    with sqlite3.connect(data / 'accounts.sqlite3') as db:
        exists = db.execute("SELECT name FROM sqlite_master WHERE name='users'").fetchone()
        existing_admin = db.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone() if exists else None
    credential = base / 'admin-access.json'
    if not existing_admin:
        subprocess.run([python, str(app / 'studio_accounts.py'), '--data-dir', str(data), '--credential-file', str(credential)], check=True)
    with sqlite3.connect(data / 'accounts.sqlite3') as db:
        admin_id = db.execute("SELECT id FROM users WHERE role='admin' ORDER BY created_at LIMIT 1").fetchone()[0]
    owner = data / 'users' / admin_id
    owner.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in ['workspace.json', 'images', 'downloads']:
        source = data / name
        target = owner / name
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)
        elif source.is_dir() and not target.exists():
            shutil.copytree(source, target)
    subprocess.run(['chown', '-R', 'www-data:www-data', str(data)], check=True)
    private = base / 'private'
    if not private.exists():
        private.mkdir(mode=0o750)
        os.chown(private, 0, grp.getgrnam('www-data').gr_gid)
    payment_config = private / 'payments.json'
    if not payment_config.exists():
        template = json.loads((args.bundle_dir / 'payments.example.json').read_text())
        if args.https_config:
            template['public_base_url'] = 'https://drama.lianchengtech.cn'
        payment_config.write_text(json.dumps(template, ensure_ascii=False, indent=2))
        payment_config.chmod(0o640)
        os.chown(payment_config, 0, grp.getgrnam('www-data').gr_gid)
    configs = [Path('/etc/nginx/conf.d/liancheng-panel.conf'), Path('/etc/nginx/conf.d/lichtv-ip-panel.conf')]
    prefix = Path('/etc/nginx/snippets/lichtv-ip-location.conf')
    originals = {path: path.read_text() for path in configs + [prefix] + ([args.https_config] if args.https_config else [])}
    for path in originals:
        shutil.copy2(path, backup / path.name)
    state = {'root': str(releases[0]), 'ip': str(releases[1]), 'previous': previous, 'backup': str(backup),
             'version': json.loads((releases[0] / 'release.json').read_text())['version'], 'activated_at': stamp,
             'account_database': str(data / 'accounts.sqlite3'), 'admin_credentials': str(credential)}
    (backup / 'state.json').write_text(json.dumps(state, indent=2))
    try:
        for path in configs:
            path.write_text(configure(originals[path]))
        prefix.write_text(originals[prefix].replace('proxy_set_header Host $host;', 'proxy_set_header Host $http_host;')
                          .replace('# Public demo access, as requested. All users share the same backend.',
                                   '# Homepage is public. Account API enforces generation and file authorization.'))
        if args.https_config:
            https = originals[args.https_config]
            if 'proxy_pass http://127.0.0.1:16018' not in https or 'drama.lianchengtech.cn' not in https:
                raise RuntimeError('HTTPS site does not point to the isolated LichTV gateway')
            https = re.sub(r'auth_basic (?:"[^"]*"|off);', 'auth_basic off;', https)
            https = https.replace('proxy_set_header Host $host;', 'proxy_set_header Host $http_host;')
            args.https_config.write_text(https)
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'restart', 'lichtv-studio'], check=True)
        for attempt in range(40):
            try:
                result = json.load(urllib.request.urlopen('http://127.0.0.1:16128/accounts/public', timeout=3))
                if len(result['packages']) == 4 and len(result.get('payment_channels', [])) == 2:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(.25)
        else:
            raise RuntimeError('Account API readiness failed')
        for link, target in zip(links, releases):
            switch(link, target)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
        for port in [16018, 16028]:
            for attempt in range(40):
                try:
                    result = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/studio-api/accounts/public', timeout=3))
                    if result.get('credits_per_second') == 2:
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError(f'Gateway readiness failed on {port}')
    except BaseException:
        for path, text in originals.items():
            path.write_text(text)
        for link, target in zip(links, previous):
            switch(link, target)
        for name in modules:
            if (backup / name).exists():
                shutil.copy2(backup / name, app / name)
        subprocess.run(['systemctl', 'restart', 'lichtv-studio'], check=True)
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
        # Never restore the old balance database during a code rollback.
        raise
    (app / 'active-release.json').write_text(json.dumps(state, indent=2))
    print(json.dumps(state))


if __name__ == '__main__':
    main()

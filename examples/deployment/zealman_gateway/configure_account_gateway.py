"""Create the scoped Nginx config that closes unmetered GPU API paths."""
import re


def configure(source, port=None, root=None, api_port=16128):
    if port:
        source = re.sub(r'listen 127\.0\.0\.1:\d+;', f'listen 127.0.0.1:{port};', source, count=1)
    if root:
        source = re.sub(r'    root [^;]+;', f'    root {root};', source, count=1)
    source = source.replace('proxy_set_header Host $host;', 'proxy_set_header Host $http_host;')
    source = re.sub(r'location \^~ /studio-api/ \{.*?\n    \}', '''location ^~ /studio-api/ {
        proxy_pass http://127.0.0.1:API_PORT/;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $http_x_real_ip;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
        proxy_read_timeout 1800s;
        proxy_request_buffering off;
        proxy_buffering off;
    }'''.replace('API_PORT', str(api_port)), source, count=1, flags=re.S)
    # Named fallback is closed as well: a regex, alternate spelling, encoded
    # slash, websocket, or unknown legacy path must not reach the raw panel.
    source, count = re.subn(r'    location @gpu_panel \{[^{}]*\}', '    location @gpu_panel { return 403; }', source, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Expected one GPU fallback block')
    proxy = f'''    location ^~ /api/ {{
        proxy_pass http://127.0.0.1:{api_port}/gateway/api/;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $http_x_real_ip;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
        proxy_read_timeout 180s;
    }}
    location = /config.json {{
        proxy_pass http://127.0.0.1:{api_port}/gateway/config.json;
        proxy_set_header Host $http_host;
    }}
'''
    if '/gateway/api/' not in source:
        source = source.replace('    location = / {', proxy + '\n    location = / {', 1)
    source = re.sub(r'(proxy_pass http://127\.0\.0\.1:)\d+(/gateway/(?:api/|config\.json);)',
                    lambda match: match[1] + str(api_port) + match[2], source)
    return source

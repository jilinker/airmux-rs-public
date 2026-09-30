#!/usr/bin/env python3
"""Initialize config.yaml and derive Docker orchestration from that single source."""
import argparse
import base64
import ipaddress
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from configuration import atomic_write, load_config

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = Path(__file__).with_name('compose.yaml')
PUBLIC_REPO = 'jilinker/airmux-rs-public'
DIGEST = re.compile(r'^sha256:[0-9a-f]{64}$')
IMAGE = re.compile(r'^[a-z0-9][a-z0-9.-]*(?::[0-9]+)?(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)+$')
MARKER = '# airmux-managed-compose-v1'

def secret(n=24):
    return base64.urlsafe_b64encode(os.urandom(n)).decode().rstrip('=')

def load(path):
    return load_config(path)

def require_map(c, name):
    value = c.get(name)
    if not isinstance(value, dict): raise ValueError(f'{name} must be a mapping')
    return value

def image_ref(value):
    if not isinstance(value, str): raise ValueError('image must be repository@sha256:digest')
    repo, separator, digest = value.rpartition('@')
    if not separator or not IMAGE.fullmatch(repo) or not DIGEST.fullmatch(digest):
        raise ValueError('image must be repository@sha256:digest')
    return value

def integer(value, lower, upper, name):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f'{name} is out of range')

def validate(c):
    db = require_map(c, 'database')
    try:
        url = urlsplit(db.get('url', ''))
        if url.scheme not in ('postgres', 'postgresql') or not url.hostname or not url.path.strip('/'):
            raise ValueError()
        url.port
    except (TypeError, ValueError): raise ValueError('database.url must be a PostgreSQL URL') from None
    integer(db.get('max_connections', 10), 1, 1024, 'database.max_connections')
    server = require_map(c, 'server')
    try:
        host, port = server['listen'].rsplit(':', 1)
        address = ipaddress.ip_address(host.strip('[]'))
        if not address.is_unspecified: raise ValueError()
        integer(int(port), 1, 65535, 'server.listen port')
    except (KeyError, AttributeError, ValueError): raise ValueError('server.listen must be an IP:port socket address') from None
    origins = server.get('allowed_origins', [])
    if not isinstance(origins, list): raise ValueError('server.allowed_origins must be a list')
    for origin in origins:
        p = urlsplit(origin)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.query or p.fragment or p.path not in ('', '/'):
            raise ValueError('allowed_origins must contain HTTP(S) origins')
    require_map(c, 'administrator')  # Rust validates initial credentials only when no admin exists.
    security = require_map(c, 'security')
    if bool(security.get('encryption_key')) == bool(security.get('encryption_key_file')):
        raise ValueError('configure exactly one encryption_key or encryption_key_file')
    if security.get('encryption_key'):
        try:
            if len(base64.b64decode(security['encryption_key'], validate=True)) != 32: raise ValueError()
        except Exception: raise ValueError('security.encryption_key must encode 32 bytes') from None
    dep = require_map(c, 'deployment')
    if dep.get('mode') != 'docker': raise ValueError('manage.py requires deployment.mode: docker')
    directory = dep.get('directory', '')
    if not isinstance(directory, str) or not os.path.isabs(directory): raise ValueError('deployment.directory must be absolute')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', dep.get('project_name', '')): raise ValueError('deployment.project_name is invalid')
    ipaddress.ip_address(dep.get('http_bind', '0.0.0.0'))
    integer(dep.get('http_port'), 1, 65535, 'deployment.http_port')
    for field in ('app_image', 'updater_image'): image_ref(dep.get(field))
    if not IMAGE.fullmatch(dep.get('image_repository', '')): raise ValueError('deployment.image_repository is invalid')
    if any(ref.split('@')[0] != dep['image_repository'] for ref in (dep['app_image'], dep['updater_image'])):
        raise ValueError('application and updater images must use image_repository')
    up = require_map(c, 'updater')
    integer(up.get('port', 8081), 1, 65535, 'updater.port')
    if not os.path.isabs(up.get('state_directory', '')): raise ValueError('updater.state_directory must be absolute')
    if up.get('enabled'):
        if bool(up.get('token')) == bool(up.get('token_file')): raise ValueError('configure exactly one updater token or token_file')
        if url.hostname != 'postgres' and not dep.get('database_container'):
            raise ValueError('external database updates require deployment.database_container for verified backups')
        address = urlsplit(up.get('url', ''))
        if address.scheme != 'http' or address.hostname != 'updater' or address.port != up['port']:
            raise ValueError('Docker updater.url must use http://updater:<updater.port>')
    # Mount the deployment directory read-only into API for optional secret files.
    for value in (security.get('encryption_key_file'), up.get('token_file')):
        if value and (not Path(value).is_absolute() or not Path(value).resolve().is_relative_to(Path(directory).resolve())):
            raise ValueError('Docker secret files must be inside deployment.directory')
    return c

def db_parts(url):
    p = urlsplit(url)
    return unquote(p.username or 'airmux'), unquote(p.password or ''), unquote(p.path.lstrip('/'))

def quote_env(value):
    value = str(value)
    if any(char in value for char in ('\n', '\r', '\0')): raise ValueError('deployment values cannot contain control characters')
    # Single quotes prevent Compose interpolation of passwords containing $ or ${...}.
    return "'" + value.replace("'", "\\'") + "'"

def write_env(path, values):
    atomic_write(path, ''.join(f'{key}={quote_env(value)}\n' for key, value in values.items()))

class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https': raise ValueError('refused insecure release redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch_json(url, accept='application/vnd.github+json'):
    request = Request(url, headers={'Accept': accept, 'User-Agent': 'airmux-manage/1'})
    with build_opener(Redirects()).open(request, timeout=20) as response:
        body = response.read(1024 * 1024 + 1)
    if len(body) > 1024 * 1024: raise ValueError('release response too large')
    return json.loads(body)

def latest_images():
    release = fetch_json('https://api.github.com/repos/' + PUBLIC_REPO + '/releases/latest')
    tag = release.get('tag_name', '')
    match = re.fullmatch(r'v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', tag)
    if not match or tuple(map(int, match.groups())) < (0, 1, 2) or release.get('draft') or release.get('prerelease'):
        raise ValueError('this installer requires release v0.1.2 or newer; use init --image for an offline image')
    asset = next((x for x in release.get('assets', []) if x.get('name') == 'release-manifest.json'), {})
    if type(asset.get('id')) is not int or asset['id'] <= 0: raise ValueError('release manifest asset missing')
    manifest = fetch_json('https://api.github.com/repos/' + PUBLIC_REPO + '/releases/assets/' + str(asset['id']), 'application/octet-stream')
    if manifest.get('version') != tag[1:] or manifest.get('architecture') != 'linux/amd64': raise ValueError('release manifest mismatch')
    image = image_ref(manifest.get('image'))
    return {'app_image': image, 'updater_image': image, 'image_repository': image.split('@')[0]}

def init_config(path, image=None):
    if path.exists(): raise ValueError('config already exists; existing configuration and keys will not be overwritten')
    c = load_config(ROOT / 'config.example.yaml', private=False)
    c['deployment']['directory'] = str(path.parent.resolve())
    c['administrator']['password'] = secret(24) + 'Aa1!'
    c['database']['url'] = 'postgres://airmux:' + secret(32) + '@postgres:5432/airmux'
    c['security']['encryption_key'] = base64.b64encode(os.urandom(32)).decode()
    c['updater']['token'] = secret(32)
    selected = image_ref(image) if image else None
    c['deployment'].update({'app_image': selected, 'updater_image': selected, 'image_repository': selected.split('@')[0]} if selected else latest_images())
    validate(c)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf8') as stream:
        stream.write(yaml.safe_dump(c, sort_keys=False, allow_unicode=True))
        stream.flush(); os.fsync(stream.fileno())
    return c

def compose_files(c, config_path):
    dep = c['deployment']; directory = Path(dep['directory'])
    directory.mkdir(parents=True, exist_ok=True)
    source = yaml.safe_load(COMPOSE.read_text())
    url = urlsplit(c['database']['url'])
    if url.hostname != 'postgres':
        source['services'].pop('postgres')
        source['services']['api'].pop('depends_on')
        if dep.get('database_network'):
            source['networks'] = {'default': {'external': True, 'name': dep['database_network']}}
    target = directory / 'compose.yaml'
    if not target.exists() or MARKER in target.read_text(encoding='utf8'):
        atomic_write(target, MARKER + '\n' + yaml.safe_dump(source, sort_keys=False), mode=0o644)
    docker_config = dep.get('docker_config_file')
    if not docker_config:
        docker_config = str(directory / 'docker-config.json')
        if not Path(docker_config).exists(): atomic_write(Path(docker_config), '{}\n')
    user, password, database = db_parts(c['database']['url'])
    env = {'AIRMUX_PROJECT_NAME': dep['project_name'], 'AIRMUX_POSTGRES_IMAGE': dep['postgres_image'], 'AIRMUX_APP_IMAGE': dep['app_image'], 'AIRMUX_UPDATER_IMAGE': dep['updater_image'], 'AIRMUX_DEPLOY_DIR': str(directory), 'AIRMUX_CONFIG_FILE': str(config_path.resolve()), 'AIRMUX_HTTP_BIND': dep.get('http_bind', '0.0.0.0'), 'AIRMUX_HTTP_PORT': dep['http_port'], 'AIRMUX_UPDATER_STATE_DIR': c['updater']['state_directory'], 'AIRMUX_DOCKER_CONFIG_FILE': docker_config, 'COMPOSE_PROFILES': 'updates' if c['updater'].get('enabled') else '', 'POSTGRES_USER': user, 'POSTGRES_PASSWORD': password, 'POSTGRES_DB': database}
    env_path = directory / '.compose.env'
    previous = env_path.read_text(encoding='utf8') if env_path.exists() else ''
    previous_image = next((line.split('=',1)[1] for line in previous.splitlines() if line.startswith('AIRMUX_APP_IMAGE=')), None)
    write_env(env_path, env)
    runtime = directory / 'runtime.env'
    if not runtime.exists(): atomic_write(runtime, '# updater-managed image state\n')
    elif previous_image and previous_image != quote_env(dep['app_image']):
        # An explicit base-image edit takes precedence over an earlier online update.
        atomic_write(runtime, '\n'.join(line for line in runtime.read_text().splitlines() if not line.startswith('AIRMUX_APP_IMAGE=')) + '\n')
    api_port = c['server']['listen'].rsplit(':', 1)[1]
    nginx = Path(__file__).with_name('nginx.conf').read_text().replace('http://api:3000', 'http://api:' + api_port)
    atomic_write(directory / 'nginx.conf', nginx, mode=0o644)
    return target, directory / '.compose.env', runtime

def run_command(action, path):
    c = validate(load(path)); compose, env, runtime = compose_files(c, path)
    command = ['docker', 'compose', '--project-directory', c['deployment']['directory'], '--env-file', str(env), '--env-file', str(runtime), '-f', str(compose), '--project-name', c['deployment']['project_name']]
    command += {'up': ['up', '-d', '--wait'], 'down': ['down'], 'ps': ['ps']}[action]
    return subprocess.run(command, check=True).returncode

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('init', 'render', 'up', 'down', 'ps'):
        command = sub.add_parser(name)
        command.add_argument('--config', required=True)
        if name == 'init': command.add_argument('--image', help='offline application image pinned by digest')
    args = parser.parse_args(argv)
    path = Path(args.config).expanduser().resolve()
    try:
        if args.action == 'init':
            config = init_config(path, args.image)
            compose_files(config, path)
            print(f'initialized {path}; review it, then use docker compose to start')
        elif args.action == 'render':
            compose_files(validate(load(path)), path)
            print('Compose parameters rendered; config.yaml is mounted read-only')
        else: run_command(args.action, path)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        # Network and parser exceptions may include secret data; keep diagnostics bounded.
        print(str(error) if isinstance(error, ValueError) else 'deployment command failed; check configuration and Docker availability', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__': raise SystemExit(main())

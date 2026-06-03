import os
from pathlib import Path
from flask import Blueprint, request, jsonify

system_bp = Blueprint('system', __name__)

_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')


def _read_env():
    """Parse .env file into a dict."""
    result = {}
    if not os.path.exists(_ENV_PATH):
        return result
    with open(_ENV_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
    return result


def _write_env(updates):
    """Update specific keys in .env file, preserving comments and order."""
    lines = []
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, 'r') as f:
            lines = f.readlines()

    # Build a map of existing keys to line indices
    key_to_line = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.partition('=')[0].strip()
            key_to_line[key] = i

    # Update existing keys or append new ones
    updated_keys = set()
    for key, value in updates.items():
        if key in key_to_line:
            idx = key_to_line[key]
            lines[idx] = f'{key}={value}\n'
        else:
            lines.append(f'{key}={value}\n')
        updated_keys.add(key)

    with open(_ENV_PATH, 'w') as f:
        f.writelines(lines)

    # Also update os.environ for immediate effect in current process
    for key, value in updates.items():
        os.environ[key] = value


def _mask_value(key, value):
    """Mask sensitive values for display."""
    if not value:
        return ''
    sensitive_keys = {'DATABASE_URL', 'REDIS_URL', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY', 'MYSQL_PASSWORD', 'VOICE_DB_PASSWORD'}
    if key in sensitive_keys:
        if len(value) <= 8:
            return '***'
        return value[:8] + '***'
    return value


@system_bp.route('/api/system/health', methods=['GET'])
def health_check():
    from server.services.redis_client import get_redis
    r = get_redis()
    redis_ok = False
    redis_latency_ms = None
    if r is not None:
        try:
            import time
            t0 = time.monotonic()
            r.ping()
            redis_latency_ms = round((time.monotonic() - t0) * 1000, 1)
            redis_ok = True
        except Exception:
            pass
    return jsonify({
        'status': 'ok',
        'redis': {
            'connected': redis_ok,
            'latency_ms': redis_latency_ms,
            'configured': bool(os.environ.get('REDIS_URL')),
        },
    })

DEFAULT_JIANYING_DIR = os.path.expanduser(
    '~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft'
)


@system_bp.route('/api/system/ls', methods=['GET'])
def list_directories():
    raw_path = request.args.get('path', '').strip()
    if not raw_path:
        target = Path(DEFAULT_JIANYING_DIR)
    else:
        target = Path(os.path.expanduser(raw_path)).resolve()

    if not target.exists():
        return jsonify({'error': '路径不存在'}), 400
    if not target.is_dir():
        return jsonify({'error': '不是目录'}), 400

    try:
        entries = []
        for item in target.iterdir():
            if item.name.startswith('.'):
                continue
            try:
                is_dir = item.is_dir()
            except OSError:
                continue
            if is_dir:
                entries.append({'name': item.name, 'path': str(item)})
        entries.sort(key=lambda e: e['name'].lower())
    except OSError:
        return jsonify({'error': '没有访问权限'}), 403

    parent = str(target.parent) if target.parent != target else None
    return jsonify({
        'current': str(target),
        'parent': parent,
        'entries': entries,
    })


@system_bp.route('/api/system/config', methods=['GET'])
def get_config():
    env = _read_env()
    # Get current effective values (env might override .env)
    config = {
        'database': {
            'DATABASE_URL': _mask_value('DATABASE_URL', env.get('DATABASE_URL', '')),
            'effective_db': 'MySQL' if env.get('DATABASE_URL', '').startswith('mysql') else 'SQLite',
        },
        'redis': {
            'REDIS_URL': _mask_value('REDIS_URL', env.get('REDIS_URL', '')),
            'REDIS_KEY_PREFIX': env.get('REDIS_KEY_PREFIX', 'video-script'),
        },
        'rag': {
            'CHROMADB_PERSIST_DIR': env.get('CHROMADB_PERSIST_DIR', ''),
            'OPENAI_API_KEY': _mask_value('OPENAI_API_KEY', env.get('OPENAI_API_KEY', '')),
            'DEEPSEEK_API_KEY': _mask_value('DEEPSEEK_API_KEY', env.get('DEEPSEEK_API_KEY', '')),
        },
    }
    # Add Redis health
    try:
        from server.services.redis_client import get_redis
        r = get_redis()
        config['redis']['connected'] = r is not None and r.ping()
    except Exception:
        config['redis']['connected'] = False

    return jsonify(config)


@system_bp.route('/api/system/config', methods=['PUT'])
def update_config():
    data = request.get_json() or {}
    allowed_keys = {'DATABASE_URL', 'REDIS_URL', 'REDIS_KEY_PREFIX', 'CHROMADB_PERSIST_DIR', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY'}
    updates = {k: v for k, v in data.items() if k in allowed_keys}
    if not updates:
        return jsonify({'error': '无有效配置项'}), 400

    _write_env(updates)
    return jsonify({'message': '配置已保存，需要重启服务生效', 'updated': list(updates.keys())})


@system_bp.route('/api/system/config/test', methods=['POST'])
def test_config():
    data = request.get_json() or {}
    target = data.get('target')  # 'database' or 'redis'
    results = {}

    if target == 'database':
        url = data.get('DATABASE_URL', '')
        if not url:
            # Test current
            from server.models.base import db
            try:
                db.session.execute(db.text('SELECT 1'))
                results['database'] = {'ok': True, 'message': '连接成功'}
            except Exception as e:
                results['database'] = {'ok': False, 'message': str(e)}
        else:
            # Test provided URL
            import sqlalchemy
            try:
                engine = sqlalchemy.create_engine(url, connect_args={'connect_timeout': 5})
                with engine.connect() as conn:
                    conn.execute(sqlalchemy.text('SELECT 1'))
                results['database'] = {'ok': True, 'message': '连接成功'}
                engine.dispose()
            except Exception as e:
                results['database'] = {'ok': False, 'message': str(e)}

    elif target == 'redis':
        url = data.get('REDIS_URL', '')
        if not url:
            # Test current
            try:
                from server.services.redis_client import get_redis
                r = get_redis()
                if r and r.ping():
                    results['redis'] = {'ok': True, 'message': '连接成功'}
                else:
                    results['redis'] = {'ok': False, 'message': 'Redis 未配置或不可用'}
            except Exception as e:
                results['redis'] = {'ok': False, 'message': str(e)}
        else:
            # Test provided URL
            import redis
            try:
                r = redis.Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5)
                r.ping()
                results['redis'] = {'ok': True, 'message': '连接成功'}
            except Exception as e:
                results['redis'] = {'ok': False, 'message': str(e)}

    return jsonify(results)

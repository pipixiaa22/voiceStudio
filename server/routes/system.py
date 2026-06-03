import os
import re
import sys
import threading
from pathlib import Path
from flask import Blueprint, request, jsonify

system_bp = Blueprint('system', __name__)

_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')


def _restart_server():
    """Restart the server process by re-exec-ing after a short delay."""
    import time
    time.sleep(1)
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _parse_database_url(url):
    """Parse a SQLAlchemy database URL into components."""
    if not url:
        return {'driver': 'sqlite', 'host': '', 'port': '', 'user': '', 'password': '', 'database': ''}
    # mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
    m = re.match(r'(\w+\+?\w*)://([^:]*):?([^@]*)@([^:/]+):?(\d*)/(\w+)', url)
    if m:
        return {
            'driver': m.group(1),
            'user': m.group(2),
            'password': m.group(3),
            'host': m.group(4),
            'port': m.group(5) or '3306',
            'database': m.group(6),
        }
    return {'driver': 'sqlite', 'host': '', 'port': '', 'user': '', 'password': '', 'database': ''}


def _build_database_url(parts):
    """Build a SQLAlchemy database URL from components."""
    driver = parts.get('driver', 'mysql+pymysql')
    host = parts.get('host', '')
    port = parts.get('port', '3306')
    user = parts.get('user', '')
    password = parts.get('password', '')
    database = parts.get('database', '')
    charset = parts.get('charset', 'utf8mb4')
    if not host or not database:
        return ''
    auth = f'{user}:{password}' if password else user
    return f'{driver}://{auth}@{host}:{port}/{database}?charset={charset}'


def _parse_redis_url(url):
    """Parse a Redis URL into components."""
    if not url:
        return {'host': '', 'port': '6379', 'password': '', 'db': '0'}
    # redis://:password@host:port/db
    m = re.match(r'redis://:?([^@]*)@([^:/]+):?(\d*)/?(\d*)', url)
    if m:
        return {
            'password': m.group(1),
            'host': m.group(2),
            'port': m.group(3) or '6379',
            'db': m.group(4) or '0',
        }
    return {'host': '', 'port': '6379', 'password': '', 'db': '0'}


def _build_redis_url(parts):
    """Build a Redis URL from components."""
    host = parts.get('host', '')
    port = parts.get('port', '6379')
    password = parts.get('password', '')
    db = parts.get('db', '0')
    if not host:
        return ''
    auth = f':{password}@' if password else ''
    return f'redis://{auth}{host}:{port}/{db}'


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


@system_bp.route('/api/system/restart', methods=['POST'])
def restart_server():
    """Restart the server process to apply new configuration."""
    threading.Thread(target=_restart_server, daemon=True).start()
    return jsonify({'message': '服务正在重启...'})


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

    db_parts = _parse_database_url(env.get('DATABASE_URL', ''))
    redis_parts = _parse_redis_url(env.get('REDIS_URL', ''))

    config = {
        'database': {
            'driver': db_parts.get('driver', 'mysql+pymysql'),
            'host': db_parts.get('host', ''),
            'port': db_parts.get('port', ''),
            'user': db_parts.get('user', ''),
            'database': db_parts.get('database', ''),
            'effective_db': 'MySQL' if db_parts.get('driver', '').startswith('mysql') else 'SQLite',
        },
        'redis': {
            'host': redis_parts.get('host', ''),
            'port': redis_parts.get('port', '6379'),
            'db': redis_parts.get('db', '0'),
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
    updates = {}

    # Database: construct URL from individual fields
    if 'database' in data:
        db = data['database']
        if db.get('host') and db.get('database'):
            url = _build_database_url(db)
            if url:
                updates['DATABASE_URL'] = url
        elif db.get('host') == '' and db.get('database') == '':
            # User wants to switch to SQLite
            updates['DATABASE_URL'] = ''

    # Redis: construct URL from individual fields
    if 'redis' in data:
        rd = data['redis']
        if rd.get('host'):
            url = _build_redis_url(rd)
            if url:
                updates['REDIS_URL'] = url
        elif rd.get('host') == '':
            updates['REDIS_URL'] = ''
        if 'REDIS_KEY_PREFIX' in rd:
            updates['REDIS_KEY_PREFIX'] = rd['REDIS_KEY_PREFIX']

    # RAG: direct key-value
    if 'rag' in data:
        rag = data['rag']
        for key in ('CHROMADB_PERSIST_DIR', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY'):
            if key in rag:
                updates[key] = rag[key]

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
        db_data = data.get('database', {})
        if db_data.get('host') and db_data.get('database'):
            url = _build_database_url(db_data)
        else:
            url = ''

        if not url:
            from server.models.base import db
            try:
                db.session.execute(db.text('SELECT 1'))
                results['database'] = {'ok': True, 'message': '连接成功'}
            except Exception as e:
                results['database'] = {'ok': False, 'message': str(e)}
        else:
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
        rd_data = data.get('redis', {})
        if rd_data.get('host'):
            url = _build_redis_url(rd_data)
        else:
            url = ''

        if not url:
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
            import redis
            try:
                r = redis.Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5)
                r.ping()
                results['redis'] = {'ok': True, 'message': '连接成功'}
            except Exception as e:
                results['redis'] = {'ok': False, 'message': str(e)}

    return jsonify(results)


# All table names that should exist
_EXPECTED_TABLES = [
    'texts', 'tags', 'folders',
    'video_templates', 'video_jobs', 'video_assets',
    'voice_workflows', 'voice_workflow_segments', 'voice_workflow_edges',
    'custom_providers',
    'discovery_sources', 'discovery_queries', 'discovery_items', 'discovery_analyses',
    'novel_projects', 'novel_outline_nodes', 'novel_chapters', 'novel_chapter_versions',
    'novel_entities', 'novel_relations', 'novel_events', 'novel_event_relations',
    'novel_graph_changes', 'novel_generations', 'novel_memories', 'novel_memory_changes',
]


@system_bp.route('/api/system/config/tables', methods=['GET'])
def check_tables():
    """Check which expected tables exist in the database."""
    from server.models.base import db
    import sqlalchemy

    try:
        engine = db.engine
        inspector = sqlalchemy.inspect(engine)
        existing = set(inspector.get_table_names())
        missing = [t for t in _EXPECTED_TABLES if t not in existing]
        return jsonify({
            'ok': True,
            'total': len(_EXPECTED_TABLES),
            'existing': len(_EXPECTED_TABLES) - len(missing),
            'missing': missing,
            'all_exist': len(missing) == 0,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_bp.route('/api/system/config/tables/create', methods=['POST'])
def create_tables():
    """Auto-create all missing tables."""
    from server.models.base import db

    try:
        db.create_all()
        # Verify
        import sqlalchemy
        inspector = sqlalchemy.inspect(db.engine)
        existing = set(inspector.get_table_names())
        created = [t for t in _EXPECTED_TABLES if t in existing]
        return jsonify({
            'ok': True,
            'message': f'已创建 {len(created)} 张表',
            'tables': created,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_bp.route('/api/system/config/tables/ddl', methods=['GET'])
def get_ddl():
    """Generate DDL SQL for all expected tables."""
    from server.models.base import db
    import sqlalchemy

    try:
        engine = db.engine
        # Use SQLAlchemy to generate DDL from metadata
        metadata = db.Model.metadata
        ddl_statements = []
        for table_name in _EXPECTED_TABLES:
            table = metadata.tables.get(table_name)
            if table is not None:
                ddl = sqlalchemy.schema.CreateTable(table).compile(engine)
                ddl_statements.append(str(ddl).strip() + ';')

        return jsonify({
            'ok': True,
            'ddl': '\n\n'.join(ddl_statements),
            'table_count': len(ddl_statements),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

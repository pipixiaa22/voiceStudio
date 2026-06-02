import os
from pathlib import Path
from flask import Blueprint, request, jsonify

system_bp = Blueprint('system', __name__)


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

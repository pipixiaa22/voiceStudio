import json
import os
import time
import logging

logger = logging.getLogger(__name__)

_client = None
_unavailable_until = 0.0
_RETRY_INTERVAL = 60  # seconds before retrying a failed connection


def get_redis():
    """Return a Redis client, or None if REDIS_URL is not configured / unreachable.

    After a connection failure, retries every RETRY_INTERVAL seconds instead
    of giving up permanently.
    """
    global _client, _unavailable_until
    if _client is not None:
        try:
            _client.ping()
            return _client
        except Exception:
            _client = None

    # Backoff window after a failure
    if _unavailable_until and time.monotonic() < _unavailable_until:
        return None

    url = os.environ.get('REDIS_URL')
    if not url:
        return None
    try:
        import redis
        _client = redis.Redis.from_url(url, decode_responses=False, socket_connect_timeout=3, socket_timeout=3)
        _client.ping()
        _unavailable_until = 0.0
        logger.info('Redis connected: %s', url.split('@')[-1] if '@' in url else url)
        return _client
    except Exception as exc:
        _client = None
        _unavailable_until = time.monotonic() + RETRY_INTERVAL
        logger.warning('Redis unavailable (retry in %ds): %s', RETRY_INTERVAL, exc)
        return None


def redis_key(*parts):
    """Build a namespaced Redis key."""
    prefix = os.environ.get('REDIS_KEY_PREFIX', 'video-script')
    clean = ':'.join(str(p).strip(':') for p in parts)
    return f'{prefix}:{clean}'


def cache_get_json(key, default=None):
    """Get a JSON value from Redis cache. Returns default on miss or error."""
    r = get_redis()
    if r is None:
        return default
    try:
        raw = r.get(key)
        if raw is None:
            return default
        return json.loads(raw)
    except Exception:
        return default


def cache_set_json(key, value, ttl=None):
    """Set a JSON value in Redis cache with optional TTL in seconds."""
    r = get_redis()
    if r is None:
        return
    try:
        data = json.dumps(value, ensure_ascii=False)
        if ttl:
            r.set(key, data, ex=ttl)
        else:
            r.set(key, data)
    except Exception:
        pass


def cache_delete(key):
    """Delete a key from Redis cache."""
    r = get_redis()
    if r is None:
        return
    try:
        r.delete(key)
    except Exception:
        pass


def acquire_lock(key, ttl=120):
    """Acquire a distributed lock with TTL. Returns a unique token or None."""
    r = get_redis()
    if r is None:
        return None
    try:
        import uuid
        token = uuid.uuid4().hex
        if r.set(key, token, nx=True, ex=ttl):
            return token
        return None
    except Exception:
        return None


def release_lock(key, token):
    """Release a lock only if the token matches (Lua CAS)."""
    r = get_redis()
    if r is None:
        return
    try:
        lua = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        end
        return 0
        """
        r.eval(lua, 1, key, token)
    except Exception:
        pass


def rate_limit_check(key, limit, window):
    """Fixed-window rate limiter. Returns (allowed: bool, remaining: int)."""
    r = get_redis()
    if r is None:
        return True, limit
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = pipe.execute()
        if count == 1:
            r.expire(key, window)
            ttl = window
        remaining = max(0, limit - count)
        return count <= limit, remaining
    except Exception:
        return True, limit


def rate_limit(category, limit, window):
    """Decorator: rate-limit a Flask route by client IP.

    Usage:
        @rate_limit('tts', 20, 60)  # 20 requests per 60 seconds
        def my_route(): ...
    """
    from functools import wraps
    from flask import request, jsonify, current_app

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Skip rate limiting in test mode
            if current_app.config.get('TESTING'):
                return f(*args, **kwargs)
            ip = request.remote_addr or 'unknown'
            key = redis_key('ratelimit', category, ip)
            allowed, remaining = rate_limit_check(key, limit, window)
            if not allowed:
                resp = jsonify({'error': f'请求过于频繁，请稍后重试', 'retry_after': window})
                resp.status_code = 429
                resp.headers['Retry-After'] = str(window)
                resp.headers['X-RateLimit-Remaining'] = '0'
                return resp
            result = f(*args, **kwargs)
            # Inject rate limit headers into successful responses
            if hasattr(result, 'headers'):
                result.headers['X-RateLimit-Remaining'] = str(remaining)
            return result
        return wrapper
    return decorator


def idempotency_check(key, ttl=600):
    """Check idempotency key. Returns existing job_id if duplicate, else None."""
    return cache_get_json(key)


def idempotency_set(key, job_id, ttl=600):
    """Store idempotency key → job_id mapping."""
    cache_set_json(key, job_id, ttl=ttl)

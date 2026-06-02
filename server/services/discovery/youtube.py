import hashlib
import json as _json
import re
import requests
from datetime import datetime, timezone, timedelta
from server.services.discovery.base import DiscoveryConnector
from server.models.discovery import DiscoverySource

YOUTUBE_SEARCH_URL = 'https://www.googleapis.com/youtube/v3/search'
YOUTUBE_VIDEOS_URL = 'https://www.googleapis.com/youtube/v3/videos'

DURATION_MAP = {
    'short': 'short',    # < 4 min
    'medium': 'medium',  # 4-20 min
    'long': 'long',      # > 20 min
}


def _parse_duration(iso_duration: str) -> float | None:
    """Parse ISO 8601 duration (PT1M30S) to seconds."""
    if not iso_duration:
        return None
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


class YoutubeConnector(DiscoveryConnector):
    platform_key = 'youtube'
    display_name = 'YouTube'

    def __init__(self, api_key: str = ''):
        self._api_key = api_key

    def _get_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        src = DiscoverySource.query.filter_by(platform_key='youtube').first()
        if src:
            import json
            config = json.loads(src.config_json) if src.config_json else {}
            return config.get('api_key', '')
        return ''

    def is_available(self) -> bool:
        return bool(self._get_api_key())

    def search(self, query, limit=20, filters=None):
        from server.services.redis_client import redis_key, cache_get_json, cache_set_json

        api_key = self._get_api_key()
        if not api_key:
            raise ValueError('YouTube API key 未配置')

        # Check cache
        filter_hash = hashlib.sha256(_json.dumps(filters or {}, sort_keys=True).encode()).hexdigest()[:8]
        cache_k = redis_key('discovery', 'search', 'youtube', hashlib.sha256(f'{query}:{limit}:{filter_hash}'.encode()).hexdigest()[:16])
        cached = cache_get_json(cache_k)
        if cached is not None:
            return cached

        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': min(limit, 50),
            'key': api_key,
        }

        if filters:
            if filters.get('order'):
                params['order'] = filters['order']
            if filters.get('published_days'):
                since = datetime.now(timezone.utc) - timedelta(days=filters['published_days'])
                params['publishedAfter'] = since.strftime('%Y-%m-%dT%H:%M:%SZ')
            if filters.get('duration') and filters['duration'] in DURATION_MAP:
                params['videoDuration'] = DURATION_MAP[filters['duration']]

        resp = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=15)
        if not resp.ok:
            error = resp.json().get('error', {}).get('message', resp.text)
            raise RuntimeError(f'YouTube API 错误: {error}')

        data = resp.json()
        video_ids = [item['id']['videoId'] for item in data.get('items', [])]
        if not video_ids:
            return []

        details = self._fetch_video_details(video_ids, api_key)
        details_map = {d['id']: d for d in details}

        results = []
        for item in data.get('items', []):
            vid = item['id']['videoId']
            snippet = item.get('snippet', {})
            detail = details_map.get(vid, {})
            stats = detail.get('statistics', {})
            content = detail.get('contentDetails', {})

            results.append({
                'platform_key': 'youtube',
                'source_url': f'https://www.youtube.com/watch?v={vid}',
                'source_id': vid,
                'title': snippet.get('title'),
                'author_name': snippet.get('channelTitle'),
                'cover_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                'published_at': snippet.get('publishedAt'),
                'duration': _parse_duration(content.get('duration')),
                'stats': {
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0)),
                },
                'tags': snippet.get('tags', []),
            })

        cache_set_json(cache_k, results, ttl=1800)  # 30 min
        return results

    def resolve_url(self, url: str) -> dict:
        from server.services.redis_client import redis_key, cache_get_json, cache_set_json

        match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', url)
        if not match:
            raise ValueError(f'无效的 YouTube URL: {url}')

        video_id = match.group(1)

        # Check cache
        cache_k = redis_key('discovery', 'video', 'youtube', video_id)
        cached = cache_get_json(cache_k)
        if cached is not None:
            return cached

        api_key = self._get_api_key()
        if not api_key:
            raise ValueError('YouTube API key 未配置')

        details = self._fetch_video_details([video_id], api_key)
        if not details:
            raise RuntimeError(f'无法获取视频信息: {video_id}')

        detail = details[0]
        snippet = detail.get('snippet', {})
        stats = detail.get('statistics', {})
        content = detail.get('contentDetails', {})

        result = {
            'platform_key': 'youtube',
            'source_url': url,
            'source_id': video_id,
            'title': snippet.get('title'),
            'author_name': snippet.get('channelTitle'),
            'cover_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
            'published_at': snippet.get('publishedAt'),
            'duration': _parse_duration(content.get('duration')),
            'stats': {
                'views': int(stats.get('viewCount', 0)),
                'likes': int(stats.get('likeCount', 0)),
                'comments': int(stats.get('commentCount', 0)),
            },
            'tags': snippet.get('tags', []),
        }

        cache_set_json(cache_k, result, ttl=86400)  # 1 day
        return result

    def _fetch_video_details(self, video_ids: list[str], api_key: str) -> list[dict]:
        resp = requests.get(YOUTUBE_VIDEOS_URL, params={
            'part': 'snippet,statistics,contentDetails',
            'id': ','.join(video_ids),
            'key': api_key,
        }, timeout=15)
        if not resp.ok:
            return []
        return resp.json().get('items', [])

import re
import requests
from server.services.discovery.base import DiscoveryConnector

URL_PATTERNS = {
    'douyin': re.compile(r'douyin\.com/video/(\d+)'),
    'bilibili': re.compile(r'bilibili\.com/video/(BV\w+)'),
    'youtube': re.compile(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)'),
    'kuaishou': re.compile(r'kuaishou\.com/short-video/(\w+)'),
}

PLATFORM_NAMES = {
    'douyin': '抖音',
    'bilibili': 'B站',
    'youtube': 'YouTube',
    'kuaishou': '快手',
}


def _detect_platform(url: str) -> tuple[str | None, str | None]:
    """返回 (platform_key, source_id) 或 (None, None)"""
    for platform, pattern in URL_PATTERNS.items():
        match = pattern.search(url)
        if match:
            return platform, match.group(1)
    return None, None


def _fetch_youtube_oembed(video_id: str) -> dict:
    """通过 YouTube oEmbed 获取标题和封面"""
    try:
        resp = requests.get(
            'https://www.youtube.com/oembed',
            params={'url': f'https://www.youtube.com/watch?v={video_id}', 'format': 'json'},
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            return {
                'title': data.get('title'),
                'author_name': data.get('author_name'),
                'cover_url': data.get('thumbnail_url'),
            }
    except Exception:
        pass
    return {}


def _fetch_page_meta(url: str) -> dict:
    """通过 HTTP GET 获取页面 og:title 和 og:image"""
    try:
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; VideoScriptBot/1.0)',
        })
        if not resp.ok:
            return {}
        html = resp.text
        title = None
        cover_url = None

        # og:title
        match = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
        if not match:
            match = re.search(r'<meta\s+content="([^"]*)"\s+property="og:title"', html)
        if match:
            title = match.group(1)
        elif '<title>' in html:
            match = re.search(r'<title>(.*?)</title>', html)
            if match:
                title = match.group(1)

        # og:image
        match = re.search(r'<meta\s+property="og:image"\s+content="([^"]*)"', html)
        if not match:
            match = re.search(r'<meta\s+content="([^"]*)"\s+property="og:image"', html)
        if match:
            cover_url = match.group(1)

        return {'title': title, 'cover_url': cover_url}
    except Exception:
        return {}


class ManualUrlConnector(DiscoveryConnector):
    platform_key = 'manual'
    display_name = '手动链接'

    def search(self, query, limit, filters=None):
        raise NotImplementedError('手动链接不支持关键词搜索')

    def resolve_url(self, url: str) -> dict:
        platform, source_id = _detect_platform(url)

        if not platform:
            return {
                'platform_key': 'manual',
                'source_url': url,
                'source_id': None,
            }

        item = {
            'platform_key': platform,
            'source_url': url,
            'source_id': source_id,
        }

        if platform == 'youtube':
            meta = _fetch_youtube_oembed(source_id)
        else:
            meta = _fetch_page_meta(url)

        item.update({k: v for k, v in meta.items() if v})
        return item

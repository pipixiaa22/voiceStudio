import pytest
from server.services.discovery.base import DiscoveryConnector
from server.services.discovery.registry import ConnectorRegistry


class DummyConnector(DiscoveryConnector):
    platform_key = 'dummy'
    display_name = 'Dummy'

    def search(self, query, limit, filters=None):
        return [{'title': f'result for {query}', 'platform_key': 'dummy'}]

    def resolve_url(self, url):
        return {'title': 'resolved', 'platform_key': 'dummy', 'source_url': url}


@pytest.fixture(autouse=True)
def clear_registry():
    ConnectorRegistry.clear()
    yield
    ConnectorRegistry.clear()


def test_register_and_get():
    conn = DummyConnector()
    ConnectorRegistry.register(conn)
    assert ConnectorRegistry.get('dummy') is conn


def test_get_nonexistent():
    assert ConnectorRegistry.get('nonexistent') is None


def test_get_all():
    conn = DummyConnector()
    ConnectorRegistry.register(conn)
    all_conns = ConnectorRegistry.get_all()
    assert 'dummy' in all_conns
    assert len(all_conns) == 1


def test_connector_search():
    conn = DummyConnector()
    results = conn.search('test query', 10)
    assert len(results) == 1
    assert results[0]['title'] == 'result for test query'


def test_connector_resolve_url():
    conn = DummyConnector()
    result = conn.resolve_url('https://example.com/video/123')
    assert result['source_url'] == 'https://example.com/video/123'


def test_connector_is_available():
    conn = DummyConnector()
    assert conn.is_available() is True


def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        DiscoveryConnector()


from server.services.discovery.manual_url import ManualUrlConnector, _detect_platform


def test_detect_platform_youtube():
    platform, vid = _detect_platform('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    assert platform == 'youtube'
    assert vid == 'dQw4w9WgXcQ'


def test_detect_platform_youtube_short():
    platform, vid = _detect_platform('https://youtu.be/dQw4w9WgXcQ')
    assert platform == 'youtube'
    assert vid == 'dQw4w9WgXcQ'


def test_detect_platform_bilibili():
    platform, vid = _detect_platform('https://www.bilibili.com/video/BV1xx411c7mD')
    assert platform == 'bilibili'
    assert vid == 'BV1xx411c7mD'


def test_detect_platform_douyin():
    platform, vid = _detect_platform('https://www.douyin.com/video/7123456789')
    assert platform == 'douyin'
    assert vid == '7123456789'


def test_detect_platform_kuaishou():
    platform, vid = _detect_platform('https://www.kuaishou.com/short-video/abc123')
    assert platform == 'kuaishou'
    assert vid == 'abc123'


def test_detect_platform_unknown():
    platform, vid = _detect_platform('https://example.com/video/123')
    assert platform is None
    assert vid is None


def test_manual_url_search_raises():
    conn = ManualUrlConnector()
    with pytest.raises(NotImplementedError):
        conn.search('test', 10)


def test_manual_url_resolve_unknown():
    conn = ManualUrlConnector()
    result = conn.resolve_url('https://example.com/video/123')
    assert result['platform_key'] == 'manual'
    assert result['source_url'] == 'https://example.com/video/123'
    assert result.get('source_id') is None

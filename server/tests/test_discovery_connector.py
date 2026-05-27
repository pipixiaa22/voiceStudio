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

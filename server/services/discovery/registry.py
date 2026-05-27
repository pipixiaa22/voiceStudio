from server.services.discovery.base import DiscoveryConnector


class ConnectorRegistry:
    _connectors: dict[str, DiscoveryConnector] = {}

    @classmethod
    def register(cls, connector: DiscoveryConnector):
        cls._connectors[connector.platform_key] = connector

    @classmethod
    def get(cls, platform_key: str) -> DiscoveryConnector | None:
        return cls._connectors.get(platform_key)

    @classmethod
    def get_all(cls) -> dict[str, DiscoveryConnector]:
        return dict(cls._connectors)

    @classmethod
    def clear(cls):
        """用于测试"""
        cls._connectors.clear()

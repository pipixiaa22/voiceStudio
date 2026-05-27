from server.services.discovery.registry import ConnectorRegistry
from server.services.discovery.manual_url import ManualUrlConnector

ConnectorRegistry.register(ManualUrlConnector())

from server.services.discovery.registry import ConnectorRegistry
from server.services.discovery.manual_url import ManualUrlConnector
from server.services.discovery.youtube import YoutubeConnector

ConnectorRegistry.register(ManualUrlConnector())
ConnectorRegistry.register(YoutubeConnector())

from abc import ABC, abstractmethod


class DiscoveryConnector(ABC):
    platform_key: str
    display_name: str

    @abstractmethod
    def search(self, query: str, limit: int, filters: dict | None = None) -> list[dict]:
        """关键词搜索，返回 DiscoveryItem 字典列表"""
        ...

    @abstractmethod
    def resolve_url(self, url: str) -> dict:
        """解析单个 URL，返回 DiscoveryItem 字典"""
        ...

    def is_available(self) -> bool:
        """检查平台是否可用（API key 配置等）"""
        return True

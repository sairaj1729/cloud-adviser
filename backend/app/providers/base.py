from abc import ABC, abstractmethod
from typing import Dict, List, Any

class CloudProviderConnector(ABC):

    @abstractmethod
    async def verify_connection(self) -> bool:
        """Verify credential validity and read access."""
        pass

    @abstractmethod
    async def get_resources() -> List[Dict[str, Any]]:
        """Discover inventory resources (e.g. EC2, EBS, RDS)."""
        pass

    @abstractmethod
    async def get_metrics(self, resource_id: str) -> Dict[str, Any]:
        """Fetch utilization metrics (e.g. CloudWatch CPU, Memory)."""
        pass

    @abstractmethod
    async def get_costs(self, resource_id: str) -> Dict[str, Any]:
        """Fetch resource cost data."""
        pass

    @abstractmethod
    async def get_recommendations() -> List[Dict[str, Any]]:
        """Fetch cloud-provider native recommendations where available."""
        pass

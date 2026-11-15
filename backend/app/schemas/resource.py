from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ResourceCostSchema(BaseModel):
    monthly: float = 0.0
    currency: str = "USD"

class ResourceMetricsSchema(BaseModel):
    cpu_average: Optional[float] = 0.0
    cpu_p95: Optional[float] = 0.0
    memory_average: Optional[float] = 0.0
    memory_p95: Optional[float] = 0.0

class NormalizedResourceSchema(BaseModel):
    id: Optional[str] = None
    user_id: str
    cloud_account_id: str
    provider: str
    account_id: str
    resource_type: str
    resource_id: str
    region: str
    name: str
    configuration: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)
    metrics: ResourceMetricsSchema = Field(default_factory=ResourceMetricsSchema)
    cost: ResourceCostSchema = Field(default_factory=ResourceCostSchema)
    last_synced_at: datetime = Field(default_factory=datetime.utcnow)

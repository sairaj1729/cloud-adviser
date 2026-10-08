from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class FindingSavingsSchema(BaseModel):
    monthly: float = 0.0
    annual: float = 0.0
    currency: str = "USD"
    type: str = "ESTIMATED"  # ESTIMATED vs PROVIDER_REPORTED

class FindingSchema(BaseModel):
    id: Optional[str] = None
    user_id: str
    cloud_account_id: str
    rule_id: str
    resource_id: str
    resource_name: Optional[str] = None
    provider: str
    severity: str = "medium"
    status: str = "open"  # open, resolved, dismissed
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommendation: Dict[str, Any] = Field(default_factory=dict)
    savings: FindingSavingsSchema = Field(default_factory=FindingSavingsSchema)
    source: str = "Cloud Advisor Rule Engine"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

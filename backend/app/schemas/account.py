from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class CloudAccountCreateSchema(BaseModel):
    provider: str = Field(..., description="aws, azure, or gcp")
    display_name: str
    account_identifier: str
    region: Optional[str] = "us-east-1"
    credential_type: str = Field(..., description="assume_role, client_secret, or service_account")
    role_arn: Optional[str] = None
    external_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    gcp_project_id: Optional[str] = None
    provider_config: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CloudAccountOutSchema(BaseModel):
    id: str
    user_id: str
    provider: str
    display_name: str
    status: str
    account_identifier: str
    region: str
    credential_type: str
    provider_config: Dict[str, Any] = Field(default_factory=dict)
    last_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class ScanSummarySchema(BaseModel):
    status: str
    resources_scanned: int
    rules_evaluated: int
    findings_created: int
    estimated_monthly_savings: float

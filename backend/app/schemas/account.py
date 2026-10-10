from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class AwsInitiateResponseSchema(BaseModel):
    connection_id: Optional[str] = None
    external_id: str
    platform_aws_account_id: str
    platform_role_arn: str
    trust_policy: Dict[str, Any]
    recommended_permissions: List[str]

class AwsVerifyRequestSchema(BaseModel):
    connection_id: Optional[str] = None
    display_name: str = Field(..., description="Connection nickname, e.g. Production AWS")
    account_id: str = Field(..., description="Customer 12-digit AWS Account ID")
    role_arn: str = Field(..., description="Customer IAM Role ARN to assume")
    external_id: str = Field(..., description="Generated External ID from Step 1")
    region: Optional[str] = Field("ap-south-1", description="AWS region, e.g. ap-south-1 or us-east-1")

class AwsVerifyResponseSchema(BaseModel):
    status: str
    verified: bool
    account: Optional[Any] = None
    session_info: Optional[Dict[str, Any]] = None
    message: str

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

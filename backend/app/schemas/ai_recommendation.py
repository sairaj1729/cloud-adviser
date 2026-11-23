from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

class AIRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    resource_id: str
    resource_name: Optional[str] = None
    provider: str
    resource_type: Optional[str] = None
    service: Optional[str] = None
    category: Optional[str] = None
    dataset_id: Optional[str] = None
    action: str = Field(..., description="RIGHTSIZE, STOP, TERMINATE, STORAGE_DOWNGRADE, or NO_ACTION")
    target_sku: Optional[str] = Field(None, description="Recommended SKU / instance type (e.g., t4g.large)")
    current_sku: Optional[str] = Field(None, description="Current instance type or storage tier")
    current_monthly_cost: float = 0.0
    estimated_monthly_savings: float = 0.0
    estimated_savings_percentage: float = 0.0
    risk_level: str = Field("LOW", description="LOW, MEDIUM, or HIGH")
    justification: str = Field(..., description="Technical explanation based on CPU/RAM/IOPS telemetry")
    remediation_steps: List[str] = Field(default_factory=list, description="Step-by-step actions for engineers")
    remediation_command: Optional[str] = Field(None, description="CLI command or Terraform snippet")
    llm_provider_used: str = "gemini"
    llm_model_used: str = "gemini-1.5-flash"
    status: str = "PENDING_APPROVAL"  # PENDING_APPROVAL, APPROVED, REJECTED, EXECUTED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIBatchRecommendationResponse(BaseModel):
    total_findings_analyzed: int
    recommendations_generated: int
    total_estimated_monthly_savings: float
    items: List[AIRecommendationResponse]

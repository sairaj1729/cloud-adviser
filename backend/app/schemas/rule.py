from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ConditionItemSchema(BaseModel):
    field: str
    operator: str  # eq, neq, gt, gte, lt, lte, in, not_in
    threshold: Any

class RuleConditionsSchema(BaseModel):
    logic: str = "AND"  # AND, OR
    items: List[ConditionItemSchema]

class RuleRecommendationConfigSchema(BaseModel):
    type: str = "RIGHTSIZING_REVIEW"
    action_template: Optional[str] = None

class SavingsCalculationConfigSchema(BaseModel):
    type: str = "ESTIMATED"
    percentage: Optional[float] = 50.0

class RuleSchema(BaseModel):
    rule_id: str
    name: str
    description: str
    provider: str
    resource_type: str
    required_data: List[str] = Field(default_factory=list)
    lookback_window: Dict[str, Any] = Field(default_factory=lambda: {"value": 14, "unit": "days"})
    conditions: RuleConditionsSchema
    recommendation: RuleRecommendationConfigSchema
    savings_calculation: SavingsCalculationConfigSchema
    severity: str = "medium"  # low, medium, high
    status: str = "active"    # active, inactive
    provenance: str = "DERIVED"

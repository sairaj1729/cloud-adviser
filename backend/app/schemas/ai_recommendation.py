from pydantic import BaseModel, Field


class RecommendationCandidateSchema(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=30)
    resource_id: str = Field(min_length=1, max_length=200)
    resource_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    problem: str = Field(min_length=1, max_length=1000)
    evidence: str = Field(min_length=1, max_length=1500)
    savings: float = Field(ge=0)
    priority: str = Field(min_length=1, max_length=20)
    confidence: float = Field(ge=0, le=100)
    action: str = Field(min_length=1, max_length=1000)
    current_monthly_cost: float = Field(ge=0)


class AiRecommendationRequestSchema(BaseModel):
    recommendations: list[RecommendationCandidateSchema] = Field(
        min_length=1,
        max_length=30,
    )

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    score: int = Field(..., ge=1, le=10)
    reason: str

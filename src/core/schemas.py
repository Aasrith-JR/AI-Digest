"""
Docstring for src.core.schemas
"""
from typing import Literal
from pydantic import BaseModel, Field


class GenAINewsEvaluation(BaseModel):
    """
    Pydantic schema for GenAI News evaluation
    """
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    topic: str
    why_it_matters: str
    target_audience: Literal["developer", "architect", "manager"]
    decision: Literal["include", "exclude"]


class ProductIdeaEvaluation(BaseModel):
    """
    Pydantic schema for Product Idea evaluation
    """
    idea_type: str
    problem_statement: str
    solution_summary: str
    maturity_level: Literal["idea", "mvp", "early_traction", "scaling"]
    reusability_score: float = Field(..., ge=0.0, le=1.0)
    decision: Literal["include", "exclude"]

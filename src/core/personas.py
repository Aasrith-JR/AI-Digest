from dataclasses import dataclass
from typing import Type

from core.schemas import GenAINewsEvaluation, ProductIdeaEvaluation


@dataclass(frozen=True)
class Persona:
    """
    Declarative persona definition.
    """
    name: str
    description: str
    evaluation_schema: Type
    min_score: float


GENAI_NEWS = Persona(
    name="GENAI_NEWS",
    description="Technical GenAI and infrastructure news",
    evaluation_schema=GenAINewsEvaluation,
    min_score=0.6,
)

PRODUCT_IDEAS = Persona(
    name="PRODUCT_IDEAS",
    description="Product and startup opportunity scanner",
    evaluation_schema=ProductIdeaEvaluation,
    min_score=0.5,
)


ALL_PERSONAS = {
    GENAI_NEWS.name: GENAI_NEWS,
    PRODUCT_IDEAS.name: PRODUCT_IDEAS,
}

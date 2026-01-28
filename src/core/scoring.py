"""
Module to score every digest
"""

from typing import Dict, Any

from core.personas import Persona


def passes_threshold(
    persona: Persona,
    structured_output: Dict[str, Any],
) -> bool:
    """
    Determines whether an evaluated item should be included
    based on persona-specific scoring logic.
    """
    if persona.name == "GENAI_NEWS":
        score = structured_output.get("relevance_score", 0.0)
        return score >= persona.min_score

    if persona.name == "PRODUCT_IDEAS":
        score = structured_output.get("reusability_score", 0.0)
        return score >= persona.min_score

    return False


def normalize_score(persona: Persona, structured_output: Dict[str, Any]) -> float:
    """
    Extracts the primary score used for ranking.
    """
    if persona.name == "GENAI_NEWS":
        return float(structured_output.get("relevance_score", 0.0))

    if persona.name == "PRODUCT_IDEAS":
        return float(structured_output.get("reusability_score", 0.0))

    return 0.0

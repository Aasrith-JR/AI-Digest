import json
import logging
import re
from typing import List, Dict, Any

from core.personas import Persona
from core.scoring import passes_threshold
from services.llm import OllamaClient

logger = logging.getLogger(__name__)


def _extract_json(content: str) -> str:
    """
    Extract JSON from LLM response, stripping markdown code blocks if present.
    """
    content = content.strip()

    # Remove markdown code blocks (```json ... ``` or ``` ... ```)
    pattern = r'^```(?:json)?\s*\n?(.*?)\n?```$'
    match = re.match(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try to find JSON array in the content
    array_match = re.search(r'\[.*\]', content, re.DOTALL)
    if array_match:
        return array_match.group(0)

    return content


async def evaluate_item(
    *,
    llm: OllamaClient,
    persona: Persona,
    prompt: str,
) -> dict:
    """
    Executes LLM evaluation and validates structured output.
    """
    response = await llm.evaluate(prompt)
    raw_content = response["content"]

    # Clean the response before parsing
    clean_json = _extract_json(raw_content)

    parsed = persona.evaluation_schema.model_validate_json(clean_json)

    decision = passes_threshold(persona, parsed.model_dump())

    return {
        "raw": raw_content,
        "parsed": parsed.model_dump(),
        "decision": "include" if decision else "exclude",
        "latency_ms": response["latency_ms"],
    }


async def evaluate_batch(
    *,
    llm: OllamaClient,
    persona: Persona,
    items: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Evaluates ALL items in a SINGLE LLM call and returns only top K results.

    Args:
        llm: The OllamaClient instance
        persona: The persona to evaluate against
        items: List of dicts with 'id', 'title', 'content', 'url' keys
        top_k: Number of top items to return (default: 5)

    Returns:
        List of evaluation results with 'id', 'parsed', 'decision' keys
    """
    if not items:
        return []

    logger.info(f"Evaluating {len(items)} items in a single LLM call, selecting top {top_k}")

    # Build compact items list - only titles and short content to fit in context
    items_text = ""
    for item in items:
        # Keep content very short to fit all items
        content_preview = item['content'][:200].replace('\n', ' ').strip()
        items_text += f"[{item['id']}] {item['title']}\n"

    # Build prompt based on persona
    if persona.name == "GENAI_NEWS":
        prompt = f"""You are a GenAI/ML news curator. Analyze these {len(items)} items and select the TOP {top_k} most relevant for developers.

ITEMS:
{items_text}

For each of the TOP {top_k} items, provide a JSON object with:
- id: the item ID (must match exactly)
- relevance_score: float 0.0-1.0
- topic: category (LLM, Inference, Training, Agents, Tools, etc.)
- why_it_matters: 1 sentence explanation
- target_audience: "developer", "architect", or "manager"
- decision: "include"

Return ONLY a JSON array with exactly {top_k} items, sorted by relevance (highest first).
Example: [{{"id": "0", "relevance_score": 0.9, "topic": "LLM", "why_it_matters": "...", "target_audience": "developer", "decision": "include"}}]

JSON array:"""
    else:  # PRODUCT_IDEAS
        prompt = f"""You are a product ideas curator. Analyze these {len(items)} items and select the TOP {top_k} most valuable for founders/builders.

ITEMS:
{items_text}

For each of the TOP {top_k} items, provide a JSON object with:
- id: the item ID (must match exactly)
- idea_type: category (SaaS, Tool, Platform, API, Mobile App, etc.)
- problem_statement: 1 sentence about the problem
- solution_summary: 1 sentence about the solution
- maturity_level: "idea", "mvp", "early_traction", or "scaling"
- reusability_score: float 0.0-1.0
- decision: "include"

Return ONLY a JSON array with exactly {top_k} items, sorted by reusability (highest first).
Example: [{{"id": "0", "idea_type": "SaaS", "problem_statement": "...", "solution_summary": "...", "maturity_level": "mvp", "reusability_score": 0.8, "decision": "include"}}]

JSON array:"""

    try:
        response = await llm.evaluate(prompt)
    except Exception as e:
        logger.error(f"LLM evaluation failed: {e}")
        raise

    raw_content = response["content"]
    logger.info(f"LLM response received (latency: {response['latency_ms']}ms)")
    logger.debug(f"Raw response: {raw_content[:500]}...")

    clean_json = _extract_json(raw_content)

    # Parse the response
    try:
        parsed_list = json.loads(clean_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Raw content: {raw_content}")
        raise ValueError(f"Invalid JSON response from LLM: {e}")

    results = []
    for parsed_item in parsed_list:
        item_id = str(parsed_item.get("id", ""))

        # Validate against schema
        try:
            validated = persona.evaluation_schema.model_validate(parsed_item)
            parsed_dict = validated.model_dump()

            results.append({
                "id": item_id,
                "parsed": parsed_dict,
                "decision": "include",
            })
            logger.info(f"Selected item {item_id} for inclusion")
        except Exception as e:
            logger.warning(f"Validation failed for item {item_id}: {e}")
            # Still include with raw data if validation fails
            results.append({
                "id": item_id,
                "parsed": parsed_item,
                "decision": "include",
            })

    logger.info(f"Evaluation complete: {len(results)} items selected")
    return results[:top_k]  # Ensure we return at most top_k

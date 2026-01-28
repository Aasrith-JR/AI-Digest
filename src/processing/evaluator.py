from core.personas import Persona
from core.scoring import passes_threshold
from services.llm import OllamaClient


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

    parsed = persona.evaluation_schema.model_validate_json(raw_content)

    decision = passes_threshold(persona, parsed.model_dump())

    return {
        "raw": raw_content,
        "parsed": parsed.model_dump(),
        "decision": "include" if decision else "exclude",
        "latency_ms": response["latency_ms"],
    }

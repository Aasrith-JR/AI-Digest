from typing import List

from core.entities import DigestEntry
from core.personas import Persona
from core.scoring import normalize_score


def summarize_cluster(
    *,
    persona: Persona,
    title: str,
    summary: str,
    why_it_matters: str,
    audience: str,
    source_urls: List[str],
    structured_output: dict,
) -> DigestEntry:
    score = normalize_score(persona, structured_output)

    return DigestEntry(
        title=title.strip(),
        summary=summary.strip(),
        why_it_matters=why_it_matters.strip(),
        audience=audience,
        source_urls=source_urls,
        score=score,
    )

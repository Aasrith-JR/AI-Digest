"""
File delivery channel
"""
import json
from pathlib import Path
from typing import List

from core.entities import DigestEntry
from delivery.base import DeliveryChannel


class FileDelivery(DeliveryChannel):
    name = "file"

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def deliver(
        self,
        *,
        persona: str,
        digest_date: str,
        entries: List[DigestEntry],
    ) -> None:
        base = self.output_dir / f"{persona}_{digest_date}"

        json_path = base.with_suffix(".json")
        md_path = base.with_suffix(".md")

        json_path.write_text(
            json.dumps(
                [entry.__dict__ for entry in entries],
                indent=2,
            ),
            encoding="utf-8",
        )

        md_lines = list[str]()
        for entry in entries:
            md_lines.append(f"## {entry.title}")
            md_lines.append(entry.summary)
            md_lines.append(f"**Why it matters:** {entry.why_it_matters}")
            md_lines.append(f"**Audience:** {entry.audience}")
            md_lines.append("")
            for url in entry.source_urls:
                md_lines.append(f"- {url}")
            md_lines.append("\n")

        md_path.write_text("\n".join(md_lines), encoding="utf-8")

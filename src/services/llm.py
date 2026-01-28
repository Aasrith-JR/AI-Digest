import httpx
import time
from typing import Dict, Any


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    async def evaluate(self, prompt: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        start = time.time()
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()

        latency_ms = int((time.time() - start) * 1000)
        data = response.json()

        return {
            "raw": data,
            "content": data["choices"][0]["message"]["content"],
            "latency_ms": latency_ms,
        }

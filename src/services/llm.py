import time
import asyncio
import logging
from typing import Dict, Any, List

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
import httpx

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    LangChain-based Ollama client with retry logic and proper connection handling.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float = 0.1,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        timeout: float = 300.0,  # 5 minutes for batch processing
    ):
        # ChatOllama uses Ollama's native API, not OpenAI-compatible /v1 endpoint
        # Strip /v1 suffix if present
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        elif base_url.endswith("/v1/"):
            base_url = base_url[:-4]

        self.base_url = base_url.rstrip('/')
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        self.llm = ChatOllama(
            base_url=self.base_url,
            model=model,
            temperature=temperature,
            num_ctx=4096,  # Context window size
        )

    async def _invoke_with_retry(self, messages: List[HumanMessage]) -> Any:
        """
        Invoke LLM with retry logic for connection failures.
        """
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    self.llm.ainvoke(messages),
                    timeout=self.timeout,
                )
                return response

            except asyncio.TimeoutError:
                last_exception = TimeoutError(
                    f"Request timed out after {self.timeout}s"
                )
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries}: Timeout, retrying..."
                )

            except Exception as e:
                last_exception = e
                error_msg = str(e)

                # Check for connection errors
                if "connection" in error_msg.lower() or "connect" in error_msg.lower():
                    logger.warning(
                        f"Attempt {attempt}/{self.max_retries}: Connection error - {error_msg} (base_url={self.base_url}, model={self.model})"
                    )
                else:
                    # For non-connection errors, don't retry
                    raise

            if attempt < self.max_retries:
                # Exponential backoff with jitter
                delay = self.retry_delay * attempt
                await asyncio.sleep(delay)

        raise last_exception or Exception("All connection attempts failed")

    async def evaluate(self, prompt: str) -> Dict[str, Any]:
        """
        Evaluate a prompt and return the response with metadata.
        """
        start = time.time()

        response = await self._invoke_with_retry([HumanMessage(content=prompt)])

        latency_ms = int((time.time() - start) * 1000)

        return {
            "raw": response,
            "content": response.content,
            "latency_ms": latency_ms,
        }

    async def summarize(self, text: str, max_length: int = 200) -> str:
        """
        Summarize text using the LLM.
        """
        prompt = f"""Summarize the following text in {max_length} characters or less.
Be concise and capture the key points.

Text: {text}

Summary:"""

        result = await self.evaluate(prompt)
        return result["content"].strip()

    async def health_check(self) -> bool:
        """
        Check if the Ollama server is reachable by calling /api/tags.
        """
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return True
                logger.error(f"Ollama health check failed: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Ollama health check error: {e} (url={url})")
            return False


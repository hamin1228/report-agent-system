"""Small typed wrapper around LiteLLM."""

import json
from typing import Any, TypeVar

from litellm import acompletion, aembedding
from pydantic import BaseModel

from report_agent.config import Settings
from report_agent.retry import with_retry

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Centralizes provider calls and structured response parsing."""

    def __init__(self, settings: Settings, *, evaluator: bool = False) -> None:
        self.settings = settings
        self.model = settings.evaluator_model if evaluator else settings.model

    async def complete(self, *, system: str, user: str) -> str:
        async def call_model() -> Any:
            return await acompletion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                timeout=self.settings.request_timeout_seconds,
            )

        response = await with_retry(
            call_model,
            attempts=self.settings.max_api_retries,
            base_delay_seconds=self.settings.retry_base_delay_seconds,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("The model returned an empty response")
        return str(content)

    async def structured(self, schema: type[T], *, system: str, user: str) -> T:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        prompt = f"{user}\n\nReturn only JSON matching this JSON Schema:\n{schema_json}"
        raw = await self.complete(system=system, user=prompt)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        return schema.model_validate_json(cleaned.strip())

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Create embeddings through LiteLLM using the configured RAG model alias."""

        if not texts:
            return []

        async def call_model() -> Any:
            return await aembedding(
                model=self.settings.rag_embedding_model,
                input=texts,
                timeout=self.settings.request_timeout_seconds,
            )

        response = await with_retry(
            call_model,
            attempts=self.settings.max_api_retries,
            base_delay_seconds=self.settings.retry_base_delay_seconds,
        )
        ordered = sorted(response.data, key=lambda item: item["index"])
        return [list(item["embedding"]) for item in ordered]

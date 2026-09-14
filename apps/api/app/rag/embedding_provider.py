import logging
from collections.abc import Sequence

import httpx

from app.core.config import Settings
from app.rag.contracts import EmbeddingProvider, EmbeddingSpace, EvidenceError

logger = logging.getLogger(__name__)

class HTTPEmbeddingProvider(EmbeddingProvider):
    """Provider-agnostic HTTP embedding provider supporting OpenAI-compatible APIs."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self.url = settings.embedding_provider_url
        self.model = settings.embedding_model
        self.api_key = settings.embedding_api_key
        
        self.dimensions = getattr(settings, "embedding_dimensions", 1536)
        
        self._space = EmbeddingSpace(
            provider="HTTP_OPENAI_COMPATIBLE",
            model=self.model,
            dimensions=self.dimensions,
            tokenizer="cl100k_base",
            distance_metric="cosine",
            pipeline_version="1",
        )
        self.client = http_client or httpx.AsyncClient(timeout=settings.dependency_timeout_seconds)

    @property
    def space(self) -> EmbeddingSpace:
        return self._space

    async def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        if not texts:
            return []

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "input": list(texts),
        }

        try:
            response = await self.client.post(
                self.url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            logger.exception("Failed to contact embedding provider: %s", e)
            raise EvidenceError("EMBEDDING_PROVIDER_ERROR") from e
        except ValueError as e:
            logger.exception("Invalid JSON from embedding provider: %s", e)
            raise EvidenceError("EMBEDDING_PROVIDER_INVALID_RESPONSE") from e

        if "data" not in data or not isinstance(data["data"], list):
            raise EvidenceError("EMBEDDING_PROVIDER_INVALID_RESPONSE")
            
        if len(data["data"]) != len(texts):
            raise EvidenceError("EMBEDDING_COUNT_MISMATCH")

        embeddings = []
        for item in sorted(data["data"], key=lambda x: x.get("index", 0)):
            if "embedding" not in item:
                raise EvidenceError("EMBEDDING_PROVIDER_INVALID_RESPONSE")
            embeddings.append(item["embedding"])

        return embeddings

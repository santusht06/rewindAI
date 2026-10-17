"""Embedding provider interface and implementations.

Implements:
- BE-INGEST-006 (Embedding provider interface and configured implementation)
- NFR-REL-001, NFR-COST-001 (Deterministic mock provider for zero-cost testing)
"""

import abc
import hashlib
import math
from typing import Sequence
import httpx

from services.api.config import settings
from services.api.errors import ProviderTimeoutError, ProviderUnavailableError


class EmbeddingProvider(abc.ABC):
    """Abstract interface for text embedding generation."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model."""
        pass

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """Vector dimension produced by this provider."""
        pass

    @abc.abstractmethod
    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate normalized vector embeddings for a list of text strings."""
        pass


class DeterministicMockEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline embedding provider for reproducible testing.

    Generates unit-normalized 256-dimensional vectors using SHA256 and sine projections.
    Texts that share common words have higher cosine similarity than unrelated texts.
    """

    def __init__(self, dimension: int = 256) -> None:
        self._dim = dimension

    @property
    def model_name(self) -> str:
        return f"mock-deterministic-{self._dim}d"

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            words = text.lower().split()
            vec = [0.0] * self._dim

            if not words:
                vec[0] = 1.0
                embeddings.append(vec)
                continue

            for word in words:
                word_hash = hashlib.sha256(word.encode("utf-8")).digest()
                for i in range(self._dim):
                    byte_val = word_hash[i % len(word_hash)]
                    vec[i] += math.sin((byte_val + i) * 0.1)

            # L2 Normalize vector
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 1e-9:
                vec = [x / norm for x in vec]
            else:
                vec[0] = 1.0

            embeddings.append(vec)

        return embeddings


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini text-embedding provider."""

    def __init__(self, api_key: str | None = None, model: str = "text-embedding-004") -> None:
        self._api_key = api_key or (settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else "")
        self._model = model
        self._dim = 768

    @property
    def model_name(self) -> str:
        return f"gemini-{self._model}"

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not self._api_key:
            raise ProviderUnavailableError("Gemini API key is not configured.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:batchEmbedContents?key={self._api_key}"
        requests_payload = [
            {"model": f"models/{self._model}", "content": {"parts": [{"text": t}]}}
            for t in texts
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json={"requests": requests_payload})
                if resp.status_code != 200:
                    raise ProviderUnavailableError(
                        f"Gemini embedding API error: status={resp.status_code}",
                        details={"response": resp.text[:200]},
                    )
                data = resp.json()
                embeddings = [e["values"] for e in data.get("embeddings", [])]
                return embeddings
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError("Gemini embedding request timed out.") from exc
            except httpx.RequestError as exc:
                raise ProviderUnavailableError(f"Network error calling Gemini: {exc}") from exc


def get_embedding_provider() -> EmbeddingProvider:
    """Factory selecting configured provider or falling back to deterministic mock."""
    if settings.has_gemini_provider():
        return GeminiEmbeddingProvider()
    return DeterministicMockEmbeddingProvider()

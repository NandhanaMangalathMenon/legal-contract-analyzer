from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from core.exceptions import ConfigurationError
from llm.config import LLMRuntimeConfig, load_llm_runtime
from llm.embeddings import EmbeddingCache, HashingEmbedder

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Replaceable model interface. Agents must not call providers directly."""

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def generate_json(self, prompt: str, system: str | None = None, **kwargs: Any) -> Any:
        raw = self.generate(prompt, system=system, **kwargs)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                return json.loads(raw[start : end + 1])
            raise


class MockLLMClient(LLMClient):
    """Offline client used for tests and demo runs without credentials."""

    def __init__(self, runtime: LLMRuntimeConfig) -> None:
        self.runtime = runtime
        self.embedder = HashingEmbedder()
        self.cache = EmbeddingCache()

    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        return json.dumps(
            {
                "provider": "mock",
                "note": "MockLLMClient does not perform legal reasoning. Deterministic modules handle analysis.",
                "prompt_chars": len(prompt),
                "system_chars": len(system or ""),
            }
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            cached = self.cache.get(text, "hashing-v1")
            if cached is None:
                cached = self.embedder.embed_one(text)
                self.cache.put(text, "hashing-v1", cached)
            vectors.append(cached)
        return vectors


class GeminiLLMClient(LLMClient):
    def __init__(self, runtime: LLMRuntimeConfig) -> None:
        if not runtime.api_key:
            raise ConfigurationError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        self.runtime = runtime
        self.cache = EmbeddingCache()
        self._fallback = HashingEmbedder()

    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.runtime.model}:generateContent"
        )
        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM:\n{system}"}]})
        parts = [{"text": prompt}]
        
        media_paths = kwargs.get("media_paths", [])
        for path in media_paths:
            import base64
            from pathlib import Path
            import mimetypes
            
            p = Path(path)
            if not p.exists():
                continue
            data = p.read_bytes()
            b64 = base64.b64encode(data).decode("utf-8")
            mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            parts.append({"inlineData": {"mimeType": mime, "data": b64}})
            
        contents.append({"role": "user", "parts": parts})
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.runtime.temperature,
                "maxOutputTokens": self.runtime.max_output_tokens,
            },
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, params={"key": self.runtime.api_key}, json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            logger.warning("Unexpected Gemini response shape: %s", exc)
            return json.dumps(data)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.runtime.embedding_model}:embedContent"
        )
        for text in texts:
            cached = self.cache.get(text, self.runtime.embedding_model)
            if cached is not None:
                vectors.append(cached)
                continue
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(
                        url,
                        params={"key": self.runtime.api_key},
                        json={"model": f"models/{self.runtime.embedding_model}", "content": {"parts": [{"text": text}]}},
                    )
                    response.raise_for_status()
                    cached = response.json()["embedding"]["values"]
            except Exception as exc:  # noqa: BLE001 — fall back locally
                logger.warning("Gemini embed failed; using local hashing embedder: %s", exc)
                cached = self._fallback.embed_one(text)
            self.cache.put(text, self.runtime.embedding_model, cached)
            vectors.append(cached)
        return vectors


def get_llm_client(runtime: LLMRuntimeConfig | None = None) -> LLMClient:
    runtime = runtime or load_llm_runtime()
    if runtime.provider in {"mock", "local", "hash"}:
        return MockLLMClient(runtime)
    if runtime.provider == "gemini":
        return GeminiLLMClient(runtime)
    raise ConfigurationError(f"Unsupported LLM_PROVIDER: {runtime.provider}")

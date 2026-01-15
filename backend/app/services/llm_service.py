import httpx
import json
from typing import AsyncIterator

from app.config import settings


class LLMService:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def generate(self, prompt: str, context: str = "") -> str:
        """Generate a response using Ollama."""
        system_prompt = """You are a helpful assistant analyzing medical claims.
Use ONLY the provided context to answer questions. Be precise and accurate.
When asked about claim status (approved, denied, pending), look at the "Status:" field in each claim.
List all matching claims you find in the context. Do not make up or infer information."""

        full_prompt = f"""Context:
{context}

Question: {prompt}

Answer based on the context above:"""

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "system": system_prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"]

    async def generate_stream(self, prompt: str, context: str = "") -> AsyncIterator[str]:
        """Stream a response using Ollama."""
        system_prompt = """You are a helpful assistant analyzing medical claims.
Use ONLY the provided context to answer questions. Be precise and accurate.
When asked about claim status (approved, denied, pending), look at the "Status:" field in each claim.
List all matching claims you find in the context. Do not make up or infer information."""

        full_prompt = f"""Context:
{context}

Question: {prompt}

Answer based on the context above:"""

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "system": system_prompt,
                    "stream": True,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]

    async def health_check(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return any(m["name"] == self.model for m in models)
                return False
        except Exception:
            return False


# Singleton
_llm_service = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

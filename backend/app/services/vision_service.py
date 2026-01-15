import httpx
import base64
from typing import AsyncIterator

from app.config import settings


class VisionService:
    """Analyze images using Gemma 3 vision capabilities."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model  # gemma3:4b has vision

    async def analyze(self, image_base64: str, question: str = "What do you see in this image?") -> str:
        """Analyze an image and answer a question about it."""

        # Remove data URL prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        system_prompt = """You are a helpful assistant analyzing screen captures.
Describe what you see clearly and concisely.
If asked a specific question about the screen, focus your answer on that."""

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": question,
                    "system": system_prompt,
                    "images": [image_base64],
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"]

    async def analyze_stream(self, image_base64: str, question: str = "What do you see in this image?") -> AsyncIterator[str]:
        """Stream analysis of an image."""

        # Remove data URL prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        system_prompt = """You are a helpful assistant analyzing screen captures.
Describe what you see clearly and concisely.
If asked a specific question about the screen, focus your answer on that."""

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": question,
                    "system": system_prompt,
                    "images": [image_base64],
                    "stream": True,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]


# Singleton
_vision_service = None


def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service

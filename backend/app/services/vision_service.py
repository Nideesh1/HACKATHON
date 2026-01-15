"""Vision service using Gemma 3 GGUF with image support."""
import asyncio
import base64
from typing import Optional

from app.services.llm_service import get_llm_multimodal


class VisionService:
    """Analyze images using Gemma 3 vision capabilities (local GGUF)."""

    def __init__(self):
        self.model = None

    def _ensure_loaded(self):
        if self.model is None:
            self.model = get_llm_multimodal()
            if self.model is None:
                raise RuntimeError("Multimodal model not available. Download mmproj-model-f16-4B.gguf")

    async def analyze(self, image_base64: str, question: str = "What do you see in this image?") -> str:
        """Analyze an image and answer a question about it."""
        self._ensure_loaded()

        # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,...")
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        # Run in thread pool to not block async
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._analyze_sync,
            image_base64,
            question
        )
        return result

    def _analyze_sync(self, image_base64: str, question: str) -> str:
        """Synchronous image analysis for thread pool."""
        system_prompt = """You are a helpful assistant analyzing screen captures.
Describe what you see clearly and concisely.
If asked a specific question about the screen, focus your answer on that."""

        # Gemma 3 expects images in chat completion format
        # The image should be base64 encoded
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    },
                    {
                        "type": "text",
                        "text": question
                    }
                ]
            }
        ]

        try:
            response = self.model.create_chat_completion(
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            # If multimodal format doesn't work, try simple text prompt
            print(f"[Vision] Multimodal format failed: {e}, trying fallback...")

            # Fallback: just describe that we received an image
            fallback_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"[An image was shared] {question}"}
            ]

            response = self.model.create_chat_completion(
                messages=fallback_messages,
                max_tokens=1024,
                temperature=0.7,
            )
            return response["choices"][0]["message"]["content"] + "\n\n(Note: Image analysis may require additional model configuration)"


# Singleton
_vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service

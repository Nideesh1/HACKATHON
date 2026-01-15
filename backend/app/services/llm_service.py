"""LLM Service using llama-cpp-python with local GGUF model."""
import asyncio
from typing import AsyncIterator, Optional

from app.config import settings
from app.services.model_downloader import ensure_model_exists, download_mmproj

# Lazy load to avoid import overhead
_llm = None
_llm_multimodal = None  # Separate instance for vision


def get_llm():
    """Get or create the LLM instance for text (lazy loaded)."""
    global _llm

    if _llm is None:
        from llama_cpp import Llama

        model_path = ensure_model_exists()
        print(f"[LLM] Loading model from {model_path}...")

        _llm = Llama(
            model_path=str(model_path),
            n_ctx=settings.llm_context_size,
            n_threads=settings.llm_threads,
            verbose=False,
        )
        print("[LLM] Model loaded successfully!")

    return _llm


def get_llm_multimodal():
    """Get or create the multimodal LLM instance for vision (lazy loaded)."""
    global _llm_multimodal

    if _llm_multimodal is None:
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Llava16ChatHandler

        model_path = ensure_model_exists()
        mmproj_path = download_mmproj()

        if mmproj_path is None or not mmproj_path.exists():
            print("[LLM] WARNING: mmproj not available, vision will not work")
            return None

        print(f"[LLM] Loading multimodal model with vision support...")

        chat_handler = Llava16ChatHandler(clip_model_path=str(mmproj_path))

        _llm_multimodal = Llama(
            model_path=str(model_path),
            chat_handler=chat_handler,
            n_ctx=settings.llm_context_size,
            n_threads=settings.llm_threads,
            verbose=False,
        )
        print("[LLM] Multimodal model loaded successfully!")

    return _llm_multimodal


class LLMService:
    def __init__(self):
        self.model = None

    def _ensure_loaded(self):
        """Ensure model is loaded."""
        if self.model is None:
            self.model = get_llm()

    async def generate(self, prompt: str, context: str = "") -> str:
        """Generate a response using local GGUF model."""
        self._ensure_loaded()

        system_prompt = """You are a helpful assistant analyzing medical claims.
Use ONLY the provided context to answer questions. Be precise and accurate.
When asked about claim status (approved, denied, pending), look at the "Status:" field in each claim.
List all matching claims you find in the context. Do not make up or infer information."""

        if context:
            full_prompt = f"""Context:
{context}

Question: {prompt}

Answer based on the context above:"""
        else:
            # For general chat without RAG context
            full_prompt = prompt
            system_prompt = context if context else "You are a helpful voice assistant. Respond naturally and conversationally."

        # Run in thread pool to not block async
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._generate_sync,
            full_prompt,
            system_prompt
        )
        return result

    def _generate_sync(self, prompt: str, system_prompt: str) -> str:
        """Synchronous generation for thread pool."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = self.model.create_chat_completion(
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        return response["choices"][0]["message"]["content"]

    async def generate_stream(self, prompt: str, context: str = "") -> AsyncIterator[str]:
        """Stream a response (simplified - yields chunks)."""
        # For now, just yield the full response
        # Full streaming would require more complex threading
        response = await self.generate(prompt, context)
        yield response

    async def health_check(self) -> bool:
        """Check if model is loaded and working."""
        try:
            self._ensure_loaded()
            return self.model is not None
        except Exception:
            return False


# Singleton
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

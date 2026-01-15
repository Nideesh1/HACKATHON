"""Router service using FunctionGemma from HuggingFace."""
import json
import os
from typing import Literal, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

from app.config import settings

# Load .env file if it exists
load_dotenv()

# Lazy load to avoid slow startup
_router_model = None
_router_tokenizer = None


def get_router_model():
    """Load FunctionGemma model (lazy loaded)."""
    global _router_model, _router_tokenizer

    if _router_model is None:
        print(f"[Router] Loading FunctionGemma from {settings.router_model}...")
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch

        # Get HF token for gated model access
        token = os.getenv("HF_TOKEN")
        if token == "your_huggingface_token_here":
            token = None

        _router_tokenizer = AutoTokenizer.from_pretrained(
            settings.router_model,
            token=token
        )
        _router_model = AutoModelForCausalLM.from_pretrained(
            settings.router_model,
            torch_dtype=torch.float32,  # CPU friendly
            device_map="cpu",
            token=token
        )
        print("[Router] FunctionGemma loaded!")

    return _router_model, _router_tokenizer


@dataclass
class RouteDecision:
    action: Literal["analyze_screen", "query_documents", "general_chat"]
    question: str


class RouterService:
    """Uses FunctionGemma to route between screen analysis, document queries, and chat."""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.tools = [
            {
                "name": "analyze_screen",
                "description": "Take a screenshot and analyze what's on the user's screen. Use when user mentions: screen, monitor, display, looking at, what do you see.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "The question about the screen"}
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "query_documents",
                "description": "Search through documents and files. Use when user mentions: documents, files, claims, records, search, find, denied claims, approved claims, patient records.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "The search query"}
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "general_chat",
                "description": "General conversation, questions, math, greetings, help. Use for everything else.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "The message"}
                    },
                    "required": ["message"]
                }
            }
        ]

    def _ensure_loaded(self):
        if self.model is None:
            self.model, self.tokenizer = get_router_model()

    async def route(self, user_input: str) -> RouteDecision:
        """Determine which action to take based on user input."""
        import asyncio

        self._ensure_loaded()

        # Build the prompt for FunctionGemma
        tools_json = json.dumps(self.tools, indent=2)
        prompt = f"""You have access to these tools:
{tools_json}

Based on the user's message, decide which tool to call.

User: {user_input}

Call the appropriate tool with the user's message as the parameter. Respond with a JSON object containing "name" and "arguments"."""

        # Run in thread pool to not block async
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._route_sync, prompt, user_input)
        return result

    def _route_sync(self, prompt: str, user_input: str) -> RouteDecision:
        """Synchronous routing for thread pool."""
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=100,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract just the generated part (after the prompt)
        generated = response[len(prompt):].strip()
        print(f"[Router] FunctionGemma response: {generated}")

        # Try to parse as JSON
        try:
            # Find JSON in response
            start = generated.find("{")
            end = generated.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = generated[start:end]
                parsed = json.loads(json_str)
                func_name = parsed.get("name", "general_chat")
                args = parsed.get("arguments", {})
                question = args.get("question") or args.get("message") or user_input

                if func_name in ["analyze_screen", "query_documents", "general_chat"]:
                    print(f"[Router] Decision: {func_name}")
                    return RouteDecision(action=func_name, question=question)
        except json.JSONDecodeError:
            pass

        # Fallback: keyword matching
        lower = user_input.lower()
        if any(kw in lower for kw in ["screen", "display", "monitor", "see", "looking"]):
            return RouteDecision(action="analyze_screen", question=user_input)
        if any(kw in lower for kw in ["document", "file", "claim", "record", "search", "find"]):
            return RouteDecision(action="query_documents", question=user_input)

        return RouteDecision(action="general_chat", question=user_input)

    async def health_check(self) -> bool:
        """Check if FunctionGemma is loaded."""
        try:
            self._ensure_loaded()
            return self.model is not None
        except Exception:
            return False


# Singleton
_router_service: Optional[RouterService] = None


def get_router_service() -> RouterService:
    global _router_service
    if _router_service is None:
        _router_service = RouterService()
    return _router_service

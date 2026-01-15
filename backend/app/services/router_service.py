import httpx
import json
from typing import Literal
from dataclasses import dataclass

from app.config import settings


@dataclass
class RouteDecision:
    action: Literal["analyze_screen", "query_documents", "general_chat"]
    question: str


class RouterService:
    """Uses FunctionGemma to route between screen analysis and document queries."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = "functiongemma"
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "analyze_screen",
                    "description": "Take a screenshot. ONLY use when user says: screen, monitor, display, looking at, what do you see, show me what's on screen.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question"
                            }
                        },
                        "required": ["question"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_documents",
                    "description": "Search files. ONLY use when user EXPLICITLY says: search documents, search files, in my documents, in the files, look in docs, check my files, find in documents, which claims, denied claims, approved claims, patient records.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question"
                            }
                        },
                        "required": ["question"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "general_chat",
                    "description": "DEFAULT choice. Normal conversation, math, questions, greetings, help, jokes, explanations. Use this for EVERYTHING unless user explicitly mentions screen or documents/files/claims.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The message"
                            }
                        },
                        "required": ["message"]
                    }
                }
            }
        ]

    async def route(self, user_input: str) -> RouteDecision:
        """Determine whether to analyze screen or query documents."""
        messages = [
            {"role": "user", "content": user_input}
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": self.tools,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()

        message = result.get("message", {})
        tool_calls = message.get("tool_calls", [])

        if tool_calls:
            tool = tool_calls[0]
            func_name = tool["function"]["name"]
            args = tool["function"].get("arguments", {})
            # Handle both "question" and "message" parameter names
            question = args.get("question") or args.get("message") or user_input

            print(f"[Router] FunctionGemma decided: {func_name}")
            print(f"[Router] Input: {question}")

            return RouteDecision(
                action=func_name,
                question=question
            )

        # Default to general chat if no tool call
        print("[Router] No tool call, defaulting to general_chat")
        return RouteDecision(
            action="general_chat",
            question=user_input
        )

    async def health_check(self) -> bool:
        """Check if FunctionGemma is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return any(m["name"].startswith("functiongemma") for m in models)
                return False
        except Exception:
            return False


# Singleton
_router_service = None


def get_router_service() -> RouterService:
    global _router_service
    if _router_service is None:
        _router_service = RouterService()
    return _router_service

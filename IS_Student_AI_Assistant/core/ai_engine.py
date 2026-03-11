from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from config import Settings
from utils.json_utils import safe_json_loads, coerce_json_object


class LLMClient(Protocol):
    """Common interface for AI calls across modules."""

    def generate_json(self, task_name: str, prompt: str, schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        """Return a JSON object (dict). Must never raise to UI layer."""
        ...


@dataclass
class MockClient:
    """Offline client: deterministic responses that keep app functional."""
    def generate_json(self, task_name: str, prompt: str, schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        # Minimal but useful outputs per task
        lower = (prompt or "").lower()
        if task_name == "sql_generate":
            return {
                "sql": "/* Mock SQL */\nSELECT 1 AS demo;",
                "explanation": "Mock mode: returned a simple SELECT to keep the app runnable.",
                "warnings": ["GEMINI_API_KEY not set -> Offline mock response used."]
            }
        if task_name == "sql_explain":
            return {
                "explanation": "Mock mode: SQL explanation is limited. This query selects a constant value.",
                "issues": [],
                "optimized_sql": None
            }
        if task_name == "code_explain":
            lang = "sql" if "select" in lower or "create table" in lower else "python"
            return {
                "language": lang,
                "explanation": "Mock mode: This is a basic explanation. Provide GEMINI_API_KEY for richer output.",
                "issues": [],
                "corrected_code": prompt
            }
        # Generic fallback
        return {"note": "Mock response", "data": {}}


class GeminiClient:
    """Gemini-backed client (new google-genai SDK)."""
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        from google import genai  # NEW SDK
        self._client = genai.Client(api_key=api_key)

    def generate_json(self, task_name: str, prompt: str, schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        """Ask Gemini for strict JSON, parse robustly, never throw to UI."""
        try:
            system = (
                "You are an assistant that returns STRICT JSON only. "
                "No markdown, no code fences, no extra text. "
                "If unsure, return best-effort JSON matching the schema."
            )
            schema_text = f"JSON schema hint (informal): {schema_hint}"
            full_prompt = f"{system}\n\nTASK: {task_name}\n\n{schema_text}\n\nUSER_PROMPT:\n{prompt}"

            resp = self._client.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )

            text = (getattr(resp, "text", None) or "").strip()
            obj = safe_json_loads(text)
            return coerce_json_object(obj, fallback={})
        except Exception:
            return {}


def build_llm_client(settings: Settings) -> LLMClient:
    """Create Gemini client if key exists, otherwise Mock client."""
    if settings.GEMINI_API_KEY:
        try:
            return GeminiClient(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
        except Exception:
            return MockClient()
    return MockClient()


def llm_json_with_fallback(client: LLMClient, task_name: str, prompt: str, schema_hint: Dict[str, Any],
                           fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Call LLM, validate JSON is object, fallback if empty/invalid."""
    obj = client.generate_json(task_name=task_name, prompt=prompt, schema_hint=schema_hint)
    if not isinstance(obj, dict) or not obj:
        return fallback
    return obj
from __future__ import annotations

from core.ai_engine import LLMClient, llm_json_with_fallback
from core.schemas import CodeExplainResult

CODE_EXPLAIN_SCHEMA_HINT = {
    "language": "sql|python|unknown",
    "explanation": "string",
    "issues": ["string"],
    "corrected_code": "string"
}


class CodeEngine:
    """Explain/fix SQL/Python code via LLM (or offline mock)."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def explain(self, code_text: str) -> CodeExplainResult:
        """Explain code and highlight issues."""
        prompt = (
            "Analyze the given code (SQL or Python). "
            "Explain what it does, highlight problems, and suggest corrections.\n"
            "Return STRICT JSON.\n\n"
            f"CODE:\n{code_text}\n"
        )
        fallback = {
            "language": "unknown",
            "explanation": "Offline fallback explanation (Mock mode or Gemini failure).",
            "issues": [],
            "corrected_code": code_text
        }
        obj = llm_json_with_fallback(self.llm, "code_explain", prompt, CODE_EXPLAIN_SCHEMA_HINT, fallback)
        return CodeExplainResult(
            language=str(obj.get("language", "unknown")),
            explanation=str(obj.get("explanation", "")),
            issues=list(obj.get("issues", []) or []),
            corrected_code=str(obj.get("corrected_code", code_text)),
        )

    def fix(self, code_text: str) -> CodeExplainResult:
        """Return corrected code + issues."""
        prompt = (
            "Fix the given code (SQL or Python). "
            "Return corrected version and list the issues you fixed.\n"
            "Return STRICT JSON.\n\n"
            f"CODE:\n{code_text}\n"
        )
        fallback = {
            "language": "unknown",
            "explanation": "Offline fallback: no real fixing performed.",
            "issues": [],
            "corrected_code": code_text
        }
        obj = llm_json_with_fallback(self.llm, "code_explain", prompt, CODE_EXPLAIN_SCHEMA_HINT, fallback)
        return CodeExplainResult(
            language=str(obj.get("language", "unknown")),
            explanation=str(obj.get("explanation", "")),
            issues=list(obj.get("issues", []) or []),
            corrected_code=str(obj.get("corrected_code", code_text)),
        )

    def add_comments(self, code_text: str) -> CodeExplainResult:
        """Add helpful comments into code (Python) or inline SQL comments."""
        prompt = (
            "Add short, useful comments to the code (SQL or Python). "
            "Do not change logic unless necessary for correctness. "
            "Return STRICT JSON.\n\n"
            f"CODE:\n{code_text}\n"
        )
        fallback = {
            "language": "unknown",
            "explanation": "Offline fallback: returning original code.",
            "issues": [],
            "corrected_code": code_text
        }
        obj = llm_json_with_fallback(self.llm, "code_explain", prompt, CODE_EXPLAIN_SCHEMA_HINT, fallback)
        return CodeExplainResult(
            language=str(obj.get("language", "unknown")),
            explanation=str(obj.get("explanation", "")),
            issues=list(obj.get("issues", []) or []),
            corrected_code=str(obj.get("corrected_code", code_text)),
        )
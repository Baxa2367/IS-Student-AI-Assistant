from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional, Tuple

from core.ai_engine import LLMClient, llm_json_with_fallback
from core.schemas import SQLExplainResult, SQLGenResult
from utils.sqlite_runner import SQLiteRunResult, run_sqlite_script


SQL_GEN_SCHEMA_HINT = {
    "sql": "string (SQL script runnable in SQLite)",
    "explanation": "string",
    "warnings": ["string"]
}

SQL_EXPLAIN_SCHEMA_HINT = {
    "explanation": "string",
    "issues": ["string"],
    "optimized_sql": "string|null"
}


class SQLEngine:
    """Business logic for SQL Lab tab."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def generate_sql(self, ddl: str, task: str) -> SQLGenResult:
        """Generate SQL for given schema and task using LLM or Mock."""
        prompt = (
            "You are helping a student with SQLite SQL.\n"
            "Given the database schema DDL and a task, generate a correct SQL script.\n"
            "Return STRICT JSON.\n\n"
            f"DDL:\n{ddl}\n\nTASK:\n{task}\n"
        )
        fallback = {
            "sql": "/* Offline fallback */\nSELECT 1 AS demo;",
            "explanation": "Offline fallback: provide GEMINI_API_KEY for generation.",
            "warnings": ["Offline fallback used."]
        }
        obj = llm_json_with_fallback(self.llm, "sql_generate", prompt, SQL_GEN_SCHEMA_HINT, fallback)
        return SQLGenResult(
            sql=str(obj.get("sql", "")),
            explanation=str(obj.get("explanation", "")),
            warnings=list(obj.get("warnings", []) or []),
        )

    def explain_sql(self, sql_text: str) -> SQLExplainResult:
        """Explain/optimize SQL using LLM or Mock."""
        prompt = (
            "Explain what this SQL does, list issues/errors (if any), and provide an optimized version if possible.\n"
            "Return STRICT JSON.\n\n"
            f"SQL:\n{sql_text}\n"
        )
        fallback = {
            "explanation": "Offline fallback explanation.",
            "issues": [],
            "optimized_sql": None
        }
        obj = llm_json_with_fallback(self.llm, "sql_explain", prompt, SQL_EXPLAIN_SCHEMA_HINT, fallback)
        optimized = obj.get("optimized_sql", None)
        return SQLExplainResult(
            explanation=str(obj.get("explanation", "")),
            issues=list(obj.get("issues", []) or []),
            optimized_sql=str(optimized) if isinstance(optimized, str) and optimized.strip() else None
        )

    def optimize_sql(self, sql_text: str) -> str:
        """Shortcut: return only optimized SQL if LLM produced it; otherwise keep original."""
        exp = self.explain_sql(sql_text)
        return exp.optimized_sql or sql_text

    def run_in_sqlite(self, ddl: str, sql_text: str, max_rows: int = 100) -> SQLiteRunResult:
        """Run DDL + SQL script in an isolated SQLite in-memory DB."""
        script = (ddl or "").strip() + "\n\n" + (sql_text or "").strip()
        return run_sqlite_script(script=script, max_rows=max_rows)
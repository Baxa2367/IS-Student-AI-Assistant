from __future__ import annotations

import json
from typing import Any, Dict


def safe_json_loads(text: str) -> Any:
    """
    Try parse JSON robustly:
    - strips whitespace
    - if model returned extra text, try to extract first {...} block.
    """
    if text is None:
        return None
    s = text.strip()
    if not s:
        return None

    # First try direct parse
    try:
        return json.loads(s)
    except Exception:
        pass

    # Try extract object boundaries
    start = s.find("{")
    end = s.rfind("}")
    if 0 <= start < end:
        chunk = s[start:end + 1]
        try:
            return json.loads(chunk)
        except Exception:
            return None
    return None


def coerce_json_object(value: Any, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure dict output; otherwise return fallback."""
    return value if isinstance(value, dict) else fallback


def safe_json_dumps(obj: Any) -> str:
    """Dump JSON safely."""
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return "{}"
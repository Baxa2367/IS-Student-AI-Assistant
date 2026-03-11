from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SQLiteRunResult:
    ok: bool
    output_text: str
    error_text: str
    headers: List[str]
    rows: List[List[Any]]


def run_sqlite_script(script: str, max_rows: int = 100) -> SQLiteRunResult:
    """
    Run SQL script in SQLite in-memory database.
    Returns:
      - ok
      - output_text (human readable)
      - error_text (sqlite error if any)
      - headers/rows for SELECT
    """
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    headers: List[str] = []
    rows: List[List[Any]] = []
    output_lines: List[str] = []
    try:
        statements = _split_sql_statements(script or "")
        last_was_select = False
        for st in statements:
            st_clean = st.strip()
            if not st_clean:
                continue

            cur.execute(st_clean)

            # If it is a SELECT-like statement, fetch rows
            if _looks_like_select(st_clean):
                last_was_select = True
                fetched = cur.fetchmany(max_rows)
                if fetched:
                    headers = list(fetched[0].keys())
                    rows = [list(r) for r in fetched]
                else:
                    headers = []
                    rows = []
                output_lines.append(f"SELECT returned {len(rows)} row(s) (showing up to {max_rows}).")
            else:
                last_was_select = False

        con.commit()

        if not statements:
            output_lines.append("No SQL to run.")

        if not last_was_select:
            output_lines.append("SQL executed successfully.")

        return SQLiteRunResult(
            ok=True,
            output_text="\n".join(output_lines).strip(),
            error_text="",
            headers=headers,
            rows=rows
        )
    except sqlite3.Error as e:
        return SQLiteRunResult(
            ok=False,
            output_text="SQLite execution failed.",
            error_text=str(e),
            headers=[],
            rows=[]
        )
    finally:
        con.close()


def _looks_like_select(sql: str) -> bool:
    """Detect SELECT/CTE statements that return rows."""
    s = sql.strip().lower()
    return s.startswith("select") or s.startswith("with") or s.startswith("pragma") or s.startswith("explain")


def _split_sql_statements(script: str) -> List[str]:
    """
    Split by semicolon while respecting simple quoted strings.
    This is not a full SQL parser, but good enough for student labs.
    """
    s = script or ""
    out: List[str] = []
    buf: List[str] = []
    in_single = False
    in_double = False

    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
        elif ch == ";" and not in_single and not in_double:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        out.append("".join(buf))
    return out
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class DDLParseResult:
    tables: Dict[str, Dict[str, Any]]
    foreign_keys: List[Dict[str, str]]


_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<body>.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL
)

_FK_INLINE_RE = re.compile(
    r"(?P<col>[A-Za-z_][A-Za-z0-9_]*)\s+[A-Za-z0-9_()]+\s+.*?REFERENCES\s+(?P<rt>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<rc>[A-Za-z_][A-Za-z0-9_]*)\)",
    re.IGNORECASE
)

_FK_TABLE_RE = re.compile(
    r"FOREIGN\s+KEY\s*\((?P<col>[A-Za-z_][A-Za-z0-9_]*)\)\s+REFERENCES\s+(?P<rt>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<rc>[A-Za-z_][A-Za-z0-9_]*)\)",
    re.IGNORECASE
)

_PK_TABLE_RE = re.compile(
    r"PRIMARY\s+KEY\s*\((?P<cols>[^)]+)\)",
    re.IGNORECASE
)


def parse_ddl_create_tables(ddl: str) -> DDLParseResult:
    """
    Minimal DDL parser for CREATE TABLE ... (...); blocks.
    Extracts:
      - table name
      - columns (name + type)
      - PK columns
      - FK relationships
    """
    ddl = ddl or ""
    tables: Dict[str, Dict[str, Any]] = {}
    foreign_keys: List[Dict[str, str]] = []

    for m in _CREATE_TABLE_RE.finditer(ddl):
        tname = m.group("name")
        body = m.group("body")

        columns: List[Dict[str, str]] = []
        pk_cols: List[str] = []

        parts = _split_table_body(body)

        # First pass: detect table-level PK/FK constraints
        for part in parts:
            p = part.strip().rstrip(",")
            pk_m = _PK_TABLE_RE.search(p)
            if pk_m:
                cols = [c.strip() for c in pk_m.group("cols").split(",") if c.strip()]
                pk_cols.extend(cols)

            fk_m = _FK_TABLE_RE.search(p)
            if fk_m:
                foreign_keys.append({
                    "table": tname,
                    "column": fk_m.group("col"),
                    "ref_table": fk_m.group("rt"),
                    "ref_column": fk_m.group("rc"),
                })

        # Second pass: parse columns and inline constraints
        for part in parts:
            p = part.strip().rstrip(",")
            if not p or p.lower().startswith(("primary key", "foreign key", "constraint", "unique", "check")):
                continue

            tokens = p.split()
            if len(tokens) < 2:
                continue
            col_name = tokens[0].strip('`"')
            col_type = tokens[1].strip().upper()

            # Inline PK
            if re.search(r"\bPRIMARY\s+KEY\b", p, re.IGNORECASE):
                if col_name not in pk_cols:
                    pk_cols.append(col_name)

            # Inline FK
            fk_inline = _FK_INLINE_RE.search(p)
            if fk_inline:
                foreign_keys.append({
                    "table": tname,
                    "column": fk_inline.group("col"),
                    "ref_table": fk_inline.group("rt"),
                    "ref_column": fk_inline.group("rc"),
                })

            columns.append({"name": col_name, "type": col_type})

        tables[tname] = {"columns": columns, "pk": pk_cols}

    return DDLParseResult(tables=tables, foreign_keys=foreign_keys)


def _split_table_body(body: str) -> List[str]:
    """Split CREATE TABLE body by commas, respecting parentheses nesting."""
    s = body or ""
    out: List[str] = []
    buf: List[str] = []
    depth = 0
    in_single = False
    in_double = False

    for ch in s:
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            continue

        if in_single or in_double:
            buf.append(ch)
            continue

        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)

    if buf:
        out.append("".join(buf))
    return out
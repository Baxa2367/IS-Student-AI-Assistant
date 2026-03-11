from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Tuple

from core.schemas import ERMermaidResult
from utils.ddl_parser import parse_ddl_create_tables, DDLParseResult


class EREngine:
    """Build ER (Mermaid) from CREATE TABLE DDL."""

    def build_mermaid(self, ddl: str) -> ERMermaidResult:
        """Parse DDL and generate Mermaid ER diagram text."""
        parsed: DDLParseResult = parse_ddl_create_tables(ddl or "")

        lines: List[str] = ["erDiagram"]
        # Tables and columns
        for tname, tdef in parsed.tables.items():
            lines.append(f"    {tname} {{")
            for col in tdef["columns"]:
                # Mermaid ER syntax: type name (type optional). We'll use TEXT as generic.
                c = col["name"]
                ctype = col.get("type", "TEXT")
                marker = ""
                if c in tdef.get("pk", []):
                    marker = " PK"
                lines.append(f"        {ctype} {c}{marker}")
            lines.append("    }")

        # Relationships (FK)
        rels: List[str] = []
        for fk in parsed.foreign_keys:
            src_t = fk["table"]
            src_c = fk["column"]
            ref_t = fk["ref_table"]
            ref_c = fk["ref_column"]

            # Assume many-to-one: many src rows -> one ref row
            rel_line = f"    {ref_t} ||--o{{ {src_t} : \"{ref_c} -> {src_c}\""
            rels.append(rel_line)

        lines.extend(rels)

        return ERMermaidResult(
            mermaid="\n".join(lines),
            tables=list(parsed.tables.keys()),
            relationships=rels
        )
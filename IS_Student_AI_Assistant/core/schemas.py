from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SQLGenResult:
    sql: str
    explanation: str
    warnings: List[str]


@dataclass
class SQLExplainResult:
    explanation: str
    issues: List[str]
    optimized_sql: Optional[str] = None


@dataclass
class CodeExplainResult:
    language: str
    explanation: str
    issues: List[str]
    corrected_code: str


@dataclass
class ERMermaidResult:
    mermaid: str
    tables: List[str]
    relationships: List[str]


@dataclass
class NormalizationReport:
    candidate_keys: List[str]
    nf_report: str
    decomposition: str
    steps: List[str]
    meta: Dict[str, Any]
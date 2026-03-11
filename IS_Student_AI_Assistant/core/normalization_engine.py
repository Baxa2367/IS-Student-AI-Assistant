from __future__ import annotations

import itertools
from dataclasses import asdict
from typing import Dict, FrozenSet, List, Set, Tuple

from core.schemas import NormalizationReport


def _parse_relation_schema(schema_text: str) -> List[str]:
    """Parse R(A,B,C) into attribute list."""
    s = (schema_text or "").strip()
    if "(" not in s or ")" not in s:
        return []
    inside = s[s.find("(") + 1:s.rfind(")")]
    attrs = [a.strip() for a in inside.split(",") if a.strip()]
    # remove duplicates preserving order
    seen = set()
    out = []
    for a in attrs:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


def _parse_fds(fd_text: str) -> List[Tuple[FrozenSet[str], FrozenSet[str]]]:
    """
    Parse functional dependencies:
      A->B, (A,C)->D, A->B,C
    Returns list of (X, Y) where both are frozensets.
    """
    text = (fd_text or "").strip()
    if not text:
        return []

    parts = [p.strip() for p in text.split(",") if p.strip()]
    fds: List[Tuple[FrozenSet[str], FrozenSet[str]]] = []

    # Join tokens that belong to the same FD if user wrote "A->B, C->D"
    # Simple approach: treat segments containing '->' as starts.
    merged: List[str] = []
    buf = ""
    for p in parts:
        if "->" in p:
            if buf:
                merged.append(buf.strip())
            buf = p
        else:
            # continuation of RHS for previous FD
            if buf:
                buf += "," + p
            else:
                # orphan token, ignore
                pass
    if buf:
        merged.append(buf.strip())

    for fd in merged:
        if "->" not in fd:
            continue
        left, right = fd.split("->", 1)
        left = left.strip()
        right = right.strip()

        def parse_side(side: str) -> Set[str]:
            side = side.strip()
            if side.startswith("(") and side.endswith(")"):
                side = side[1:-1]
            tokens = [t.strip() for t in side.split(",") if t.strip()]
            return set(tokens)

        X = frozenset(parse_side(left))
        Y = frozenset(parse_side(right))
        if X and Y:
            fds.append((X, Y))
    return fds


def closure(attrs: Set[str], fds: List[Tuple[FrozenSet[str], FrozenSet[str]]]) -> Set[str]:
    """Compute attribute closure of attrs under given functional dependencies."""
    result = set(attrs)
    changed = True
    while changed:
        changed = False
        for X, Y in fds:
            if set(X).issubset(result) and not set(Y).issubset(result):
                result |= set(Y)
                changed = True
    return result


def is_superkey(X: Set[str], all_attrs: Set[str], fds: List[Tuple[FrozenSet[str], FrozenSet[str]]]) -> bool:
    """Check if X is a superkey for relation(all_attrs) under fds."""
    return closure(set(X), fds) >= set(all_attrs)


def find_candidate_keys(attrs: List[str], fds: List[Tuple[FrozenSet[str], FrozenSet[str]]]) -> List[Set[str]]:
    """Find candidate keys by brute force (reasonable for student-sized schemas)."""
    A = set(attrs)
    if not A:
        return []
    keys: List[Set[str]] = []
    # Try subsets by increasing size
    for r in range(1, len(attrs) + 1):
        for comb in itertools.combinations(attrs, r):
            X = set(comb)
            if is_superkey(X, A, fds):
                # minimal?
                if not any(k.issubset(X) for k in keys):
                    keys.append(X)
    return keys


def nf_checks(attrs: List[str], fds: List[Tuple[FrozenSet[str], FrozenSet[str]]], cand_keys: List[Set[str]]) -> Dict[str, bool]:
    """Check 1NF/2NF/3NF/BCNF using standard FD-based heuristics."""
    A = set(attrs)
    prime_attrs = set().union(*cand_keys) if cand_keys else set()

    # 1NF: assume atomic values (cannot be proven from FDs)
    is_1nf = True

    # 2NF: no partial dependency of non-prime attribute on a proper subset of any candidate key
    is_2nf = True
    for K in cand_keys:
        if len(K) <= 1:
            continue
        for X, Y in fds:
            Xs = set(X)
            Ys = set(Y)
            if Xs.issubset(K) and Xs != K:
                # partial dependency candidate
                if any(a not in prime_attrs for a in Ys):
                    is_2nf = False

    # 3NF: for every X->A, either X is superkey OR A is prime OR A in X (trivial)
    is_3nf = True
    for X, Y in fds:
        Xs = set(X)
        for a in set(Y):
            if a in Xs:
                continue
            if is_superkey(Xs, A, fds):
                continue
            if a in prime_attrs:
                continue
            is_3nf = False

    # BCNF: for every non-trivial X->Y, X is superkey
    is_bcnf = True
    for X, Y in fds:
        Xs = set(X)
        Ys = set(Y)
        if Ys.issubset(Xs):
            continue  # trivial
        if not is_superkey(Xs, A, fds):
            is_bcnf = False

    return {"1NF": is_1nf, "2NF": is_2nf, "3NF": is_3nf, "BCNF": is_bcnf}


def decompose_bcnf(attrs: List[str], fds: List[Tuple[FrozenSet[str], FrozenSet[str]]]) -> Tuple[List[Set[str]], List[str]]:
    """
    Basic BCNF decomposition algorithm:
      While exists X->Y violating BCNF in current relation R:
        R1 = X ∪ Y
        R2 = R - (Y - X)
    Note: This does not guarantee dependency preservation; we report that.
    """
    steps: List[str] = []
    relations: List[Set[str]] = [set(attrs)]
    if not attrs:
        return [], ["No attributes to decompose."]

    changed = True
    while changed:
        changed = False
        new_relations: List[Set[str]] = []
        for R in relations:
            # Consider only FDs relevant to R
            relevant_fds = []
            for X, Y in fds:
                if set(X).issubset(R) and set(Y).issubset(R):
                    relevant_fds.append((X, Y))

            violation_found = False
            for X, Y in relevant_fds:
                Xs, Ys = set(X), set(Y)
                if Ys.issubset(Xs):
                    continue
                if not is_superkey(Xs, R, relevant_fds):
                    violation_found = True
                    changed = True
                    R1 = Xs | Ys
                    R2 = R - (Ys - Xs)
                    steps.append(
                        f"BCNF violation in R({','.join(sorted(R))}): "
                        f"{'(' + ','.join(sorted(Xs)) + ')'} -> {','.join(sorted(Ys))} "
                        f"where X is not a superkey. Decompose into "
                        f"R1({','.join(sorted(R1))}) and R2({','.join(sorted(R2))})."
                    )
                    new_relations.append(R1)
                    new_relations.append(R2)
                    break
            if not violation_found:
                new_relations.append(R)

        # Deduplicate by frozenset
        uniq = []
        seen = set()
        for r in new_relations:
            fr = frozenset(r)
            if fr not in seen:
                seen.add(fr)
                uniq.append(r)
        relations = uniq

    return relations, steps


class NormalizationEngine:
    """Core normalization logic for the Normalization tab."""

    def analyze(self, relation_schema: str, fd_text: str) -> NormalizationReport:
        """Compute candidate keys, NF checks, and BCNF decomposition report."""
        attrs = _parse_relation_schema(relation_schema)
        fds = _parse_fds(fd_text)

        steps: List[str] = []
        steps.append(f"Parsed attributes: {attrs if attrs else '∅'}")
        steps.append(f"Parsed FDs: {len(fds)}")

        cand_keys = find_candidate_keys(attrs, fds)
        cand_keys_str = [",".join(sorted(k)) for k in cand_keys] if cand_keys else []
        steps.append(f"Candidate keys found: {cand_keys_str if cand_keys_str else 'None'}")

        checks = nf_checks(attrs, fds, cand_keys)
        nf_lines = [
            "Normalization check:",
            f"  1NF: {'YES (assumed atomic values)' if checks['1NF'] else 'NO'}",
            f"  2NF: {'YES' if checks['2NF'] else 'NO'}",
            f"  3NF: {'YES' if checks['3NF'] else 'NO'}",
            f"  BCNF: {'YES' if checks['BCNF'] else 'NO'}",
        ]

        relations, d_steps = decompose_bcnf(attrs, fds)
        steps.extend(d_steps)

        decomp_lines = []
        if relations:
            decomp_lines.append("BCNF decomposition result (relations):")
            for i, r in enumerate(relations, 1):
                decomp_lines.append(f"  R{i}({','.join(sorted(r))})")
            decomp_lines.append("")
            decomp_lines.append("Note: This BCNF decomposition may NOT preserve all dependencies.")
        else:
            decomp_lines.append("No decomposition produced.")

        return NormalizationReport(
            candidate_keys=cand_keys_str,
            nf_report="\n".join(nf_lines),
            decomposition="\n".join(decomp_lines),
            steps=steps,
            meta={
                "attributes": attrs,
                "fds": [({"X": sorted(list(X)), "Y": sorted(list(Y))}) for X, Y in fds],
                "checks": checks,
            }
        )

    def find_keys_only(self, relation_schema: str, fd_text: str) -> List[str]:
        """Compute only candidate keys."""
        attrs = _parse_relation_schema(relation_schema)
        fds = _parse_fds(fd_text)
        cand_keys = find_candidate_keys(attrs, fds)
        return [",".join(sorted(k)) for k in cand_keys]
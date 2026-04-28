"""Cyclomatic complexity computation (Reviewer 2, Weakness 3).

Used to stratify the evaluation set into low / medium / high complexity bins
(Table Q in §VI.A). Production setups use solc-mcc on real Solidity ASTs;
this module provides a regex-based fallback that is good enough for the
synthetic corpus and CI tests.
"""
from __future__ import annotations

import re
from typing import Dict

# Branch keywords whose presence increments the cyclomatic count.
_BRANCH_TOKENS = (
    r"\bif\b", r"\belse\s+if\b", r"\bfor\b", r"\bwhile\b",
    r"\bcase\b", r"\bcatch\b", r"\?\s*[^:]+\s*:",     # ternary
    r"\&\&", r"\|\|", r"\brequire\b", r"\bassert\b",
)
_BRANCH_RE = re.compile("|".join(_BRANCH_TOKENS))
_FUNCTION_RE = re.compile(r"\bfunction\s+(\w+)\s*\(")


def cyclomatic_complexity(source: str) -> int:
    """Estimate cyclomatic complexity of an entire contract.

    Result is `1 + #branches`, summed over all functions. Used for binning,
    not for compiler-grade analysis.
    """
    return 1 + len(_BRANCH_RE.findall(source))


def per_function_complexity(source: str) -> Dict[str, int]:
    """Return a per-function cyclomatic-complexity map."""
    out: Dict[str, int] = {}
    matches = list(_FUNCTION_RE.finditer(source))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        body = source[start:end]
        out[m.group(1)] = cyclomatic_complexity(body)
    return out


def complexity_bin(value: int) -> str:
    """Bin into the {low, medium, high} buckets used by Table Q."""
    if value < 10:
        return "low"
    if value <= 30:
        return "medium"
    return "high"

"""Rule-based static analyzers for known SWC patterns.

These complement bounded symbolic execution by catching syntactically obvious
issues fast. The Slither / Oyente comparison in the paper (Section VII) treats
this layer as analogous to those tools, with BELMA's advantage coming from the
downstream coupling to repair + re-verification (R1-C2).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable, List, Pattern

from belma.types import Contract, SWC, Vulnerability

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class StaticRule:
    swc: SWC
    name: str
    pattern: Pattern[str]
    severity: str
    confidence: float
    description: str

    def scan(self, source: str) -> List[Vulnerability]:
        vulns: List[Vulnerability] = []
        for m in self.pattern.finditer(source):
            line = source.count("\n", 0, m.start()) + 1
            vulns.append(
                Vulnerability(
                    swc=self.swc,
                    location=(line, line),
                    function_name=_enclosing_function(source, m.start()),
                    description=self.description,
                    severity=self.severity,
                    confidence=self.confidence,
                    raw_context=_extract_context(source, m.start()),
                )
            )
        return vulns


def _enclosing_function(source: str, offset: int) -> str:
    head = source[:offset]
    matches = re.findall(r"function\s+(\w+)\s*\(", head)
    return matches[-1] if matches else "<top-level>"


def _extract_context(source: str, offset: int, lines_before: int = 5,
                     lines_after: int = 5) -> str:
    line_no = source.count("\n", 0, offset)
    lines = source.split("\n")
    start = max(0, line_no - lines_before)
    end = min(len(lines), line_no + lines_after + 1)
    return "\n".join(lines[start:end])


# ----------------------------------------------------------------------
# default rule catalog
# ----------------------------------------------------------------------
DEFAULT_RULES: List[StaticRule] = [
    StaticRule(
        swc=SWC.REENTRANCY,
        name="call-before-state-update",
        pattern=re.compile(r"\.call\.value\s*\(.*?\)\s*\(.*?\)", re.DOTALL),
        severity="high",
        confidence=0.6,
        description="Low-level call.value used; possible reentrancy if state "
                    "is updated after the call.",
    ),
    StaticRule(
        swc=SWC.UNCHECKED_CALL,
        name="unchecked-low-level-call",
        pattern=re.compile(r"^[ \t]*\w+\.call\(.*?\)\s*;", re.MULTILINE),
        severity="medium",
        confidence=0.5,
        description="Return value of low-level call is not checked.",
    ),
    StaticRule(
        swc=SWC.INTEGER_OVERFLOW,
        name="unchecked-arith-pre-0.8",
        pattern=re.compile(r"\b(\w+)\s*([+\-*])\s*(\w+)\s*;"),
        severity="medium",
        confidence=0.3,
        description="Possible unchecked arithmetic in pre-0.8 Solidity.",
    ),
    StaticRule(
        swc=SWC.TIMESTAMP_DEP,
        name="block-timestamp-control",
        pattern=re.compile(r"\bblock\.timestamp\b|\bnow\b"),
        severity="low",
        confidence=0.4,
        description="Reliance on block.timestamp; miner-manipulable.",
    ),
    StaticRule(
        swc=SWC.AUTHORIZATION,
        name="missing-onlyowner",
        pattern=re.compile(
            r"function\s+\w+\s*\([^)]*\)\s+(public|external)(?!\s+(view|pure|onlyOwner))",
        ),
        severity="high",
        confidence=0.4,
        description="Public/external function without authorization modifier.",
    ),
]


class RuleBasedDetector:
    """Apply the rule catalog to a contract and return all matches."""

    def __init__(self, rules: List[StaticRule] | None = None):
        self.rules = list(rules) if rules is not None else list(DEFAULT_RULES)

    def scan(self, contract: Contract) -> List[Vulnerability]:
        out: List[Vulnerability] = []
        for rule in self.rules:
            try:
                out.extend(rule.scan(contract.source))
            except re.error as e:
                log.warning("Rule %s failed: %s", rule.name, e)
        return out

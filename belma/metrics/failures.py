"""Failure taxonomy (Reviewer 2, Other Comment 3).

Distinguishes:
    LOCAL  — failures attributable to the testbed environment (RAM, model
             choice, RPC quotas) and addressable through engineering work.
    FUNDAMENTAL — failures attributable to engine-level constraints
             (path explosion, SMT solver timeouts, specification language)
             and addressable only through methodological advances.

The taxonomy table in `docs/FAILURE_TAXONOMY.md` enumerates each cause and
its mitigation path.
"""
from __future__ import annotations

import enum
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


class FailureCategory(str, enum.Enum):
    LOCAL = "local"
    FUNDAMENTAL = "fundamental"


# Authoritative cause -> category mapping. Keep aligned with FAILURE_TAXONOMY.md.
CAUSE_CATEGORY: Dict[str, FailureCategory] = {
    "loop_bound_truncated":              FailureCategory.FUNDAMENTAL,
    "inter_contract_depth_exceeded":     FailureCategory.FUNDAMENTAL,
    "smt_timeout":                       FailureCategory.FUNDAMENTAL,
    "delegate_call_summary_limit":       FailureCategory.FUNDAMENTAL,
    "property_not_in_swc_vocab":         FailureCategory.FUNDAMENTAL,
    "obfuscation_defeats_ast_similarity": FailureCategory.FUNDAMENTAL,
    "memory_exhaustion":                 FailureCategory.LOCAL,
    "llm_context_window_truncation":     FailureCategory.LOCAL,
    "network_sync_gap":                  FailureCategory.LOCAL,
    "rpc_rate_limit":                    FailureCategory.LOCAL,
}

MITIGATION: Dict[str, str] = {
    "loop_bound_truncated":              "Larger k, summary abstractions, modular verification",
    "inter_contract_depth_exceeded":     "Compositional verification, summary inference",
    "smt_timeout":                       "Solver portfolio, abstraction refinement",
    "delegate_call_summary_limit":       "Deeper modeling of upgradable proxy patterns",
    "property_not_in_swc_vocab":         "Property inference, human-in-loop review",
    "obfuscation_defeats_ast_similarity": "Semantic-only embeddings, adversarial training",
    "memory_exhaustion":                 "Distributed verification, larger-memory machines",
    "llm_context_window_truncation":     "Long-context models, hierarchical prompting",
    "network_sync_gap":                  "Pinned-block analysis, cached state",
    "rpc_rate_limit":                    "Self-hosted node, dedicated infrastructure",
}


@dataclass
class FailureRecord:
    contract_name: str
    cause: str
    category: FailureCategory
    mitigation: str
    note: Optional[str] = None

    @classmethod
    def from_cause(cls, contract_name: str, cause: str,
                   note: Optional[str] = None) -> "FailureRecord":
        return cls(
            contract_name=contract_name,
            cause=cause,
            category=CAUSE_CATEGORY.get(cause, FailureCategory.LOCAL),
            mitigation=MITIGATION.get(cause, "—"),
            note=note,
        )


@dataclass
class FailureLog:
    """Append-only log of failures observed during evaluation runs."""
    records: List[FailureRecord] = field(default_factory=list)

    def add(self, record: FailureRecord) -> None:
        self.records.append(record)

    def summary(self) -> Dict[str, Dict[str, int]]:
        cat_counts: Counter = Counter()
        cause_counts: Counter = Counter()
        for r in self.records:
            cat_counts[r.category.value] += 1
            cause_counts[r.cause] += 1
        return {
            "by_category": dict(cat_counts),
            "by_cause": dict(cause_counts),
            "total": {"count": len(self.records)},
        }

    def dump_jsonl(self, path: str) -> None:
        with open(path, "w") as fh:
            for r in self.records:
                d = asdict(r)
                d["category"] = r.category.value
                fh.write(json.dumps(d) + "\n")

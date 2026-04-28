"""Shared dataclasses used across detection and repair layers."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Platform(str, Enum):
    ETHEREUM = "ethereum"
    FABRIC = "fabric"
    EOS = "eos"


class SWC(str, Enum):
    """Subset of the Smart Contract Weakness Classification we target."""
    REENTRANCY = "SWC-107"
    INTEGER_OVERFLOW = "SWC-101"
    UNCHECKED_CALL = "SWC-104"
    TIMESTAMP_DEP = "SWC-116"
    TX_ORDER_DEP = "SWC-114"
    AUTHORIZATION = "SWC-115"


@dataclass
class Contract:
    """A smart contract under analysis. Holds source, bytecode, and platform."""
    name: str
    source: str
    platform: Platform
    bytecode: Optional[str] = None
    abi: Optional[List[Dict[str, Any]]] = None
    loc: int = 0
    cyclomatic_complexity: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Vulnerability:
    """A single detected vulnerability."""
    swc: Optional[SWC]                    # None means non-SWC (Beyond-SWC pipeline)
    location: Tuple[int, int]             # (line_start, line_end)
    function_name: str
    description: str
    severity: str                          # high / medium / low / advisory
    confidence: float                      # 0.0–1.0
    raw_context: str = ""                  # ~30 lines around the site
    ast_path: List[str] = field(default_factory=list)   # canonical AST path

    @property
    def is_beyond_swc(self) -> bool:
        return self.swc is None


@dataclass
class StructuredContext:
    """Layer-1 → Layer-2 hand-off (AST + metadata, see Fig. 1 of the paper)."""
    contract: Contract
    vulnerability: Vulnerability
    ast_node: Dict[str, Any]
    enclosing_function: str
    state_variables: List[str]
    call_targets: List[str]
    bytecode_slice: Optional[str] = None


@dataclass
class Patch:
    """Candidate or accepted patch for a single vulnerability."""
    vulnerability: Vulnerability
    patched_source: str
    diff: str
    bias_score: float = float("inf")
    error_score: float = float("inf")
    iterations: int = 0
    accepted: bool = False
    rejection_reason: Optional[str] = None
    # latency decomposition (R1-C3)
    t_gen_ms: float = 0.0
    t_ref_ms: float = 0.0
    t_val_ms: float = 0.0


@dataclass
class DetectionResult:
    contract: Contract
    vulnerabilities: List[Vulnerability]
    coverage: float                # path-coverage fraction of bounded exploration
    runtime_ms: float
    k_bound_used: int
    timed_out: bool = False


@dataclass
class RepairResult:
    contract: Contract
    patches: List[Patch]
    repaired_source: Optional[str] = None
    runtime_ms: float = 0.0
    rsr: float = 0.0               # local repair success rate for this contract


@dataclass
class PipelineResult:
    detection: DetectionResult
    repair: RepairResult
    capability_metrics: Dict[str, float] = field(default_factory=dict)
    infrastructure_metrics: Dict[str, float] = field(default_factory=dict)

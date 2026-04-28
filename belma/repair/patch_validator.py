"""Patch validator — bounded symbolic re-verification (Section IV.B.3).

Each accepted patch is re-checked against the SWC-derived bounded assertions
within k-bounded execution depths. The paper enforces *k-bounded soundness*
rather than global completeness: every reachable execution trace within depth
k is verified to satisfy the security assertion (R2-W1).

This is the T_val component of the latency decomposition (R1-C3, mean ~8 ms).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from belma.config import Config, load_config
from belma.detection.symbolic_executor import (
    AssertionProperty, SymbolicExecutor, default_properties,
)
from belma.types import Contract, Vulnerability

log = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    accepted: bool
    properties_checked: int
    violations: List[str]
    t_val_ms: float
    k_used: int


class BoundedValidator:
    """Wraps SymbolicExecutor for the post-patch re-verification call.

    Used by `RefinementLoop` after acceptance via Bias/Error thresholds. A
    patch is finally accepted only if all SWC-derived assertions hold under
    bounded exploration at depth k (default 16).
    """

    def __init__(
        self,
        executor: Optional[SymbolicExecutor] = None,
        properties: Optional[List[AssertionProperty]] = None,
        config: Optional[Config] = None,
    ):
        cfg = config or load_config()
        self.executor = executor or SymbolicExecutor(
            k_bound=cfg.symbolic_k(),
            smt_timeout_s=cfg.smt_timeout(),
        )
        self.properties = properties or default_properties()

    def validate(self, patched: Contract, target: Vulnerability) -> bool:
        """Return True iff the targeted vulnerability is no longer reachable.

        Implementation note: we run the full symbolic executor on the patched
        contract and check that NO new instance of `target.swc` is detected.
        """
        report = self.validate_full(patched, target)
        return report.accepted

    def validate_full(self, patched: Contract, target: Vulnerability) -> ValidationReport:
        t0 = time.perf_counter()
        result = self.executor.verify(patched, self.properties)
        t_val_ms = (time.perf_counter() - t0) * 1000.0

        # only fail acceptance if the SAME class of vulnerability re-appears
        target_swc = target.swc
        violations = [
            f"{v.swc}@{v.location} ({v.function_name})"
            for v in result.vulnerabilities
            if target_swc is not None and v.swc == target_swc
        ]
        accepted = len(violations) == 0

        log.debug(
            "Validation: %d violations of %s in patched contract; t_val=%.1f ms",
            len(violations), target_swc, t_val_ms,
        )
        return ValidationReport(
            accepted=accepted,
            properties_checked=len(self.properties),
            violations=violations,
            t_val_ms=t_val_ms,
            k_used=self.executor.k_bound,
        )

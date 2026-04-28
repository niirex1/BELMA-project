"""Infrastructure metrics (R1-C2).

These measure the engineering layer (DHT distribution, caching, batching,
parallelism) and reflect deployment efficiency rather than tool capability.
Definitions follow Eqs. (13)–(14) of the paper.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class InfrastructureMetrics:
    # Eq. 13
    ob: float = 0.0       # observed block overhead
    tb: float = 1.0       # baseline block size
    t_dual: float = 0.0   # total runtime, dual-layer pipeline
    t_single: float = 0.0  # total runtime, single-layer baseline

    # Eq. 14
    oc: float = 0.0       # observed code-efficiency numerator
    tc: float = 1.0       # baseline code-efficiency denominator
    nt: int = 0           # transactions completed in time-window
    t_window: float = 1.0  # length of time window (s)
    response_times_ms: List[float] = field(default_factory=list)

    # ---- properties ----
    @property
    def bor(self) -> float:
        """Block overhead rate = ob / tb (Eq. 13)."""
        return self.ob / self.tb if self.tb else 0.0

    @property
    def eto(self) -> float:
        """Execution time overhead = t_dual - t_single (Eq. 13)."""
        return self.t_dual - self.t_single

    @property
    def ce(self) -> float:
        """Code efficiency = oc / tc (Eq. 14)."""
        return self.oc / self.tc if self.tc else 0.0

    @property
    def tp(self) -> float:
        """Throughput in transactions per second (Eq. 14)."""
        return self.nt / self.t_window if self.t_window else 0.0

    @property
    def latency(self) -> float:
        """Mean response latency (Eq. 14)."""
        if not self.response_times_ms:
            return 0.0
        return sum(self.response_times_ms) / len(self.response_times_ms)

    def to_dict(self) -> Dict[str, float]:
        return {
            "BOR": self.bor,
            "ETO": self.eto,
            "CE": self.ce,
            "TP": self.tp,
            "L_ms": self.latency,
        }

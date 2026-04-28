"""Latency decomposition (Reviewer 1, Comment 3).

Manuscript §V.E paragraph (f). Per-vulnerability repair latency decomposes:

    T_repair^(v) = T_gen^(v) + Σ_i T_ref^(v,i) + T_val^(v)

with the abstract's "8 ms validation latency" referring specifically to T_val
(the bounded symbolic re-check stage), NOT the full per-vulnerability repair
time, which is the 180–280 ms band reported in Fig. 4.

This module aggregates per-stage timings recorded by `RefinementLoop`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, List

from belma.types import Patch


@dataclass
class StageStats:
    samples: List[float] = field(default_factory=list)

    @property
    def mean_ms(self) -> float:
        return mean(self.samples) if self.samples else 0.0

    def percentile(self, p: float) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        idx = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
        return s[idx]


@dataclass
class LatencyDecomposition:
    """Aggregator over a population of patches.

    Usage:
        ld = LatencyDecomposition()
        for patch in repair_result.patches:
            ld.record(patch)
        report = ld.summary()
    """
    t_gen: StageStats = field(default_factory=StageStats)
    t_ref: StageStats = field(default_factory=StageStats)
    t_val: StageStats = field(default_factory=StageStats)
    iterations: List[int] = field(default_factory=list)

    def record(self, patch: Patch) -> None:
        self.t_gen.samples.append(patch.t_gen_ms)
        self.t_ref.samples.append(patch.t_ref_ms)
        self.t_val.samples.append(patch.t_val_ms)
        self.iterations.append(patch.iterations)

    def total_ms(self) -> List[float]:
        return [
            self.t_gen.samples[i] + self.t_ref.samples[i] + self.t_val.samples[i]
            for i in range(len(self.t_gen.samples))
        ]

    def summary(self) -> Dict[str, Dict[str, float]]:
        totals = self.total_ms()
        mean_total = mean(totals) if totals else 0.0
        return {
            "T_gen":   {"mean_ms": self.t_gen.mean_ms,
                        "p95_ms": self.t_gen.percentile(95)},
            "T_ref":   {"mean_ms": self.t_ref.mean_ms,
                        "p95_ms": self.t_ref.percentile(95)},
            "T_val":   {"mean_ms": self.t_val.mean_ms,
                        "p95_ms": self.t_val.percentile(95)},
            "T_repair_total": {"mean_ms": mean_total},
            "k_mean":  {"value": mean(self.iterations) if self.iterations else 0.0},
        }

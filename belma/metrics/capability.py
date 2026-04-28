"""Capability metrics — intrinsic to the analysis pipeline (R1-C2).

These metrics measure the quality of detection and repair OUTPUT and are
independent of the deployment infrastructure (DHT, cache, batch). The
single-node ablation in `experiments/single_node_ablation.py` confirms
they shift by less than 0.4 pp when infrastructure features are disabled.

Definitions follow Eqs. (11)–(19) of the paper.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence


@dataclass
class CapabilityMetrics:
    """Holds the per-evaluation numbers reported in §VI.A and Table IV.

    Computed from raw confusion-matrix counts (TP, FP, TN, FN) plus the
    repair-attempt counters (vd, vt, rs, rt, ep, tp, pc, pt).
    """

    tp: int = 0    # vulnerabilities correctly detected
    fp: int = 0
    tn: int = 0
    fn: int = 0

    # repair counters (Eq. 11)
    vd: int = 0    # vulnerabilities detected
    vt: int = 0    # total vulnerabilities (ground truth)
    rs: int = 0    # successful repairs
    rt: int = 0    # repair attempts

    # coverage / time (Eq. 12)
    pc: int = 0    # paths covered
    pt: int = 0    # paths total

    # repair efficacy (Eq. 15)
    ep: int = 0    # effective patches (semantically valid + property-satisfying)
    tp_repair: int = 0    # total patches generated

    # ----- Eq. 11 -----
    @property
    def vdr(self) -> float:
        return self.vd / self.vt if self.vt else 0.0

    @property
    def rsr(self) -> float:
        return self.rs / self.rt if self.rt else 0.0

    # ----- Eq. 12 -----
    @property
    def coverage(self) -> float:
        return self.pc / self.pt if self.pt else 0.0

    # ----- Eq. 15 -----
    @property
    def cpe(self) -> float:
        return self.ep / self.tp_repair if self.tp_repair else 0.0

    # ----- Eqs. 16–19 -----
    @property
    def accuracy(self) -> float:
        denom = self.tp + self.tn + self.fp + self.fn
        return (self.tp + self.tn) / denom if denom else 0.0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def mcc(self) -> float:
        num = (self.tp * self.tn) - (self.fp * self.fn)
        denom2 = (
            (self.tp + self.fp)
            * (self.tp + self.fn)
            * (self.tn + self.fp)
            * (self.tn + self.fn)
        )
        return num / math.sqrt(denom2) if denom2 > 0 else 0.0

    # ----- presentation helpers -----
    def to_dict(self) -> Dict[str, float]:
        return {
            "VDR": self.vdr,
            "RSR": self.rsr,
            "Coverage": self.coverage,
            "CPE": self.cpe,
            "Accuracy": self.accuracy,
            "Precision": self.precision,
            "Recall": self.recall,
            "F1": self.f1,
            "MCC": self.mcc,
        }

    def update(self, **counts) -> "CapabilityMetrics":
        for k, v in counts.items():
            if hasattr(self, k):
                setattr(self, k, getattr(self, k) + int(v))
        return self


def bootstrap_ci(
    values: Sequence[float],
    n_resamples: int = 10_000,
    alpha: float = 0.05,
    seed: int = 20250901,
) -> tuple[float, float]:
    """Bootstrap percentile CI used for the 95% bands in Tables III–VI."""
    import numpy as np
    rng = np.random.default_rng(seed)
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return (0.0, 0.0)
    idx = rng.integers(0, arr.size, size=(n_resamples, arr.size))
    samples = arr[idx].mean(axis=1)
    lo, hi = np.percentile(samples, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)

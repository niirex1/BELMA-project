"""Pareto-based cost-benefit optimization — Algorithm 4 of the paper.

For a set of candidate repairs CR, evaluate each on (accuracy, reliability,
computational cost), construct an evaluation matrix EM, then extract the
non-dominated front NDS = Pareto(EM). The application-specific filter
F(NDS, RiskProfile) returns the optimized solution set OSS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RepairScore:
    accuracy: float        # detection accuracy after applying this repair (0..1)
    reliability: float     # repair reliability / RSR-like (0..1)
    cost: float            # computational cost (lower is better; e.g., ms)


@dataclass
class CandidateRepair:
    """A candidate repair with its evaluation scores."""
    id: str
    score: RepairScore
    description: str = ""


def is_dominated(a: RepairScore, b: RepairScore) -> bool:
    """`a` is dominated by `b` iff b is no worse on all axes and strictly
    better on at least one."""
    if (b.accuracy >= a.accuracy and b.reliability >= a.reliability and b.cost <= a.cost):
        if (b.accuracy > a.accuracy or b.reliability > a.reliability or b.cost < a.cost):
            return True
    return False


@dataclass
class ParetoOptimizer:
    """Algorithm 4: Pareto-Based Cost-Benefit Optimization."""

    @staticmethod
    def evaluation_matrix(candidates: List[CandidateRepair]) -> List[RepairScore]:
        return [c.score for c in candidates]

    @staticmethod
    def pareto_front(candidates: List[CandidateRepair]) -> List[CandidateRepair]:
        """Return the non-dominated subset NDS."""
        result: List[CandidateRepair] = []
        for i, ci in enumerate(candidates):
            dominated = False
            for j, cj in enumerate(candidates):
                if i == j:
                    continue
                if is_dominated(ci.score, cj.score):
                    dominated = True
                    break
            if not dominated:
                result.append(ci)
        return result

    @staticmethod
    def filter_by_risk(
        nds: List[CandidateRepair],
        alpha: float,
        beta: float,
        gamma: float,
        top_k: Optional[int] = None,
    ) -> List[CandidateRepair]:
        """Apply scalarized risk weights and rank.

        For audit-scale deployments raise gamma; for high-stakes financial
        contracts raise beta (penalize false negatives).
        """
        def cost(c: CandidateRepair) -> float:
            s = c.score
            # Risk-cost model (Algorithm 4):
            #   alpha = FP cost  → penalize unreliable patches (false alarms)
            #   beta  = FN cost  → penalize inaccurate patches  (missed bugs)
            #   gamma = ops cost → penalize runtime / resource use
            return alpha * (1 - s.reliability) + beta * (1 - s.accuracy) + gamma * s.cost

        ranked = sorted(nds, key=cost)
        return ranked[:top_k] if top_k else ranked

    def optimize(
        self,
        candidates: List[CandidateRepair],
        alpha: float = 1.0,
        beta: float = 1.0,
        gamma: float = 0.5,
        top_k: Optional[int] = None,
    ) -> List[CandidateRepair]:
        """Algorithm 4 end-to-end."""
        nds = self.pareto_front(candidates)
        return self.filter_by_risk(nds, alpha, beta, gamma, top_k)

"""Tests for the Pareto cost-benefit optimizer (Algorithm 4)."""
from __future__ import annotations

from belma.optimization.pareto_optimizer import (
    CandidateRepair, ParetoOptimizer, RepairScore, is_dominated,
)


def _c(id_, acc, rel, cost):
    return CandidateRepair(id=id_, score=RepairScore(acc, rel, cost))


def test_dominance_detection():
    a = RepairScore(0.9, 0.9, 100)
    b = RepairScore(0.95, 0.95, 80)   # b dominates a on all axes
    assert is_dominated(a, b)
    assert not is_dominated(b, a)


def test_pareto_front_excludes_dominated():
    cands = [
        _c("a", 0.90, 0.90, 100),
        _c("b", 0.95, 0.95,  80),     # dominates a
        _c("c", 0.85, 0.99,  60),     # not dominated by b (better recall, cheaper)
    ]
    nds = ParetoOptimizer.pareto_front(cands)
    ids = {c.id for c in nds}
    assert "b" in ids and "c" in ids
    assert "a" not in ids


def test_filter_by_risk_orders_by_weights():
    cands = [
        _c("low_acc",  0.80, 0.95, 50),
        _c("high_acc", 0.99, 0.95, 90),
    ]
    # heavy beta (FN penalty) should prefer high accuracy / high reliability
    out = ParetoOptimizer().optimize(cands, alpha=0.1, beta=2.0, gamma=0.001)
    assert out[0].id == "high_acc"

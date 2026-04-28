"""Cost-benefit optimization (Section IV.D, Algorithm 4).

Pareto-based optimization that balances false positives, false negatives, and
runtime overhead:

    Minimize  C = alpha * FP + beta * FN + gamma * R

with weights tunable per deployment context (e.g., financial-contract auditing
prioritises low FN; high-throughput audit pipelines prioritise low R).
"""
from belma.optimization.pareto_optimizer import (
    ParetoOptimizer, CandidateRepair, RepairScore,
)
from belma.optimization.cost_benefit import CostBenefit

__all__ = ["ParetoOptimizer", "CandidateRepair", "RepairScore", "CostBenefit"]

"""Cost-benefit objective from Eq. (3) of the paper:

        C = alpha * FP + beta * FN + gamma * R

where FP, FN are false detections and R is computational repair cost. The
weights (alpha, beta, gamma) are configured in `belma_config.yaml` and
documented in Section IV.D.
"""
from __future__ import annotations

from dataclasses import dataclass

from belma.config import Config, load_config


@dataclass
class CostBenefit:
    alpha: float = 1.0   # FP weight
    beta: float = 1.0    # FN weight
    gamma: float = 0.5   # runtime weight

    @classmethod
    def from_config(cls, config: Config | None = None) -> "CostBenefit":
        cfg = config or load_config()
        a, b, g = cfg.cost_benefit_weights()
        return cls(alpha=a, beta=b, gamma=g)

    def cost(self, fp: float, fn: float, runtime: float) -> float:
        return self.alpha * fp + self.beta * fn + self.gamma * runtime

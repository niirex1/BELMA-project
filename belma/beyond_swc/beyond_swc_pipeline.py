"""Beyond-SWC pipeline orchestrator (advisory mode only).

Used in two contexts:
  (a) standalone screening of a contract that the SWC-based detection
      layer cleared (no SWC violations) — does it nevertheless look OOD?
  (b) post-detection routing: any vulnerability whose `swc` is None is
      passed through this pipeline rather than the auto-repair loop.

The output is a list of `Hypothesis` objects for human review. BELMA does
NOT auto-patch contracts in this pipeline.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from belma.beyond_swc.anomaly_screen import (
    AnomalyVerdict, MahalanobisAnomalyScreen,
)
from belma.beyond_swc.hypothesis_generator import (
    Hypothesis, HypothesisGenerator,
)
from belma.config import Config, load_config
from belma.types import Contract

log = logging.getLogger(__name__)


@dataclass
class BeyondSwcReport:
    contract_name: str
    verdict: AnomalyVerdict
    hypothesis: Optional[Hypothesis] = None
    flagged_for_human_review: bool = False
    notes: List[str] = field(default_factory=list)


class BeyondSwcPipeline:
    """Two-stage pipeline: anomaly screen (Stage 1) → hypothesis gen (Stage 2)."""

    def __init__(
        self,
        screen: Optional[MahalanobisAnomalyScreen] = None,
        generator: Optional[HypothesisGenerator] = None,
        config: Optional[Config] = None,
    ):
        cfg = config or load_config()
        self.enabled = cfg.beyond_swc_enabled()
        self.screen = screen or MahalanobisAnomalyScreen(
            percentile=float(cfg.raw["beyond_swc"]["mahalanobis_percentile"])
        )
        self.generator = generator or HypothesisGenerator(
            fewshot=None,                 # default 8 examples kick in
        )

    def run(self, contract: Contract) -> BeyondSwcReport:
        if not self.enabled:
            return BeyondSwcReport(
                contract_name=contract.name,
                verdict=AnomalyVerdict(False, 0.0, 0.0, 0.0),
                flagged_for_human_review=False,
                notes=["Beyond-SWC pipeline disabled in config."],
            )

        # ---- Stage 1: anomaly screen ----
        try:
            verdict = self.screen.screen(contract.source)
        except RuntimeError:
            # screen has not been fit; this is a soft failure — just don't flag
            log.warning("AnomalyScreen not fit; skipping Beyond-SWC for %s",
                        contract.name)
            return BeyondSwcReport(
                contract_name=contract.name,
                verdict=AnomalyVerdict(False, 0.0, 0.0, 0.0),
                flagged_for_human_review=False,
                notes=["Anomaly screen not calibrated; install reference corpus."],
            )

        if not verdict.is_anomalous:
            return BeyondSwcReport(
                contract_name=contract.name,
                verdict=verdict,
                flagged_for_human_review=False,
                notes=["In-distribution; no Beyond-SWC concern."],
            )

        # ---- Stage 2: hypothesis generation ----
        hypothesis = self.generator.generate(contract)
        return BeyondSwcReport(
            contract_name=contract.name,
            verdict=verdict,
            hypothesis=hypothesis,
            flagged_for_human_review=True,
            notes=[
                f"Stage 1 distance {verdict.distance:.2f} > "
                f"threshold {verdict.threshold:.2f}",
                f"Suspected class: {hypothesis.suspected_class}",
                "Flagged for human review; auto-repair NOT applied.",
            ],
        )

"""Repair pipeline orchestrator — Layer 2 end-to-end (Section IV.B).

Couples LLM patch generation, the BiasScore/ErrorScore refinement loop, and
the bounded symbolic re-validator. Per-vulnerability latency decomposition
(R1-C3) is preserved on each `Patch` instance.
"""
from __future__ import annotations

import logging
import time
from typing import Iterable, List, Optional

from belma.config import Config, load_config
from belma.repair.bias_score import BiasScore
from belma.repair.error_score import ErrorScore
from belma.repair.llm_patcher import LLMPatcher
from belma.repair.patch_validator import BoundedValidator
from belma.repair.refinement_loop import RefinementLoop
from belma.types import (
    Contract, Patch, RepairResult, StructuredContext,
)

log = logging.getLogger(__name__)


class RepairPipeline:
    """End-to-end repair layer."""

    def __init__(
        self,
        config: Optional[Config] = None,
        bias: Optional[BiasScore] = None,
        error: Optional[ErrorScore] = None,
        patcher: Optional[LLMPatcher] = None,
        validator: Optional[BoundedValidator] = None,
    ):
        cfg = config or load_config()
        self.config = cfg
        self.bias = bias or BiasScore(config=cfg)
        self.error = error or ErrorScore(config=cfg)
        self.patcher = patcher or LLMPatcher(config=cfg)
        self.validator = validator or BoundedValidator(config=cfg)
        self.loop = RefinementLoop(
            bias_score=self.bias,
            error_score=self.error,
            patcher=self.patcher,
            config=cfg,
            validator=self.validator,
        )

    def repair(self, contexts: Iterable[StructuredContext]) -> RepairResult:
        contexts = list(contexts)
        if not contexts:
            return RepairResult(
                contract=Contract(name="<empty>", source="", platform=None),
                patches=[], runtime_ms=0.0, rsr=0.0,
            )

        contract = contexts[0].contract
        t0 = time.perf_counter()
        patches: List[Patch] = []
        accepted = 0
        flagged = 0

        for ctx in contexts:
            res = self.loop.refine(ctx)
            patches.append(res.patch)
            if res.converged:
                accepted += 1
            elif res.flagged_for_human_review:
                flagged += 1

        # per the policy in belma_config.yaml, flagged-for-review patches are
        # excluded from the auto-repair RSR statistics (§VI.A footnote)
        attempted_auto = max(1, len(patches) - flagged)
        rsr = accepted / attempted_auto

        repaired = self._compose(contract, patches)
        return RepairResult(
            contract=contract,
            patches=patches,
            repaired_source=repaired,
            runtime_ms=(time.perf_counter() - t0) * 1000.0,
            rsr=rsr,
        )

    @staticmethod
    def _compose(contract: Contract, patches: List[Patch]) -> str:
        """Compose accepted patches into a single repaired source.

        The naive policy is to take the latest patched_source from any
        accepted patch; conflict resolution between overlapping patches is
        delegated to a future merge module (see §IX.B refinements).
        """
        accepted_patches = [p for p in patches if p.accepted]
        if not accepted_patches:
            return contract.source
        return accepted_patches[-1].patched_source

"""Refinement loop — Algorithm 2 of the paper.

This module implements the closed-loop refinement that drives candidate patches
toward acceptance. It also produces the per-stage latency decomposition
required by Reviewer 1, Comment 3 (R1-C3):

    T_repair^(v) = T_gen^(v) + Σ T_ref^(v,i) + T_val^(v)

with means and 95% CIs reported in §V.E paragraph (f).

The abstract's "8 ms validation latency" refers to T_val (the bounded symbolic
re-check stage) — NOT the full per-vulnerability repair time, which is the
180–280 ms band reported in Fig. 4.
"""
from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

from belma.config import Config, load_config
from belma.repair.bias_score import BiasScore
from belma.repair.error_score import ErrorScore
from belma.repair.llm_patcher import LLMPatcher
from belma.types import Contract, Patch, StructuredContext

log = logging.getLogger(__name__)


@dataclass
class IterationTrace:
    """Per-iteration record. Used by experiments/bias_error_sensitivity.py."""
    iteration: int
    bias: float
    error: float
    accepted: bool
    duration_ms: float


@dataclass
class RefinementResult:
    patch: Patch
    iterations: List[IterationTrace] = field(default_factory=list)
    converged: bool = False
    flagged_for_human_review: bool = False


class RefinementLoop:
    """Algorithm 2: refine T' until B <= tau_B and E <= tau_E, or k_max iterations.

    On non-convergence the patch is FLAGGED for human review (per the
    `on_non_convergence: human_review` policy in `belma_config.yaml`). It is
    NOT auto-accepted, and is excluded from RSR statistics in §VI.A.
    """

    def __init__(
        self,
        bias_score: Optional[BiasScore] = None,
        error_score: Optional[ErrorScore] = None,
        patcher: Optional[LLMPatcher] = None,
        config: Optional[Config] = None,
        validator: Optional["BoundedValidator"] = None,   # forward-declared
    ):
        cfg = config or load_config()
        self.k_max = cfg.k_max()
        self.bias = bias_score or BiasScore(config=cfg)
        self.error = error_score or ErrorScore(config=cfg)
        self.patcher = patcher or LLMPatcher(config=cfg)
        self.validator = validator       # set later by RepairPipeline

    def refine(self, context: StructuredContext) -> RefinementResult:
        """Iteratively refine until acceptance or k_max."""
        traces: List[IterationTrace] = []
        feedback: Optional[str] = None

        # ---- Stage 1: initial generation (T_gen) ----
        t_gen_start = time.perf_counter()
        gen = self.patcher.generate(context, feedback=None)
        t_gen_ms = (time.perf_counter() - t_gen_start) * 1000.0

        candidate_source = gen.patched_source
        candidate_contract = self._make_patched_contract(context.contract, candidate_source)
        swc_label = context.vulnerability.swc.value if context.vulnerability.swc else None

        # ---- Stage 2: refinement iterations (T_ref) ----
        t_ref_total_ms = 0.0
        accepted = False
        for i in range(self.k_max):
            iter_start = time.perf_counter()

            b_components = self.bias.compute(candidate_source, swc_label)
            e_components = self.error.compute(candidate_contract)
            b = b_components.weighted_total
            e = e_components.weighted_total

            iter_ms = (time.perf_counter() - iter_start) * 1000.0
            t_ref_total_ms += iter_ms

            log.debug(
                "Refinement iter %d: B=%.3f (tau=%.3f), E=%.3f (tau=%.3f)",
                i, b, self.bias.threshold, e, self.error.threshold,
            )

            if b <= self.bias.threshold and e <= self.error.threshold:
                accepted = True
                traces.append(IterationTrace(
                    iteration=i, bias=b, error=e,
                    accepted=True, duration_ms=iter_ms,
                ))
                break

            traces.append(IterationTrace(
                iteration=i, bias=b, error=e,
                accepted=False, duration_ms=iter_ms,
            ))

            # build feedback for the next LLM call
            feedback = self._build_feedback(b_components, e_components)
            ref_call = self.patcher.generate(context, feedback=feedback)
            candidate_source = ref_call.patched_source
            candidate_contract = self._make_patched_contract(
                context.contract, candidate_source
            )

        # ---- Stage 3: bounded symbolic re-check (T_val) ----
        t_val_ms = 0.0
        if accepted and self.validator is not None:
            t_val_start = time.perf_counter()
            accepted = self.validator.validate(candidate_contract, context.vulnerability)
            t_val_ms = (time.perf_counter() - t_val_start) * 1000.0

        flagged = (not accepted) and len(traces) >= self.k_max

        patch = Patch(
            vulnerability=context.vulnerability,
            patched_source=candidate_source,
            diff=_unified_diff(context.contract.source, candidate_source),
            bias_score=traces[-1].bias if traces else float("inf"),
            error_score=traces[-1].error if traces else float("inf"),
            iterations=len(traces),
            accepted=accepted,
            rejection_reason=None if accepted else "k_max exceeded; flagged for review",
            t_gen_ms=t_gen_ms,
            t_ref_ms=t_ref_total_ms,
            t_val_ms=t_val_ms,
        )

        return RefinementResult(
            patch=patch,
            iterations=traces,
            converged=accepted,
            flagged_for_human_review=flagged,
        )

    # ---- helpers ----
    @staticmethod
    def _make_patched_contract(original: Contract, new_source: str) -> Contract:
        patched = copy.copy(original)
        patched.source = new_source
        return patched

    @staticmethod
    def _build_feedback(b_components, e_components) -> str:
        bits = []
        if b_components.cosine_distance > 0.3:
            bits.append("Patch deviates from secure-patch distribution; "
                        "align more closely with checks-effects-interactions idioms.")
        if b_components.perplexity > 0.6:
            bits.append("Generated tokens have unusually high perplexity; "
                        "prefer canonical Solidity constructs.")
        if b_components.ast_dissimilarity > 0.4:
            bits.append("Patch structure differs from nearest SWC template; "
                        "consider matching the template's control-flow shape.")
        if e_components.e_compile > 0:
            bits.append("Patch fails to compile; fix syntax before resubmission.")
        if e_components.e_assert > 0:
            bits.append(f"{e_components.e_assert*100:.0f}% of SWC assertions still violated.")
        if e_components.e_regress > 0:
            bits.append(f"{e_components.e_regress*100:.0f}% of unit tests fail.")
        return "\n".join(f"- {b}" for b in bits) or "- Refine patch quality."


def _unified_diff(a: str, b: str) -> str:
    import difflib
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile="original", tofile="patched", n=2,
        )
    )

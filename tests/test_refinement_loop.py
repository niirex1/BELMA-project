"""Tests for the refinement loop (Algorithm 2) and human-review fallback."""
from __future__ import annotations

import pytest

from belma.repair.refinement_loop import RefinementLoop
from belma.repair.bias_score import BiasScore
from belma.repair.error_score import ErrorScore
from belma.repair.llm_patcher import LLMPatcher
from belma.types import (
    Contract, Platform, StructuredContext, SWC, Vulnerability,
)


def _ctx() -> StructuredContext:
    c = Contract(name="T", source="contract T {}", platform=Platform.ETHEREUM, loc=1)
    v = Vulnerability(
        swc=SWC.REENTRANCY, location=(1, 1), function_name="f",
        description="x", severity="high", confidence=0.9,
    )
    return StructuredContext(
        contract=c, vulnerability=v,
        ast_node={}, enclosing_function="f",
        state_variables=[], call_targets=[],
    )


def test_refinement_terminates_at_k_max_and_flags_for_review():
    """Per the policy in belma_config.yaml, non-converging patches are NOT
    auto-accepted. They are flagged for human review."""
    bias = BiasScore(); bias.threshold = -1.0   # never passes
    error = ErrorScore(); error.threshold = -1.0  # never passes
    loop = RefinementLoop(
        bias_score=bias, error_score=error, patcher=LLMPatcher(),
    )
    res = loop.refine(_ctx())
    assert res.flagged_for_human_review
    assert not res.converged
    assert res.patch.iterations == loop.k_max


def test_refinement_records_per_stage_latency():
    """Latency decomposition (R1-C3) requires t_gen, t_ref, t_val on each Patch."""
    loop = RefinementLoop()
    res = loop.refine(_ctx())
    p = res.patch
    assert p.t_gen_ms >= 0.0
    assert p.t_ref_ms >= 0.0
    assert p.t_val_ms >= 0.0


def test_iteration_count_capped_at_k_max():
    bias = BiasScore(); bias.threshold = -1.0
    error = ErrorScore(); error.threshold = -1.0
    loop = RefinementLoop(bias_score=bias, error_score=error)
    res = loop.refine(_ctx())
    assert res.patch.iterations <= loop.k_max

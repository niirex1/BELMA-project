"""Beyond-SWC advisory pipeline (Reviewer 2, Weakness 2).

Vulnerabilities outside the SWC catalog — flash-loan price manipulation,
read-only reentrancy, governance attacks via flash-loan voting power, MEV
sandwiching, oracle manipulation, cross-chain bridge replay, storage
collision in proxy patterns, and donation attacks on yield vaults — are
handled by a TWO-STAGE ADVISORY pipeline. BELMA never auto-patches these.

    Stage 1 (anomaly screen):
        compute the contract embedding phi(C) and compare against
        mu_secure via Mahalanobis distance over the BERT feature space.
        Flag if d_M(phi(C), mu_secure) > delta, with delta set to the
        95th percentile of in-distribution distances on the validation
        split (target FPR ~5% on benign contracts).

    Stage 2 (LLM-guided hypothesis generation):
        flagged contracts are passed to the repair LLM with a few-shot
        prompt comprising eight curated post-2023 exploit examples. The
        LLM produces a natural-language hypothesis and, where the
        property is formalizable, a candidate Hoare-style assertion.
        The contract is surfaced for HUMAN REVIEW, never auto-patched.

Empirical evaluation: §VI.G of the manuscript, 50-contract corpus from
Rekt News / Immunefi / BlockSec post-mortems.
"""
from belma.beyond_swc.anomaly_screen import MahalanobisAnomalyScreen
from belma.beyond_swc.hypothesis_generator import HypothesisGenerator
from belma.beyond_swc.beyond_swc_pipeline import BeyondSwcPipeline

__all__ = [
    "MahalanobisAnomalyScreen",
    "HypothesisGenerator",
    "BeyondSwcPipeline",
]

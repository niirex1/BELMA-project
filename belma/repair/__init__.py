"""Layer 2: Automated Vulnerability Repair.

Algorithm 2 of the paper. For each `StructuredContext` produced by Layer 1:

    1) extract context C around the vulnerability site
    2) convert C to a structured form T'
    3) compute B = BiasScore(T')   and   E = ErrorScore(T')
    4) while B > tau_B  OR  E > tau_E  (and iterations < k_max):
           refine T' under B and E guidance
           recompute B and E
    5) generate patch P from refined T'
    6) bounded symbolic re-verification of P (Section IV.B.3, k-bounded soundness)
    7) accept if and only if all SWC-derived assertions hold within k

Operational definitions of B and E are in `bias_score.py` / `error_score.py`,
calibrated as described in `experiments/bias_error_sensitivity.py` (R1-C4).
"""
from belma.repair.bias_score import BiasScore
from belma.repair.error_score import ErrorScore
from belma.repair.llm_patcher import LLMPatcher
from belma.repair.patch_validator import BoundedValidator
from belma.repair.refinement_loop import RefinementLoop
from belma.repair.repair_pipeline import RepairPipeline

__all__ = [
    "BiasScore",
    "ErrorScore",
    "LLMPatcher",
    "BoundedValidator",
    "RefinementLoop",
    "RepairPipeline",
]

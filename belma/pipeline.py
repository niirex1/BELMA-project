"""BELMA top-level pipeline (Algorithm 3, Section IV.C).

The dual-layer repair–validation cycle:

    Run DA on S to produce vulnerability context VC
    if VC ≠ ∅:
        Generate candidate patch VC' using RA(VC)
        Apply VC' to obtain repaired contract S'
        Re-run DA on S' to validate
        Update CR with validation outcome
    else:
        CR ← "No vulnerabilities detected"
    return CR

Plus the Beyond-SWC advisory pipeline (R2-W2) for non-SWC vulnerabilities and
the cost–benefit / DHT layer for resource-aware execution at scale.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from belma.beyond_swc.beyond_swc_pipeline import (
    BeyondSwcPipeline, BeyondSwcReport,
)
from belma.config import Config, load_config
from belma.detection.detection_pipeline import DetectionPipeline
from belma.infrastructure.batch_processor import BatchProcessor
from belma.infrastructure.cache import AnalysisCache
from belma.infrastructure.dht_balancer import DHTLoadBalancer
from belma.metrics.capability import CapabilityMetrics
from belma.metrics.infrastructure import InfrastructureMetrics
from belma.metrics.latency_decomposition import LatencyDecomposition
from belma.platforms import adapter_for
from belma.repair.repair_pipeline import RepairPipeline
from belma.types import (
    Contract, DetectionResult, Patch, Platform, RepairResult,
)

log = logging.getLogger("belma.pipeline")


@dataclass
class BelmaResult:
    contract_name: str
    detection: DetectionResult
    repair: RepairResult
    beyond_swc: Optional[BeyondSwcReport] = None
    capability: dict = field(default_factory=dict)
    infrastructure: dict = field(default_factory=dict)
    latency: dict = field(default_factory=dict)


class BELMA:
    """Top-level dual-layer pipeline (Algorithm 3 of the paper)."""

    def __init__(
        self,
        config: Optional[Config] = None,
        detection: Optional[DetectionPipeline] = None,
        repair: Optional[RepairPipeline] = None,
        beyond_swc: Optional[BeyondSwcPipeline] = None,
        cache: Optional[AnalysisCache] = None,
        balancer: Optional[DHTLoadBalancer] = None,
        batch: Optional[BatchProcessor] = None,
    ):
        self.config = config or load_config()
        self.detection = detection or DetectionPipeline(self.config)
        self.repair = repair or RepairPipeline(self.config)
        self.beyond_swc = beyond_swc or BeyondSwcPipeline(config=self.config)
        self.cache = cache or AnalysisCache(
            max_entries=int(self.config.raw["infrastructure"]["cache"]["max_entries"]),
            ttl_seconds=int(self.config.raw["infrastructure"]["cache"]["ttl_seconds"]),
            enabled=bool(self.config.raw["infrastructure"]["cache"]["enabled"]),
        )
        self.balancer = balancer or DHTLoadBalancer(
            enabled=bool(self.config.raw["infrastructure"]["dht"]["enabled"]),
        )
        self.batch = batch or BatchProcessor(
            max_batch_size=int(self.config.raw["infrastructure"]["batch"]["max_batch_size"]),
            enabled=bool(self.config.raw["infrastructure"]["batch"]["enabled"]),
        )

    # ------------------------------------------------------------------
    # single-contract entry point
    # ------------------------------------------------------------------
    def analyze_and_repair(self, contract: Contract) -> BelmaResult:
        # cache hit?
        cached = self.cache.get(contract.source)
        if cached is not None:
            log.debug("Cache hit for %s", contract.name)
            return cached

        # Algorithm 3, line 1: run DA
        det = self.detection.analyze(contract)

        # Algorithm 3, lines 2–6: if VC ≠ ∅ generate, apply, re-validate
        if det.vulnerabilities:
            contexts = list(self.detection.to_contexts(det))
            rep = self.repair.repair(contexts)
        else:
            rep = RepairResult(
                contract=contract, patches=[], runtime_ms=0.0, rsr=0.0,
            )

        # Beyond-SWC advisory pipeline (R2-W2). Triggers when:
        #  (a) SWC detection cleared the contract (rep.patches empty), OR
        #  (b) any vulnerability lacks an SWC label (non-SWC class).
        beyond = None
        non_swc = any(v.is_beyond_swc for v in det.vulnerabilities)
        if not det.vulnerabilities or non_swc:
            beyond = self.beyond_swc.run(contract)

        # capability + infrastructure metrics
        cap = self._capability_from_run(det, rep)
        infra = self._infrastructure_from_run(det, rep)
        latency = self._latency_from_patches(rep.patches)

        result = BelmaResult(
            contract_name=contract.name,
            detection=det,
            repair=rep,
            beyond_swc=beyond,
            capability=cap.to_dict(),
            infrastructure=infra.to_dict(),
            latency=latency,
        )
        self.cache.put(contract.source, result)
        return result

    # ------------------------------------------------------------------
    # batch entry point — used for §VI.A reproducibility
    # ------------------------------------------------------------------
    def analyze_batch(self, contracts: List[Contract]) -> List[BelmaResult]:
        # pretend-distribute to expose the DHT layer
        self.balancer.assign_batch([c.name for c in contracts])
        return self.batch.process(contracts, self.analyze_and_repair)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    @staticmethod
    def _capability_from_run(
        det: DetectionResult, rep: RepairResult,
    ) -> CapabilityMetrics:
        accepted = sum(1 for p in rep.patches if p.accepted)
        attempted = sum(
            1 for p in rep.patches
            if not (p.rejection_reason and "flagged for review" in p.rejection_reason)
        )
        return CapabilityMetrics(
            vd=len(det.vulnerabilities),
            vt=max(len(det.vulnerabilities), 1),  # local: vulns considered the population
            rs=accepted,
            rt=max(attempted, 1),
            pc=int(det.coverage * 100),
            pt=100,
            ep=accepted,
            tp_repair=max(len(rep.patches), 1),
            tp=accepted,
            fp=0, tn=0, fn=0,
        )

    @staticmethod
    def _infrastructure_from_run(
        det: DetectionResult, rep: RepairResult,
    ) -> InfrastructureMetrics:
        return InfrastructureMetrics(
            t_dual=det.runtime_ms + rep.runtime_ms,
            t_single=det.runtime_ms,
            response_times_ms=[p.t_gen_ms + p.t_ref_ms + p.t_val_ms for p in rep.patches],
            nt=max(len(rep.patches), 1),
            t_window=max(0.001, (det.runtime_ms + rep.runtime_ms) / 1000.0),
        )

    @staticmethod
    def _latency_from_patches(patches: List[Patch]) -> dict:
        ld = LatencyDecomposition()
        for p in patches:
            ld.record(p)
        return ld.summary()


# ----------------------------------------------------------------------
# I/O helpers
# ----------------------------------------------------------------------
def load_contract(path: str | Path, platform: str) -> Contract:
    p = Path(path)
    source = p.read_text(encoding="utf-8")
    plat = Platform(platform.lower())
    return Contract(
        name=p.stem,
        source=source,
        platform=plat,
        loc=len(source.splitlines()),
    )


def _result_to_dict(r: BelmaResult) -> dict:
    return {
        "contract": r.contract_name,
        "detection": {
            "vulnerabilities": [
                {
                    "swc": v.swc.value if v.swc else None,
                    "function": v.function_name,
                    "line": v.location[0],
                    "severity": v.severity,
                    "confidence": v.confidence,
                }
                for v in r.detection.vulnerabilities
            ],
            "coverage": r.detection.coverage,
            "runtime_ms": r.detection.runtime_ms,
            "k_bound": r.detection.k_bound_used,
            "timed_out": r.detection.timed_out,
        },
        "repair": {
            "patches": [
                {
                    "swc": (p.vulnerability.swc.value if p.vulnerability.swc else None),
                    "accepted": p.accepted,
                    "iterations": p.iterations,
                    "bias": p.bias_score,
                    "error": p.error_score,
                    "t_gen_ms": p.t_gen_ms,
                    "t_ref_ms": p.t_ref_ms,
                    "t_val_ms": p.t_val_ms,
                    "rejection_reason": p.rejection_reason,
                }
                for p in r.repair.patches
            ],
            "rsr": r.repair.rsr,
            "runtime_ms": r.repair.runtime_ms,
        },
        "beyond_swc": (
            {
                "is_anomalous": r.beyond_swc.verdict.is_anomalous,
                "distance": r.beyond_swc.verdict.distance,
                "threshold": r.beyond_swc.verdict.threshold,
                "flagged_for_human_review": r.beyond_swc.flagged_for_human_review,
                "hypothesis": (
                    r.beyond_swc.hypothesis.natural_language
                    if r.beyond_swc.hypothesis else None
                ),
                "suspected_class": (
                    r.beyond_swc.hypothesis.suspected_class
                    if r.beyond_swc.hypothesis else None
                ),
            }
            if r.beyond_swc else None
        ),
        "capability": r.capability,
        "infrastructure": r.infrastructure,
        "latency": r.latency,
    }


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def cli() -> int:
    parser = argparse.ArgumentParser(
        prog="belma",
        description="BELMA dual-layer smart-contract analyzer and repairer",
    )
    parser.add_argument("--contract", required=True, help="Path to contract source")
    parser.add_argument(
        "--platform", default="ethereum",
        choices=["ethereum", "fabric", "eos"],
        help="Target blockchain platform",
    )
    parser.add_argument("--config", default=None, help="Path to belma_config.yaml")
    parser.add_argument("--output", default=None, help="Write result JSON to this path")
    parser.add_argument("--verbose", "-v", action="count", default=0)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING - 10 * min(args.verbose, 2),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = load_config(args.config) if args.config else load_config()
    contract = load_contract(args.contract, args.platform)
    pipeline = BELMA(config=cfg)
    result = pipeline.analyze_and_repair(contract)

    payload = _result_to_dict(result)
    text = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(cli())

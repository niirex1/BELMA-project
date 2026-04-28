"""Detection pipeline orchestrator (Section IV.A end-to-end).

Wires Word2Vec preprocessing → bounded symbolic execution → static rules →
vulnerability classification, returning a `DetectionResult` plus an enumerable
sequence of `StructuredContext` objects to feed the repair layer.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from belma.config import Config, load_config
from belma.detection.symbolic_executor import (
    SymbolicExecutor, default_properties,
)
from belma.detection.static_analyzer import RuleBasedDetector
from belma.detection.vulnerability_classifier import (
    FusionWeights, VulnerabilityClassifier,
)
from belma.detection.word2vec_preprocessor import Word2VecPreprocessor
from belma.types import (
    Contract, DetectionResult, StructuredContext, Vulnerability,
)

log = logging.getLogger(__name__)


class DetectionPipeline:
    """End-to-end detection layer."""

    def __init__(
        self,
        config: Optional[Config] = None,
        embed: Optional[Word2VecPreprocessor] = None,
        symbolic: Optional[SymbolicExecutor] = None,
        rule_based: Optional[RuleBasedDetector] = None,
        classifier: Optional[VulnerabilityClassifier] = None,
    ):
        self.config = config or load_config()
        self.embed = embed or Word2VecPreprocessor()
        self.symbolic = symbolic or SymbolicExecutor(
            k_bound=self.config.symbolic_k(),
            smt_timeout_s=self.config.smt_timeout(),
        )
        self.rule_based = rule_based or RuleBasedDetector()
        self.classifier = classifier or VulnerabilityClassifier(FusionWeights())

    def analyze(self, contract: Contract) -> DetectionResult:
        """Run the full detection layer on a single contract."""
        t0 = time.perf_counter()

        # 1) symbolic exploration
        symbolic_result = self.symbolic.verify(contract, default_properties())
        # 2) static rules
        static_vulns = self.rule_based.scan(contract)
        # 3) classifier fusion
        fused = self.classifier.classify(
            contract,
            symbolic_vulns=symbolic_result.vulnerabilities,
            static_vulns=static_vulns,
            embedding_signal=None,        # plug in later
        )

        result = DetectionResult(
            contract=contract,
            vulnerabilities=fused,
            coverage=symbolic_result.coverage,
            runtime_ms=(time.perf_counter() - t0) * 1000.0,
            k_bound_used=symbolic_result.k_bound_used,
            timed_out=symbolic_result.timed_out,
        )
        log.info(
            "Detection on %s: %d vulnerabilities, coverage=%.2f, %.1f ms",
            contract.name, len(fused), result.coverage, result.runtime_ms,
        )
        return result

    def to_contexts(self, result: DetectionResult) -> Iterator[StructuredContext]:
        """Yield a `StructuredContext` per vulnerability for the repair layer."""
        for v in result.vulnerabilities:
            yield StructuredContext(
                contract=result.contract,
                vulnerability=v,
                ast_node={"function": v.function_name, "line": v.location[0]},
                enclosing_function=v.function_name,
                state_variables=[],
                call_targets=[],
                bytecode_slice=None,
            )

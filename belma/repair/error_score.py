"""ErrorScore — operational definition (R1-C4).

Manuscript §IV.B.1, Eq. (1):

    E(T') = a1 * e_compile(T') + a2 * e_assert(T') + a3 * e_regress(T')

where:
    e_compile  in {0, 1}        : 1 if solc / protoc / eosio-cpp fails
    e_assert   in [0, 1]        : fraction of SWC-derived bounded assertions
                                  still violated by T' under symbolic re-execution
                                  at depth k
    e_regress  in [0, 1]        : fraction of pre-existing functional unit
                                  tests that fail on the patched contract
                                  (0 if no unit tests are available)

Default weights (grid search on validation split):
    (a1, a2, a3) = (0.5, 0.4, 0.1)
Default acceptance threshold:
    tau_E = 0.05
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import Callable, List, Optional

from belma.config import Config, load_config
from belma.types import Contract, Platform

log = logging.getLogger(__name__)


@dataclass
class ErrorScoreComponents:
    e_compile: float
    e_assert: float
    e_regress: float
    weighted_total: float


class ErrorScore:
    """Compute E(T') for a candidate patch."""

    def __init__(
        self,
        compile_fn: Optional[Callable[[Contract], bool]] = None,
        assertion_check_fn: Optional[Callable[[Contract, List[str]], float]] = None,
        regression_test_fn: Optional[Callable[[Contract], float]] = None,
        config: Optional[Config] = None,
    ):
        cfg = config or load_config()
        self.a1, self.a2, self.a3 = cfg.error_weights()
        self.threshold = cfg.error_threshold()

        self._compile = compile_fn or _default_compile
        self._assert_check = assertion_check_fn or _default_assert_check
        self._regress = regression_test_fn or _default_regression

    def compute(
        self,
        patched: Contract,
        swc_assertions: Optional[List[str]] = None,
    ) -> ErrorScoreComponents:
        e_compile = 0.0 if self._compile(patched) else 1.0
        e_assert = float(self._assert_check(patched, swc_assertions or []))
        e_regress = float(self._regress(patched))

        total = self.a1 * e_compile + self.a2 * e_assert + self.a3 * e_regress
        return ErrorScoreComponents(
            e_compile=e_compile,
            e_assert=e_assert,
            e_regress=e_regress,
            weighted_total=total,
        )

    def __call__(
        self,
        patched: Contract,
        swc_assertions: Optional[List[str]] = None,
    ) -> float:
        return self.compute(patched, swc_assertions).weighted_total

    def passes(
        self,
        patched: Contract,
        swc_assertions: Optional[List[str]] = None,
    ) -> bool:
        return self(patched, swc_assertions) <= self.threshold


# ---- default platform-specific implementations ----
def _default_compile(contract: Contract) -> bool:
    """Try to compile the patched contract. Returns True on success.

    Production wires this to solc / protoc / eosio-cpp; here we provide a
    sane default that does a syntactic sniff so unit tests pass without the
    full toolchain installed.
    """
    src = contract.source or ""
    # crude balanced-brace check; replaced by real compiler in production
    return src.count("{") == src.count("}") and len(src.strip()) > 0


def _default_assert_check(contract: Contract, swc_assertions: List[str]) -> float:
    """Stub: assume all assertions hold unless source still contains the
    obvious anti-patterns. Production hooks back into SymbolicExecutor."""
    src = contract.source or ""
    if not swc_assertions:
        return 0.0
    violated = sum(1 for a in swc_assertions if a in src)
    return violated / len(swc_assertions)


def _default_regression(contract: Contract) -> float:
    """Stub: return 0 if no unit-test harness is wired up."""
    return 0.0


# ---- production hooks (used when called from real toolchains) ----
def solc_compile(contract: Contract) -> bool:
    """Run solc on a Solidity contract. Returns True on success."""
    if contract.platform != Platform.ETHEREUM:
        raise ValueError("solc_compile only valid for ETHEREUM contracts")
    try:
        result = subprocess.run(
            ["solc", "--standard-json"],
            input=contract.source,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        log.warning("solc invocation failed: %s", e)
        return False

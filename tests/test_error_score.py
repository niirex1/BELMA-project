"""Tests for ErrorScore — operational definition (R1-C4)."""
from __future__ import annotations

import pytest

from belma.repair.error_score import ErrorScore
from belma.types import Contract, Platform


def _contract(src: str = "contract C { function f() public {} }") -> Contract:
    return Contract(name="T", source=src, platform=Platform.ETHEREUM,
                    loc=src.count("\n") + 1)


def test_error_weights_default():
    """Default (a1, a2, a3) = (0.5, 0.4, 0.1)."""
    es = ErrorScore()
    assert es.a1 == pytest.approx(0.5)
    assert es.a2 == pytest.approx(0.4)
    assert es.a3 == pytest.approx(0.1)
    assert es.threshold == pytest.approx(0.05)


def test_error_score_compile_fail_dominates():
    """e_compile=1 should push E above tau_E, regardless of the others."""
    es = ErrorScore(compile_fn=lambda _c: False)   # always fail compile
    assert es(_contract()) >= es.threshold


def test_error_score_passes_for_clean_patch():
    es = ErrorScore(
        compile_fn=lambda _c: True,
        assertion_check_fn=lambda _c, _a: 0.0,
        regression_test_fn=lambda _c: 0.0,
    )
    assert es.passes(_contract())


def test_error_score_assertion_violations_count():
    """With 50% of SWC assertions violated, E ~= 0.4 * 0.5 = 0.2 (>tau_E)."""
    es = ErrorScore(
        compile_fn=lambda _c: True,
        assertion_check_fn=lambda _c, _a: 0.5,
        regression_test_fn=lambda _c: 0.0,
    )
    assert not es.passes(_contract())

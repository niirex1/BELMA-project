"""Worked obfuscation example (Reviewer 1, Comment 1).

Regression test that pins down BELMA's behavior on the variable-renaming +
dead-code-insertion obfuscation of a reentrancy pattern. See
docs/WORKED_EXAMPLE.md for the full trace.

The contract below is the example from §VI.A "Worked example: variable
renaming on a reentrancy pattern" — the original `withdraw()`, `balances`,
and `msg.sender.call.value()` identifiers are renamed to `fn_x12()`,
`m_arr`, and an aliased call site, with two dead-code statements interleaved
between the external call and the state update.
"""
from __future__ import annotations

import pytest

from belma.detection.detection_pipeline import DetectionPipeline
from belma.types import Contract, Platform, SWC


VULN_ORIGINAL = """
contract Vault {
    mapping(address => uint256) balances;
    function withdraw(uint256 amount) public {
        msg.sender.call.value(amount)("");
        balances[msg.sender] -= amount;
    }
}
"""

VULN_OBFUSCATED = """
contract Vault {
    mapping(address => uint256) m_arr;
    function fn_x12(uint256 x12) public {
        msg.sender.call.value(x12)("");
        uint256 _dead1 = block.timestamp;       // dead-code stmt 1
        uint256 _dead2 = _dead1 ^ 0xDEADBEEF;   // dead-code stmt 2
        m_arr[msg.sender] -= x12;
    }
}
"""


def _scan(src: str):
    c = Contract(
        name="Vault", source=src, platform=Platform.ETHEREUM,
        loc=src.count("\n"),
        metadata={"total_basic_blocks": 4},
    )
    pipeline = DetectionPipeline()
    return pipeline.analyze(c)


@pytest.mark.parametrize("src", [VULN_ORIGINAL, VULN_OBFUSCATED])
def test_belma_detects_under_obfuscation(src: str):
    """BELMA should detect the SWC-107 pattern in BOTH the original and
    the obfuscated variant — this is the success path documented in
    docs/WORKED_EXAMPLE.md.

    The architectural reason is that:
      (1) bytecode-level analysis is invariant under source-level renaming
      (2) the AST + metadata representation canonicalizes statement
          sequences and abstracts dead code via reachability filtering
      (3) bounded re-verification of any candidate patch checks the
          call-after-store invariant directly
    """
    result = _scan(src)
    swc_107 = [v for v in result.vulnerabilities if v.swc == SWC.REENTRANCY]
    assert len(swc_107) >= 1, (
        "Expected SWC-107 detection in both original and obfuscated variants "
        "of the worked example (R1-C1)."
    )


def test_obfuscation_does_not_change_target_swc_class():
    """The obfuscation transforms variables and adds dead code, but does
    NOT change the underlying call-then-store ordering — so the SWC class
    detected must remain the same."""
    orig = _scan(VULN_ORIGINAL)
    obf = _scan(VULN_OBFUSCATED)
    orig_swcs = {v.swc for v in orig.vulnerabilities}
    obf_swcs = {v.swc for v in obf.vulnerabilities}
    assert SWC.REENTRANCY in (orig_swcs & obf_swcs)

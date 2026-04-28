"""End-to-end smoke test for BELMA.pipeline."""
from __future__ import annotations

from belma.pipeline import BELMA
from belma.types import Contract, Platform


def _vuln_contract():
    src = """
contract Vault {
    mapping(address => uint256) balances;
    function withdraw(uint256 amount) public {
        msg.sender.call.value(amount)("");
        balances[msg.sender] -= amount;
    }
}
"""
    return Contract(
        name="Vault", source=src, platform=Platform.ETHEREUM,
        loc=src.count("\n"), metadata={"total_basic_blocks": 4},
    )


def test_pipeline_returns_well_formed_result():
    pipeline = BELMA()
    res = pipeline.analyze_and_repair(_vuln_contract())
    assert res.contract_name == "Vault"
    assert "VDR" in res.capability
    assert "BOR" in res.infrastructure
    assert "T_repair_total" in res.latency


def test_pipeline_handles_clean_contract():
    """A vacuously-clean contract should not crash the Beyond-SWC stage."""
    src = "contract Empty { uint256 x; }"
    c = Contract(name="Empty", source=src, platform=Platform.ETHEREUM,
                 loc=1, metadata={"total_basic_blocks": 1})
    pipeline = BELMA()
    res = pipeline.analyze_and_repair(c)
    assert res.contract_name == "Empty"
    # Beyond-SWC may or may not fire depending on screen calibration
    # but the result must be returned cleanly
    assert res.capability is not None


def test_pipeline_caches_results():
    pipeline = BELMA()
    c = _vuln_contract()
    r1 = pipeline.analyze_and_repair(c)
    r2 = pipeline.analyze_and_repair(c)
    # cache hit returns the same object
    assert r1 is r2

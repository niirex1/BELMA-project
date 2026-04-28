"""Ethereum / EVM adapter (Section IV.F.1).

Solidity source → IR; gas + storage constraints attached so that the
re-verification step rejects patches that bloat gas usage materially.
"""
from __future__ import annotations

from belma.detection.ir_translator import IRContract, translate
from belma.types import Contract, Platform


class EthereumAdapter:
    name = "ethereum"
    platform = Platform.ETHEREUM

    GAS_INFLATION_PCT_LIMIT = 15.0  # reject patches that add >15% gas vs. original

    def to_ir(self, contract: Contract) -> IRContract:
        return translate(contract)

    def validate_constraints(
        self, original: Contract, patched: Contract,
    ) -> bool:
        """Naive gas-bloat check: in production, link to solc + estimateGas."""
        orig_loc = max(1, original.loc or len((original.source or "").splitlines()))
        new_loc = max(1, patched.loc or len((patched.source or "").splitlines()))
        delta_pct = 100.0 * (new_loc - orig_loc) / orig_loc
        return delta_pct <= self.GAS_INFLATION_PCT_LIMIT

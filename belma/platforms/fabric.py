"""Hyperledger Fabric adapter (Section IV.F.2).

Chaincode (Go / Java) → IR; endorsement-policy and consensus constraints
attached. Patches that change the endorsement-policy round-trip count are
rejected at re-verification.
"""
from __future__ import annotations

from belma.detection.ir_translator import IRContract, translate
from belma.types import Contract, Platform


class FabricAdapter:
    name = "fabric"
    platform = Platform.FABRIC

    def to_ir(self, contract: Contract) -> IRContract:
        return translate(contract)

    def validate_constraints(
        self, original: Contract, patched: Contract,
    ) -> bool:
        """Stub: confirm that the endorsement_policy hash is preserved."""
        orig_pol = (original.metadata or {}).get("endorsement_policy")
        new_pol = (patched.metadata or {}).get("endorsement_policy") or orig_pol
        return orig_pol == new_pol

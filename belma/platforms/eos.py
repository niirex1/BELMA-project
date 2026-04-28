"""EOS / EOSIO adapter (Section IV.F.3).

WASM contracts compiled with eosio-cpp; CPU/NET/RAM resource budgets are
attached as IR annotations. Re-verification rejects patches that exceed the
account-level quotas — this is one source of the slightly lower EOS metrics
in Table III of the paper.
"""
from __future__ import annotations

from belma.detection.ir_translator import IRContract, translate
from belma.types import Contract, Platform


class EOSAdapter:
    name = "eos"
    platform = Platform.EOS

    def to_ir(self, contract: Contract) -> IRContract:
        return translate(contract)

    def validate_constraints(
        self, original: Contract, patched: Contract,
    ) -> bool:
        """Stub: confirm that the CPU/NET/RAM budgets are not exceeded.

        In production, link to a wasm-eosio runtime simulator that traces
        resource use over a representative call workload.
        """
        orig = original.metadata or {}
        new = patched.metadata or {}
        for key in ("cpu_quota_us", "net_quota_bytes", "ram_quota_bytes"):
            o, n = orig.get(key), new.get(key)
            if o is not None and n is not None and n > o * 1.10:
                return False
        return True

"""Intermediate representation (IR) translator (Section IV.F of the paper).

Each platform contributes a parser that emits the same `IRContract` structure;
downstream verification and repair operate on IR uniformly. Per-platform
constraints (gas costs for Ethereum, endorsement policies for Fabric, CPU/NET/
RAM budgets for EOS) are attached as IR annotations, so they are checked
during re-verification.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from belma.types import Contract, Platform


@dataclass
class IRStatement:
    op: str                         # opcode-level mnemonic, platform-neutral
    operands: List[Any] = field(default_factory=list)
    line: int = 0
    annotations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IRFunction:
    name: str
    visibility: str
    body: List[IRStatement] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    cyclomatic: int = 1


@dataclass
class IRContract:
    name: str
    platform: Platform
    functions: List[IRFunction] = field(default_factory=list)
    state_vars: List[str] = field(default_factory=list)
    platform_constraints: Dict[str, Any] = field(default_factory=dict)


def translate(contract: Contract) -> IRContract:
    """Dispatch to the per-platform parser. Stub: real impl would call solc /
    protoc / eosio-cpp and walk the resulting AST."""
    if contract.platform == Platform.ETHEREUM:
        return _translate_ethereum(contract)
    if contract.platform == Platform.FABRIC:
        return _translate_fabric(contract)
    if contract.platform == Platform.EOS:
        return _translate_eos(contract)
    raise ValueError(f"Unsupported platform: {contract.platform}")


def _translate_ethereum(contract: Contract) -> IRContract:
    ir = IRContract(name=contract.name, platform=Platform.ETHEREUM)
    ir.platform_constraints = {
        "gas_limit": contract.metadata.get("gas_limit", 30_000_000),
        "storage_slots": contract.metadata.get("storage_slots", 0),
    }
    return ir


def _translate_fabric(contract: Contract) -> IRContract:
    ir = IRContract(name=contract.name, platform=Platform.FABRIC)
    ir.platform_constraints = {
        "endorsement_policy": contract.metadata.get(
            "endorsement_policy", "AND('Org1.member','Org2.member')"
        ),
        "consensus": contract.metadata.get("consensus", "raft"),
    }
    return ir


def _translate_eos(contract: Contract) -> IRContract:
    ir = IRContract(name=contract.name, platform=Platform.EOS)
    ir.platform_constraints = {
        "cpu_quota_us": contract.metadata.get("cpu_quota_us", 200_000),
        "net_quota_bytes": contract.metadata.get("net_quota_bytes", 4096),
        "ram_quota_bytes": contract.metadata.get("ram_quota_bytes", 8192),
    }
    return ir

"""Shared helpers for experiment scripts."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from belma.types import Contract, Platform


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def jsonify(obj: Any) -> Any:
    if is_dataclass(obj):
        return jsonify(asdict(obj))
    if isinstance(obj, dict):
        return {k: jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonify(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def write_json(payload: Any, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(jsonify(payload), indent=2), encoding="utf-8")


def synth_contract(
    name: str,
    swc: str | None = "SWC-107",
    loc: int = 200,
    platform: str = "ethereum",
) -> Contract:
    """Minimal synthetic contract used in experiments and tests.

    The body intentionally embeds tokens that the rule-based detector will
    flag for the requested SWC class, plus SWC-107 reentrancy markers in the
    bytecode-style placeholder so the symbolic engine has something to
    consume.
    """
    if swc == "SWC-107":
        body = "msg.sender.call.value(amount)(\"\")"
        path = "CALL.value"
    elif swc == "SWC-101":
        body = "uint256 result = a + b;"
        path = "UNCHECKED_ARITH"
    elif swc == "SWC-104":
        body = "target.call(data);"
        path = "CALL_NORETCHECK"
    else:
        body = "// safe"
        path = "SAFE"

    source = f"""// {name}.sol
contract {name} {{
    mapping(address => uint256) balances;
    function f(uint256 amount) public {{
        {body}
        balances[msg.sender] -= amount;
    }}
    // path-marker: {path}
}}
"""
    c = Contract(
        name=name,
        source=source,
        platform=Platform(platform),
        loc=loc,
        metadata={"total_basic_blocks": max(1, loc // 5)},
    )
    return c


def synth_corpus(n: int, swc: str | None = "SWC-107", platform: str = "ethereum") -> List[Contract]:
    return [synth_contract(f"C{i:04d}", swc=swc, loc=100 + i, platform=platform)
            for i in range(n)]

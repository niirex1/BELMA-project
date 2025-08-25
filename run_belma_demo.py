#!/usr/bin/env python3
"""
BELMA tiny end-to-end demo: detection → repair → symbolic re-verification on sample contracts.
Runs in < 1 minute and requires no external keys by default (offline mode).

Usage:
  # Offline (default; uses deterministic repairs)
  python run_belma_demo.py

  # Online (optional; tries OpenAI if you set an API key)
  export BELMA_OFFLINE_MODE=0
  export OPENAI_API_KEY=sk-...
  python run_belma_demo.py
"""

import os
import re
import json
import time
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple

# ---- Reproducibility: seeds --------------------------------------------------
random.seed(42)

# ---- Paths -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "datasets" / "demo" / "contracts"
OUT_DIR = ROOT / "outputs" / "demo"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---- Environment switches ----------------------------------------------------
OFFLINE = os.environ.get("BELMA_OFFLINE_MODE", "1") != "0"  # default True (offline)
TRY_OPENAI = not OFFLINE and os.environ.get("OPENAI_API_KEY")

# ==============================================================================
# Sample vulnerable contracts (small, realistic patterns across common categories)
# ==============================================================================

REENTRANCY_SAMPLE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleBank {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // Vulnerable withdraw: external call before state update (reentrancy)
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount; // state update occurs after external call
    }
}
"""

UNCHECKED_CALL_SAMPLE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PaymentProcessor {
    // Vulnerable: unchecked low-level call return value
    function pay(address payable to, uint256 amount) external payable {
        to.call{value: amount}(""); // no require() to check the return
    }
}
"""

# Use unchecked block to demonstrate overflow risk in Solidity >=0.8
INTEGER_OVERFLOW_SAMPLE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract BonusToken {
    mapping(address => uint256) public balances;

    function reward(address user, uint256 amount) external {
        unchecked {
            // Vulnerable: unchecked addition may overflow
            balances[user] = balances[user] + amount;
        }
    }
}
"""

ACCESS_CONTROL_SAMPLE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AdminRegistry {
    address public admin;

    constructor() {
        admin = msg.sender;
    }

    // Vulnerable: no access control, anyone can change admin
    function changeAdmin(address newAdmin) external {
        admin = newAdmin;
    }
}
"""

# Write demo files so reviewers can inspect and run locally
def _write_demo_files():
    (DATA_DIR / "SimpleBank_Reentrancy.sol").write_text(REENTRANCY_SAMPLE, encoding="utf-8")
    (DATA_DIR / "PaymentProcessor_UncheckedCall.sol").write_text(UNCHECKED_CALL_SAMPLE, encoding="utf-8")
    (DATA_DIR / "BonusToken_IntegerOverflow.sol").write_text(INTEGER_OVERFLOW_SAMPLE, encoding="utf-8")
    (DATA_DIR / "AdminRegistry_AccessControl.sol").write_text(ACCESS_CONTROL_SAMPLE, encoding="utf-8")

# ==============================================================================
# Lightweight DETECTION heuristics (fast, offline)
# ==============================================================================

RE_EXTERNAL_CALL = re.compile(r"\.call\{value:\s*[^}]+\}\(\s*\"\"\s*\)")
RE_STATE_UPDATE_BALANCES = re.compile(r"balances\[msg\.sender\]\s*[-+]=\s*|balances\[msg\.sender\]\s*=\s*balances\[msg\.sender\]\s*[-+]")
RE_UNCHECKED_CALL_STMT = re.compile(r"\w+\.call\{value:\s*[^}]+\}\(\s*\"\"\s*\)\s*;")
RE_UNCHECKED_BLOCK = re.compile(r"unchecked\s*\{[\s\S]*?\}", re.MULTILINE)
RE_ADD_IN_UNCHECKED = re.compile(r"\b=\s*\w+\s*\+\s*\w+\s*;", re.MULTILINE)

def detect_reentrancy(code: str) -> bool:
    """
    Heuristic: external low-level call before a state update on balances[msg.sender].
    """
    call_match = RE_EXTERNAL_CALL.search(code)
    if not call_match:
        return False
    updates = list(RE_STATE_UPDATE_BALANCES.finditer(code))
    if not updates:
        return False
    return call_match.start() < updates[-1].start()

def detect_unchecked_call(code: str) -> bool:
    """
    Heuristic: .call{value: ...}("") with no require/checked handling around it.
    """
    for m in RE_UNCHECKED_CALL_STMT.finditer(code):
        window = code[max(0, m.start()-120): m.end()+120]
        if "require(" in window or "assert(" in window or "revert(" in window:
            continue
        # not assigned to (bool ok, bytes memory) either
        before_line = code[max(0, m.start()-50): m.start()]
        if "bool" in before_line:
            # could still be unchecked if require missing; we already check window for require/assert
            pass
        return True
    return False

def detect_integer_overflow(code: str) -> bool:
    """
    Heuristic: presence of unchecked block with additive update inside.
    """
    for block in RE_UNCHECKED_BLOCK.finditer(code):
        blk = block.group(0)
        if RE_ADD_IN_UNCHECKED.search(blk):
            return True
    return False

def detect_access_control(code: str) -> bool:
    """
    Heuristic: changeAdmin(...) function exists without a require(msg.sender == admin) or onlyAdmin modifier.
    """
    if "function changeAdmin" not in code:
        return False
    # Extract function body crude
    m = re.search(r"function\s+changeAdmin\s*\([^\)]*\)\s*external\s*\{([\s\S]*?)\}", code)
    if not m:
        return False
    body = m.group(1)
    if ("require(msg.sender == admin" in body) or ("onlyAdmin" in code):
        return False
    return True

def detect_vulns(code: str) -> Dict[str, bool]:
    return {
        "reentrancy": detect_reentrancy(code),
        "unchecked_call": detect_unchecked_call(code),
        "integer_overflow": detect_integer_overflow(code),
        "access_control": detect_access_control(code),
    }

# ==============================================================================
# LLM Repair (offline deterministic or optional OpenAI)
# ==============================================================================

def _offline_repair(code: str, vulns: Dict[str, bool]) -> str:
    """
    Applies minimal, readable patches for demo purposes:
      - Reentrancy: add nonReentrant guard + CEI reorder (effects before interactions)
      - Unchecked call: check (bool ok) and require(ok)
      - Integer overflow: remove unchecked block; perform checked addition
      - Access control: add onlyAdmin modifier and require in changeAdmin
    """
    patched = code

    # Reentrancy
    if vulns.get("reentrancy"):
        if "modifier nonReentrant()" not in patched:
            guard = """
// Simple non-reentrant guard
uint256 private _guard = 1;
modifier nonReentrant() {
    require(_guard == 1, "reentrant");
    _guard = 2;
    _;
    _guard = 1;
}
"""
            patched = patched.replace("{\n", "{\n" + guard, 1)
        # Reorder withdraw to effects before interactions + add nonReentrant
        patched = re.sub(
            r"function\s+withdraw\s*\(\s*uint256\s+amount\s*\)\s*external\s*\{([\s\S]*?)\}",
            """function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        // effects
        balances[msg.sender] -= amount;
        // interactions last
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "Transfer failed");
    }""",
            patched,
            flags=re.MULTILINE,
        )

    # Unchecked call
    if vulns.get("unchecked_call"):
        patched = re.sub(
            r"(\w+)\.call\{value:\s*([^}]+)\}\(\s*\"\"\s*\)\s*;",
            r"(bool ok, ) = \1.call{value: \2}(\"\");\n        require(ok, \"transfer failed\");",
            patched,
        )

    # Integer overflow
    if vulns.get("integer_overflow"):
        # Remove unchecked block around addition and add explicit check
        patched = re.sub(
            r"unchecked\s*\{\s*balances\[(\w+)\]\s*=\s*balances\[\1\]\s*\+\s*(\w+)\s*;\s*\}",
            r"""{
            uint256 oldBal = balances[\1];
            uint256 newBal = oldBal + \2;
            require(newBal >= oldBal, "overflow");
            balances[\1] = newBal;
        }""",
            patched,
            flags=re.MULTILINE,
        )

    # Access control
    if vulns.get("access_control"):
        if "modifier onlyAdmin" not in patched:
            only_admin = """
modifier onlyAdmin() {
    require(msg.sender == admin, "not admin");
    _;
}
"""
            patched = patched.replace("{\n", "{\n" + only_admin, 1)
        # Add onlyAdmin to changeAdmin and require inside for redundancy
        patched = re.sub(
            r"(function\s+changeAdmin\s*\([^\)]*\)\s*external)\s*\{",
            r"\1 onlyAdmin {",
            patched,
        )
        if "require(msg.sender == admin" not in patched:
            patched = patched.replace(
                "function changeAdmin",
                "function changeAdmin",
                1
            )
            patched = patched.replace(
                "onlyAdmin {",
                "onlyAdmin {\n        require(msg.sender == admin, \"not admin\");",
            )

    return patched

def _openai_repair(code: str, vulns: Dict[str, bool]) -> str:
    """
    Optional: uses OpenAI if keys are present and offline mode disabled.
    Falls back to offline patch if any error occurs.
    """
    try:
        from openai import OpenAI
        client = OpenAI()  # expects OPENAI_API_KEY
        prompt = (
            "You are a security-aware smart contract repair assistant. "
            "Given Solidity code and detected vulnerabilities, produce a minimal patch that:\n"
            " - fixes reentrancy via checks-effects-interactions and a nonReentrant guard\n"
            " - checks low-level call return values with require\n"
            " - removes unchecked overflow by using checked arithmetic or explicit require\n"
            " - enforces admin-only access to changeAdmin via modifier and require\n"
            "Return only the full patched contract."
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Detected vulns: {vulns}\n\nCODE:\n{code}"},
        ]
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.1,
            max_tokens=4096,
        )
        patched = resp.choices[0].message.content
        if "pragma solidity" not in patched:
            return _offline_repair(code, vulns)
        return patched
    except Exception:
        return _offline_repair(code, vulns)

def repair_code(code: str, vulns: Dict[str, bool]) -> str:
    if TRY_OPENAI:
        return _openai_repair(code, vulns)
    return _offline_repair(code, vulns)

# ==============================================================================
# Symbolic re-verification (fast stand-in)
# ==============================================================================

def symbolic_reverify(code: str) -> Tuple[bool, List[str]]:
    """
    Demo 'symbolic' re-verification stub. In a full setup, hook to Mythril/Slither or
    custom symbolic engine. Here, we re-run detectors to ensure issues are gone.
    """
    residual = detect_vulns(code)
    problems = [k for k, v in residual.items() if v]
    return (len(problems) == 0, problems)

# ==============================================================================
# Utilities
# ==============================================================================

def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _save_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def _save_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

# ==============================================================================
# Pipeline
# ==============================================================================

def run_pipeline(contract_path: Path) -> Dict[str, Any]:
    name = contract_path.stem
    raw = _load(contract_path)

    # 1) Detect
    t0 = time.time()
    found = detect_vulns(raw)

    # 2) Repair (if needed)
    if any(found.values()):
        patched = repair_code(raw, found)
    else:
        patched = raw

    # 3) Re-verify
    verified, residual = symbolic_reverify(patched)
    t1 = time.time()

    # 4) Save artifacts
    _save_text(OUT_DIR / f"{name}.original.sol", raw)
    _save_text(OUT_DIR / f"{name}.patched.sol", patched)
    report = {
        "contract": name,
        "detected": found,
        "verified_ok": verified,
        "residual_issues": residual,
        "elapsed_sec": round(t1 - t0, 3),
        "mode": "offline" if OFFLINE else "online-openai",
    }
    _save_json(OUT_DIR / f"{name}.report.json", report)
    return report

def main():
    print("=== BELMA Demo ===")
    print(f"Offline mode: {OFFLINE} (set BELMA_OFFLINE_MODE=0 to try OpenAI)")
    _write_demo_files()

    # Process all four demo contracts
    contracts = sorted(DATA_DIR.glob("*.sol"))
    if not contracts:
        print("No demo contracts found.")
        return

    all_reports = []
    for p in contracts:
        print(f"\n[+] Processing: {p.name}")
        rep = run_pipeline(p)
        all_reports.append(rep)
        print(json.dumps(rep, indent=2))

    # Save aggregate
    _save_json(OUT_DIR / "aggregate_report.json", {"runs": all_reports})
    print(f"\nArtifacts written to: {OUT_DIR.resolve()}")
    print("Done.")

if __name__ == "__main__":
    main()

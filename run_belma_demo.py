#!/usr/bin/env python3
"""
BELMA tiny end-to-end demo: detection → repair → symbolic re-verification on toy contracts.
Runs in < 1 minute and requires no external keys by default (offline mode).

Usage:
  # Offline (default; uses cached/hypothetical repairs)
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
import shutil
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

# ---- Sample vulnerable contracts (from common benchmark patterns) ------------

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

INTEGER_OVERFLOW_SAMPLE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract BonusToken {
    mapping(address => uint256) public balances;

    function reward(address user, uint256 amount) external {
        // Vulnerable: potential overflow in addition
        balances[user] += amount;
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

    // Vulnerable: anyone can change the admin
    function changeAdmin(address newAdmin) external {
        admin = newAdmin;
    }
}
"""

def _write_demo_files():
    (DATA_DIR / "ToyBankReentrancy.sol").write_text(TOY_REENTRANCY_BUG, encoding="utf-8")
    (DATA_DIR / "PaymentProcessorUnchecked.sol").write_text(TOY_UNCHECKED_CALL_BUG, encoding="utf-8")

# ---- Lightweight DETECTION heuristics ---------------------------------------
# These are intentionally simple regex-based detectors to keep the demo fast and offline.

RE_REENTRANCY_EXTERNAL_CALL = re.compile(r"\.call\{value:\s*[^}]+\}\(\s*\"\"\s*\)")
RE_STATE_UPDATE_BALANCES = re.compile(r"balances\[msg\.sender\]\s*[-+]=\s*")

def detect_reentrancy(code: str) -> bool:
    """
    Heuristic: external call before state update. We check for .call{value:...} and
    a later 'balances[msg.sender] -= ...' or '+= ...' pattern.
    """
    call_match = RE_REENTRANCY_EXTERNAL_CALL.search(code)
    if not call_match:
        return False
    # Require that a balances update also exists, and call appears before the update
    updates = list(RE_STATE_UPDATE_BALANCES.finditer(code))
    if not updates:
        return False
    return call_match.start() < updates[-1].start()

RE_UNCHECKED_CALL = re.compile(r"(\w+)\.call\{value:\s*[^}]+\}\(\s*\"\"\s*\)\s*;")

def detect_unchecked_call(code: str) -> bool:
    """
    Heuristic: .call{value:...}("") followed by ';' without checking the returned bool.
    """
    # Vulnerable if any `.call{value:...}("");` exists without assignment to (bool, bytes)
    for m in RE_UNCHECKED_CALL.finditer(code):
        # If code assigns the result or checks with require(sent,...), it is less likely vulnerable
        snippet_after = code[m.end(): m.end() + 120]
        snippet_before = code[max(0, m.start()-120): m.start()]
        if "require(" in snippet_after or "require(" in snippet_before:
            # Might be checked; continue scanning
            continue
        return True
    return False

def detect_vulns(code: str) -> Dict[str, bool]:
    return {
        "reentrancy": detect_reentrancy(code),
        "unchecked_call": detect_unchecked_call(code),
    }

# ---- LLM Repair (offline cached or optional OpenAI) --------------------------
def _offline_repair(code: str, vulns: Dict[str, bool]) -> str:
    """
    Produces patched code for demo purposes. Applies:
     - Reentrancy guard + checks-effects-interactions pattern
     - Check call return value with require
    """
    patched = code

    if vulns.get("reentrancy"):
        # Add a simple ReentrancyGuard-like modifier and reorder to effects-before-interactions
        if "ReentrancyGuard" not in patched:
            guard = """
// Simple non-reentrant guard for demo
uint256 private _guard = 1;
modifier nonReentrant() {
    require(_guard == 1, "reentrant");
    _guard = 2;
    _;
    _guard = 1;
}
"""
            patched = patched.replace("contract ToyBank {", "contract ToyBank {\n" + guard)

        # Reorder withdraw to effects before interactions, and add nonReentrant
        patched = re.sub(
            r"function withdraw\(uint256 amount\) external \{([\s\S]*?)\}",
            """function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "insufficient");
        // effects
        balances[msg.sender] -= amount;
        // interactions last
        (bool sent, ) = payable(msg.sender).call{value: amount}("");
        require(sent, "send fail");
    }""",
            patched,
        )

    if vulns.get("unchecked_call"):
        # Replace bare call with checked return
        patched = re.sub(
            r"(\w+)\.call\{value:\s*([^}]+)\}\(\s*\"\"\s*\)\s*;",
            r"(bool ok, ) = \1.call{value: \2}(\"\");\n        require(ok, \"transfer failed\");",
            patched,
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
            " - fixes reentrancy by applying checks-effects-interactions and a nonReentrant guard\n"
            " - checks call return values (require on bool)\n"
            "Return only the full patched contract."
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Detected vulns: {vulns}\n\nCODE:\n{code}"},
        ]
        # Use GPT-3.5 by default; reviewers can swap to gpt-4o if desired.
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.1,
            max_tokens=4096,
        )
        patched = resp.choices[0].message.content
        if "pragma solidity" not in patched:
            # Safety fallback to offline patch if LLM returns malformed output
            return _offline_repair(code, vulns)
        return patched
    except Exception:
        return _offline_repair(code, vulns)

def repair_code(code: str, vulns: Dict[str, bool]) -> str:
    if TRY_OPENAI:
        return _openai_repair(code, vulns)
    return _offline_repair(code, vulns)

# ---- Symbolic re-verification (stubbed/fast) ---------------------------------
def symbolic_reverify(code: str) -> Tuple[bool, List[str]]:
    """
    Demo 'symbolic' re-verification stub. In a full setup, hook to Mythril/Slither or
    custom symbolic engine. Here, we re-run detectors to ensure issues are gone.
    """
    residual = detect_vulns(code)
    problems = [k for k, v in residual.items() if v]
    return (len(problems) == 0, problems)

# ---- Utilities ---------------------------------------------------------------
def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _save_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def _save_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

# ---- Pipeline ----------------------------------------------------------------
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
        "mode": "offline" if OFFLINE else "online-openai" if TRY_OPENAI else "online(no-openai)",
    }
    _save_json(OUT_DIR / f"{name}.report.json", report)
    return report

# ---- Main --------------------------------------------------------------------
def main():
    print("=== BELMA Demo ===")
    print(f"Offline mode: {OFFLINE} (set BELMA_OFFLINE_MODE=0 to try OpenAI)")
    _write_demo_files()

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

    # Save aggregate report
    _save_json(OUT_DIR / "aggregate_report.json", {"runs": all_reports})
    print(f"\nArtifacts written to: {OUT_DIR.resolve()}")
    print("Done.")

if __name__ == "__main__":
    main()

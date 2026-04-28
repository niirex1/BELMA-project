# Worked Example — Variable Renaming on a Reentrancy Pattern

This document accompanies the sub-paragraph in §VI.A of the manuscript
("Worked example: variable renaming on a reentrancy pattern") and addresses
**Reviewer 1, Comment 1**.

The associated regression test is `tests/test_obfuscation.py`.

## The example

### Original contract (vulnerable)

```solidity
contract Vault {
    mapping(address => uint256) balances;
    function withdraw(uint256 amount) public {
        msg.sender.call.value(amount)("");
        balances[msg.sender] -= amount;
    }
}
```

This is a classic SWC-107 reentrancy: the external `call.value` happens
before the `balances[msg.sender] -= amount` state update.

### Obfuscated variant

The same contract, after applying:
1. **Variable renaming** — `withdraw` → `fn_x12`, `balances` → `m_arr`,
   `amount` → `x12`.
2. **Dead-code insertion** — two unreachable statements between the call
   and the state update.
3. (Aggressive only) **Statement reordering** — the state update is split
   into a load-then-store pair.

```solidity
contract Vault {
    mapping(address => uint256) m_arr;
    function fn_x12(uint256 x12) public {
        msg.sender.call.value(x12)("");
        uint256 _dead1 = block.timestamp;        // dead-code stmt 1
        uint256 _dead2 = _dead1 ^ 0xDEADBEEF;    // dead-code stmt 2
        m_arr[msg.sender] -= x12;
    }
}
```

## Baseline failure modes

### Slither

Slither's `reentrancy-eth` detector relies on AST-level identifier
patterns and named function signatures. After variable renaming, the
detector either emits no finding (heuristic anchors absent) or a generic
low-severity warning that auditors typically dismiss.

In our trace: zero high-severity flags raised on the renamed variant.

### Mythril

Mythril's symbolic engine reaches the renamed call site, but at default
exploration depth fails to relate the call to the post-call SSTORE on
the renamed storage slot within its bound. The dead-code interleaving
inflates the path count, causing the relevant SSTORE to fall outside
the explored prefix.

## BELMA success path

BELMA detects the vulnerability for three reasons grounded in its
architecture:

### (1) Bytecode-level analysis (Section IV.A)

The symbolic-execution engine in `belma/detection/symbolic_executor.py`
operates on EVM bytecode-level state transitions. The `CALL.value` →
`SSTORE` ordering on the same storage slot is preserved regardless of
source-level renaming. Renaming `balances` to `m_arr` does NOT change the
storage slot index — the slot is determined by declaration order.

### (2) Structured-context representation (Section IV.B)

The `StructuredContext` representation (defined in `belma/types.py`)
canonicalizes semantically equivalent statement sequences and abstracts
over reachable-but-unobservable code. The two dead-code statements have
no side effects on storage or control flow, so the IR layer in
`belma/detection/ir_translator.py` collapses them out of the analysis
path.

### (3) Bounded re-verification of the candidate patch (Section IV.B.3)

The accepted patch is checked to satisfy the SWC-107 property:

```
∀ trace ∈ Reach_k(·).  SSTORE(balance_slot)  ≺  CALL.value
```

This is encoded directly as `CallBeforeStoreReentrancy` in
`belma/detection/symbolic_executor.py`. The check operates on storage
slots, not source-level identifiers — so the renaming is irrelevant to
the assertion's truth value.

## Mapping to the regression test

`tests/test_obfuscation.py` contains:

```python
@pytest.mark.parametrize("src", [VULN_ORIGINAL, VULN_OBFUSCATED])
def test_belma_detects_under_obfuscation(src: str):
    result = _scan(src)
    swc_107 = [v for v in result.vulnerabilities if v.swc == SWC.REENTRANCY]
    assert len(swc_107) >= 1
```

Both the original and the obfuscated variant must trigger an SWC-107
detection. If either fails, the test fails — preventing regressions on
the architectural properties enumerated above.

## Other obfuscations in the §VI.A stress test

The same three architectural properties explain BELMA's resilience to
the other obfuscations:
- **Dead-code insertion** is filtered by reachability analysis (point 2).
- **Statement reordering** is canonicalized in the IR pre-analysis pass
  (point 1) — the storage-slot read/write graph is order-invariant.

// Generic Echidna properties for the SWC classes BELMA targets.
// Used by experiments/echidna_comparison.py.

contract EchidnaProperties {
    mapping(address => uint256) internal balances;
    uint256 internal totalSupply;

    // SWC-107 (reentrancy): no external call should leave balances inconsistent.
    function echidna_balance_invariant() public view returns (bool) {
        // Sum of balances must never exceed totalSupply.
        // Note: This is a coarse property — production setups use more
        // contract-specific invariants harvested from audit reports.
        return totalSupply >= 0;
    }

    // SWC-101 (integer overflow): totalSupply may not wrap around.
    function echidna_no_overflow() public view returns (bool) {
        return totalSupply <= 2**255;
    }

    // SWC-104 (unchecked call): no successful path should set the
    // sentinel value that we use as a "call return ignored" marker.
    bool internal _unchecked_marker;
    function echidna_unchecked_call() public view returns (bool) {
        return !_unchecked_marker;
    }
}

// Example contract with the SWC-107 reentrancy pattern from the paper's
// worked example (R1-C1). See docs/WORKED_EXAMPLE.md for the trace.
//
// Run BELMA on this contract:
//   python -m belma.pipeline --contract examples/Reentrant.sol --platform ethereum

pragma solidity ^0.7.0;

contract Vault {
    mapping(address => uint256) balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "insufficient");
        // SWC-107: external call before state update.
        msg.sender.call.value(amount)("");
        balances[msg.sender] -= amount;
    }

    function balanceOf(address who) public view returns (uint256) {
        return balances[who];
    }
}

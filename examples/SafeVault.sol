// Example contract following the checks-effects-interactions pattern.
// BELMA should produce zero SWC-107 findings on this file.

pragma solidity ^0.8.0;

contract SafeVault {
    mapping(address => uint256) private balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        // 1. effects: state update FIRST
        balances[msg.sender] -= amount;
        // 2. interactions: external call AFTER state is consistent
        (bool ok, ) = payable(msg.sender).call{value: amount}("");
        require(ok, "transfer failed");
    }

    function balanceOf(address who) external view returns (uint256) {
        return balances[who];
    }
}

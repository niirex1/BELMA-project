// VulnerableBankContract.sol (Conceptual Representation)
pragma solidity ^0.6.0;

contract VulnerableBank {
    mapping(address => uint) public balances;

    function deposit() public payable {
        require(msg.value > 0);
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint _amount) public {
        require(balances[msg.sender] >= _amount);
        // Vulnerable to reentrancy attack
        (bool sent, ) = msg.sender.call{value: _amount}("");
        require(sent, "Failed to send Ether");
        balances[msg.sender] -= _amount;
    }
}

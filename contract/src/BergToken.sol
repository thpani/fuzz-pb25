// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract BergToken {
    // Constants: Token
    string public constant name = "ProtocolBerg Token";
    string public constant symbol = "BERG";
    string public constant version = "1";

    // Constants: EIP-712 for ERC-2612 Permit
    bytes32 private constant PERMIT_TYPEHASH = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");
    bytes32 public DOMAIN_SEPARATOR;

    // State: Admins
    mapping(address => bool) public admins;
    // State: Circulating tokens
    mapping(address => uint256) public balances;
    uint256 public totalSupply;
    // State: Permits
    mapping(address => uint256) public nonces;
    mapping(address => mapping(address => uint256)) public allowance;
    // State: Staking
    uint256 public totalStakingShares;
    mapping(address => uint256) public stakingShares;

    constructor() {
        admins[msg.sender] = true;

        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes(name)),
            keccak256(bytes(version)),
            block.chainid,
            address(this)
        ));
    }

    modifier onlyAdmin() {
        require(admins[msg.sender], "Not an admin");
        _;
    }

    // Add an admin
    function addAdmin(address _admin) external onlyAdmin {
        admins[_admin] = true;
    }

    // Remove the caller as an admin
    function removeAdmin() external onlyAdmin {
        admins[msg.sender] = false;
    }

    // Mint tokens
    function mint(address to, uint256 amount) external onlyAdmin {
        require(to != address(0), "invalid recipient");
        require(amount > 0, "invalid amount");
        balances[to] += amount;
        totalSupply += amount;
    }

    // Transfer tokens
    function transfer(address to, uint256 amount) external {
        require(to != address(0), "invalid recipient");
        require(amount > 0, "invalid amount");
        require(balances[msg.sender] >= amount, "insufficient balance");

        unchecked { // Safe because of the require above
            balances[msg.sender] -= amount;
        }
        balances[to] += amount;
    }

    // ERC-2612 Permit for signed approvals
    function permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) external
    {
        bytes32 digest =
            keccak256(abi.encodePacked(
                hex"1901",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(PERMIT_TYPEHASH,
                                     owner,
                                     spender,
                                     value,
                                     nonces[owner]++,   // increment nonce!
                                     deadline))
        ));

        require(owner != address(0), "invalid holder");
        // ecrecover returns the address(0) if the signature is invalid
        require(owner == ecrecover(digest, v, r, s), "invalid permit");
        require(block.timestamp <= deadline, "permit expired");
        allowance[owner][spender] = value;
    }

    // Transfer tokens from another address
    function transferFrom(address from, address to, uint256 amount) external {
        require(amount > 0, "invalid amount");
        require(to != address(0), "invalid recipient");
        require(balances[from] >= amount, "insufficient balance");
        require(allowance[from][msg.sender] >= amount, "insufficient allowance");

        unchecked { // Safe because of the require above
            balances[from] -= amount;
            allowance[from][msg.sender] -= amount;
        }
        balances[to] += amount;
    }

    // Stake tokens
    function stake(uint256 amount) external {
        require(amount > 0, "Cannot stake 0");
        require(balances[msg.sender] >= amount, "Insufficient BERG balance");

        // First staker initializes the share price 1:1, after that it is based on the current price
        uint256 totalStakedBERG = balances[address(this)];
        uint256 sharesToMint = totalStakingShares == 0 ? amount : amount * (totalStakingShares / totalStakedBERG);

        unchecked { // Safe because of the require above
             balances[msg.sender] -= amount;
        }
        balances[address(this)] += amount;
        stakingShares[msg.sender] += sharesToMint;
        totalStakingShares += sharesToMint;
    }

    // Unstake tokens
    function unstake(uint256 shares) external {
        require(shares > 0, "Cannot unstake 0");
        require(stakingShares[msg.sender] >= shares, "Insufficient staking shares");
        require(totalStakingShares > 0, "No staking shares"); // Avoid division by zero

        uint256 totalStakedBERG = balances[address(this)];
        uint256 amountToReturn = shares * (totalStakedBERG / totalStakingShares);

        unchecked { // Safe because of the require above
            stakingShares[msg.sender] -= shares;
            totalStakingShares -= shares;
            balances[address(this)] -= amountToReturn;
        }
        balances[msg.sender] += amountToReturn;
    }
}

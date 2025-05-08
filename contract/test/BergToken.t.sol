// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";
import {BergToken} from "../src/BergToken.sol";

contract BergTokenTest is Test {
    BergToken public bergToken;

    address public alice = address(0x1);
    address public bob = address(0x2);
    address public charlie = address(0x3);

    function setUp() public {
        vm.startPrank(alice);
        bergToken = new BergToken();
        vm.stopPrank();
    }

    function testAddAdmin() public {
        vm.startPrank(alice);
        bergToken.addAdmin(bob);
        vm.stopPrank();
        assertTrue(bergToken.admins(bob));
    }

    function testAddAdminByNonAdmin() public {
        vm.startPrank(bob);
        vm.expectRevert("Not an admin");
        bergToken.addAdmin(charlie);
        vm.stopPrank();
    }

    function testRemoveAdmin() public {
        vm.startPrank(alice);
        bergToken.removeAdmin();
        vm.stopPrank();
        assertFalse(bergToken.admins(alice));
    }

    function testRemoveAdminByNonAdmin() public {
        vm.startPrank(bob);
        vm.expectRevert("Not an admin");
        bergToken.removeAdmin();
        vm.stopPrank();
    }

    function testMint() public {
        vm.startPrank(alice);
        bergToken.mint(alice, 100);
        bergToken.mint(bob, 100);
        vm.stopPrank();
        assertEq(bergToken.balances(alice), 100);
        assertEq(bergToken.balances(bob), 100);
        assertEq(bergToken.balances(charlie), 0);
    }

    function testMintToZeroAddress() public {
        vm.startPrank(alice);
        vm.expectRevert("invalid recipient");
        bergToken.mint(address(0), 100);
        vm.stopPrank();
    }

    function testTransfer() public {
        vm.startPrank(alice);
        bergToken.mint(bob, 100);
        vm.stopPrank();

        vm.startPrank(bob);
        bergToken.transfer(charlie, 50);
        vm.stopPrank();

        assertEq(bergToken.balances(alice), 0);
        assertEq(bergToken.balances(bob), 50);
        assertEq(bergToken.balances(charlie), 50);
    }

    function testTransferToZeroAddress() public {
        vm.startPrank(alice);
        bergToken.mint(bob, 100);
        vm.stopPrank();

        vm.startPrank(bob);
        vm.expectRevert("invalid recipient");
        bergToken.transfer(address(0), 50);
        vm.stopPrank();
    }

    function testTransferInsufficientBalance() public {
        vm.startPrank(alice);
        bergToken.mint(bob, 100);
        vm.stopPrank();

        vm.startPrank(bob);
        vm.expectRevert("insufficient balance");
        bergToken.transfer(charlie, 200);
        vm.stopPrank();
    }

    function testPermit() public {
        (address david, uint256 davidPk) = makeAddrAndKey("david");

        vm.startPrank(alice);
        bergToken.mint(david, 100);
        vm.stopPrank();

        uint256 nonce = bergToken.nonces(bob);
        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                bergToken.DOMAIN_SEPARATOR(),
                keccak256(abi.encode(
                    keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"),
                    david,
                    charlie,
                    50,
                    nonce,
                    type(uint256).max
                ))
            )
        );
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(davidPk, digest);

        vm.startPrank(charlie);
        bergToken.permit(david, charlie, 50, type(uint256).max, v, r, s);
        bergToken.transferFrom(david, charlie, 50);
        vm.stopPrank();

        assertEq(bergToken.balances(alice), 0);
        assertEq(bergToken.balances(bob), 0);
        assertEq(bergToken.balances(charlie), 50);
        assertEq(bergToken.balances(david), 50);
    }
}

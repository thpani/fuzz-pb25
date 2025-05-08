#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from eth.abc import VirtualMachineAPI
from eth.db.atomic import AtomicDB
from eth.constants import GENESIS_BLOCK_NUMBER, ZERO_ADDRESS
from eth.chains.base import Chain
from eth.vm.forks.cancun import CancunVM

from eth_keys.datatypes import PrivateKey
from eth_utils.crypto import keccak
from eth_typing import Address


class Account:
    def __init__(self, private_key_bytes: bytes|None = None):
        if private_key_bytes is None:
            private_key_bytes = keccak(os.urandom(32))
        self.private_key = PrivateKey(private_key_bytes)

    def __repr__(self) -> str:
        return self.private_key.public_key.to_address()

    @property
    def address(self) -> Address:
        return Address(self.private_key.public_key.to_canonical_address())


def get_vm() -> VirtualMachineAPI:
    PBFuzzChain = Chain.configure(
        "PBFuzzChain",
        vm_configuration=((GENESIS_BLOCK_NUMBER, CancunVM),)
    )
    chain = PBFuzzChain.from_genesis(AtomicDB(), {
        "coinbase": ZERO_ADDRESS,
        "difficulty": 0,
        "gas_limit": 10**9,
        "timestamp": 0,
    })
    return chain.get_vm()

def main() -> None:
    vm = get_vm()
    account = Account()
    print(f"Account: {account}, nonce: {vm.state.get_nonce(account.address)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # catch keyboard interrupt
        print("Keyboard interrupt, exiting...")
    except Exception as e:
        raise

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import cast

from eth.abc import ComputationAPI, VirtualMachineAPI
from eth.db.atomic import AtomicDB
from eth.constants import GENESIS_BLOCK_NUMBER, ZERO_ADDRESS
from eth.chains.base import Chain
from eth.vm.forks.shanghai.transactions import ShanghaiTransactionBuilder
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


def create_and_execute_tx(vm: VirtualMachineAPI, signer: Account, to: Address, data: bytes = b'', value: int = 0) -> ComputationAPI:
    # create a transaction
    builder = cast(ShanghaiTransactionBuilder, vm.get_transaction_builder())
    tx = builder.new_unsigned_dynamic_fee_transaction(
        chain_id=1,
        nonce=vm.state.get_nonce(signer.address),
        gas=2_000_000,
        max_priority_fee_per_gas=1,
        max_fee_per_gas=875_000_000,
        to=to,
        value=value,
        data=data,
        access_list=[],
    )

    # sign the transaction
    signed_tx = tx.as_signed_transaction(signer.private_key)

    # fund the sender
    vm.state.set_balance(signer.address, 10**18)

    # apply the transaction
    _, computation = vm.apply_transaction(vm.get_header(), signed_tx)

    return computation


def main() -> None:
    vm = get_vm()
    account = Account()
    print(f"Account: {account}, nonce: {vm.state.get_nonce(account.address)}")

    computation = create_and_execute_tx(
        vm,
        signer=account,
        to=Account().address,
        data=b'',
        value=0,
    )
    print(f"Account: {account}, nonce: {vm.state.get_nonce(account.address)}")
    print(f"Computation: {computation}, error: {computation.is_error}, gas: {computation.get_gas_used()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # catch keyboard interrupt
        print("Keyboard interrupt, exiting...")
    except Exception as e:
        raise

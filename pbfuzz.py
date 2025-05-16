#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import random
from typing import cast, Any

import eth
from eth.abc import ComputationAPI, VirtualMachineAPI
from eth.db.atomic import AtomicDB
from eth.constants import CREATE_CONTRACT_ADDRESS, GENESIS_BLOCK_NUMBER, ZERO_ADDRESS
from eth.chains.base import Chain
from eth.vm.forks.shanghai.transactions import ShanghaiTransactionBuilder
from eth.vm.forks.cancun import CancunVM

from eth_abi import abi
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


def create_and_execute_tx(vm: VirtualMachineAPI, signer: Account, to: Address, data: bytes, value: int = 0) -> ComputationAPI:
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

class Contract:
    abi: list[dict[str, Any]]
    bytecode: bytes
    deployedBytecode: bytes
    address: Address

    def __init__(self, abi: list[dict[str, Any]], bytecode: bytes, deployedBytecode: bytes) -> None:
        self.abi = abi
        self.bytecode = bytecode
        self.deployedBytecode = deployedBytecode

def get_contract() -> Contract:
    with open('./contract/out/BergToken.sol/BergToken.json', 'r') as f:
        contract_json = f.read()
        contract = json.loads(contract_json) # type: ignore
        return Contract(
            abi=contract['abi'], # type: ignore
            bytecode=bytes.fromhex(contract['bytecode']['object'][2:]),
            deployedBytecode=bytes.fromhex(contract['deployedBytecode']['object'][2:])
        )

def deploy_contract(vm: VirtualMachineAPI, contract: Contract, account: Account) -> Address:
    # generate a new contract address. this uses the nonce of the account - keep it before the deploy!
    contract_address = Address(eth._utils.address.generate_contract_address(account.address, vm.state.get_nonce(account.address))) # type: ignore

    computation = create_and_execute_tx(
        vm,
        signer=account,
        to=CREATE_CONTRACT_ADDRESS,
        data=contract.bytecode,
        value=0,
    )

    if computation.is_error:
        raise Exception(f"Error deploying contract: {computation.error}")

    return contract_address

def main() -> None:
    vm = get_vm()
    account = Account()
    print(f"Account: {account}, nonce: {vm.state.get_nonce(account.address)}")

    contract = get_contract()
    contract.address = deploy_contract(vm, contract, account)
    assert vm.state.get_code(contract.address) == contract.deployedBytecode, "Deployed bytecode does not match the expected bytecode"
    print(f"Contract deployed at: 0x{contract.address.hex()}")
    print(f"Account: {account}, nonce: {vm.state.get_nonce(account.address)}")

    fuzzed_functions = [ f for f in contract.abi if f['type'] == 'function' ]

    for episode in range(10_000):
        # randomly select a function to fuzz
        function = random.choice(fuzzed_functions)

        # generate random bytestring for arguments
        arg_len = random.randint(0, 32)
        args = random.randbytes(arg_len)

        # encode the function call
        signature = f"{function['name']}({','.join([i['type'] for i in function['inputs']])})"
        calldata = keccak(text=signature)[:4] + args

        computation = create_and_execute_tx(vm, account, contract.address, calldata)

        print(f"{episode:06} {('success' if computation.is_success else 'error'):7} {function['name']} with 0x{calldata.hex()}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # catch keyboard interrupt
        print("Keyboard interrupt, exiting...")
    except Exception as e:
        raise

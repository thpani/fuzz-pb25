#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import random
from typing import cast, Any
import sys

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

ALL_EOA = [ Account() for _ in range(5) ]
DEPLOYER = ALL_EOA[0]
ALL_ADDRESSES = [ a.address for a in ALL_EOA ]

def deploy_contract(vm: VirtualMachineAPI, contract: Contract) -> Address:
    # generate a new contract address. this uses the nonce of the account - keep it before the deploy!
    contract_address = Address(eth._utils.address.generate_contract_address(DEPLOYER.address, vm.state.get_nonce(DEPLOYER.address))) # type: ignore

    computation = create_and_execute_tx(
        vm,
        signer=DEPLOYER,
        to=CREATE_CONTRACT_ADDRESS,
        data=contract.bytecode,
        value=0,
    )

    if computation.is_error:
        raise Exception(f"Error deploying contract: {computation.error}")

    return contract_address

def random_input(t: str) -> Any:
    if t == 'address':
        return random.choice(ALL_ADDRESSES) # TODO: should also cover other possible choices, including address(0) and precompiles
    elif t == 'uint8':
        return random.randint(0, 2**8 - 1)
    elif t == 'uint256':
        return random.randint(0, 2**256 - 1)
    elif t == 'bytes32':
        return random.randbytes(32)
    else:
        raise ValueError(f"Unknown type: {t}")

def decode_error(computation: ComputationAPI) -> str:
    assert computation.is_error, "Computation must be an error to decode it"
    if computation.error.args:
        error_sig = computation.error.args[0][:4]
        if error_sig == keccak(text='Error(string)')[:4]:
            # revert() with a string
            return "Error('{}')".format(abi.decode(['string'], computation.error.args[0][4:])[0])
        elif error_sig == keccak(text='Panic(uint256)')[:4]:
            # panics inserted by the compiler
            error_code = abi.decode(['uint256'], computation.error.args[0][4:])[0]
            if error_code == 0x11:
                return "Panic(arithmetic under/overflow)"
            else:
                return f"Panic(0x{error_code:02x})"
    return f"Error: {computation.error}"

def balanceOf(vm: VirtualMachineAPI, contract: Contract, address: Address) -> int:
    # fetch balance
    computation = create_and_execute_tx(
        vm,
        signer=DEPLOYER,
        to=contract.address,
        data=keccak(text='balances(address)')[:4] + abi.encode(['address'], [address]),
    )
    assert computation.is_success, "balanceOf failed"
    return abi.decode(['uint256'], computation.output)[0]

def totalSupply(vm: VirtualMachineAPI, contract: Contract) -> int:
    # fetch total supply
    computation = create_and_execute_tx(
        vm,
        signer=DEPLOYER,
        to=contract.address,
        data=keccak(text='totalSupply()')[:4],
    )
    assert computation.is_success, "totalSupply failed"
    return abi.decode(['uint256'], computation.output)[0]

def stakingShares(vm: VirtualMachineAPI, contract: Contract, address: Address) -> int:
    # fetch staking shares
    computation = create_and_execute_tx(
        vm,
        signer=DEPLOYER,
        to=contract.address,
        data=keccak(text='stakingShares(address)')[:4] + abi.encode(['address'], [address]),
    )
    assert computation.is_success, "stakingShares failed"
    return abi.decode(['uint256'], computation.output)[0]

def totalStakingShares(vm: VirtualMachineAPI, contract: Contract) -> int:
    # fetch total staking shares
    computation = create_and_execute_tx(
        vm,
        signer=DEPLOYER,
        to=contract.address,
        data=keccak(text='totalStakingShares()')[:4],
    )
    assert computation.is_success, "totalStakingShares failed"
    return abi.decode(['uint256'], computation.output)[0]

def main() -> None:
    vm = get_vm()
    contract = get_contract()
    contract.address = deploy_contract(vm, contract)
    ALL_ADDRESSES.append(contract.address)
    assert(vm.state.get_code(contract.address) == contract.deployedBytecode)
    print(f"Contract deployed at: 0x{contract.address.hex()}")

    fuzzed_functions = [ f for f in contract.abi if f['type'] == 'function' and f['stateMutability'] in ['nonpayable', 'payable'] ]

    for episode in range(10_000):
        # randomly select a function to fuzz
        function = random.choice(fuzzed_functions)

        # abi inputs
        input_types = [ i['type'] for i in function['inputs'] ]
        random_inputs = [ random_input(t) for t in input_types ]

        # randomly select the caller
        caller = random.choice(ALL_EOA)

        # encode the function call
        signature = f"{function['name']}({','.join([i['type'] for i in function['inputs']])})"
        calldata = keccak(text=signature)[:4] + abi.encode(input_types, random_inputs)

        # skip functions that are not callable
        if function['name'] == 'removeAdmin':
            # skip this function, it disables most other functions
            continue

        computation = create_and_execute_tx(vm, caller, contract.address, calldata)

        if computation.is_error:
            print(f"{episode:06} {('success' if computation.is_success else 'error'):7} 0x{caller.address.hex()} {function['name']}({', '.join([f"0x{i.hex()}" if isinstance(i, bytes) else f"{i}" for i in random_inputs])}) => {decode_error(computation)}")
        else:
            print(f"{episode:06} {('success' if computation.is_success else 'error'):7} 0x{caller.address.hex()} {function['name']}({', '.join([f"0x{i.hex()}" if isinstance(i, bytes) else f"{i}" for i in random_inputs])})")

        invariant = sum([balanceOf(vm, contract, a) for a in ALL_ADDRESSES]) == totalSupply(vm, contract)
        if not invariant:
            print(f"INVARIANT FAILED: totalSupply() != sum(balances)")
            print(f"totalSupply: {totalSupply(vm, contract)}")
            print(f"balances: {[balanceOf(vm, contract, a) for a in ALL_ADDRESSES]}")
            sys.exit(1)

        invariant2 = sum([stakingShares(vm, contract, a.address) for a in ALL_EOA]) == totalStakingShares(vm, contract)
        if not invariant2:
            print(f"INVARIANT2 FAILED: totalStakingShares() != sum(stakingShares)")
            print(f"totalStakingShares: {totalStakingShares(vm, contract)}")
            print(f"stakingShares: {[stakingShares(vm, contract, a.address) for a in ALL_EOA]}")
            sys.exit(1)
        
        if episode % 100 == 0:
            sys.stdout.flush()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # catch keyboard interrupt
        print("Keyboard interrupt, exiting...")
    except Exception as e:
        raise

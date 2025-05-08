#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from eth.abc import VirtualMachineAPI
from eth.db.atomic import AtomicDB
from eth.constants import GENESIS_BLOCK_NUMBER, ZERO_ADDRESS
from eth.chains.base import Chain
from eth.vm.forks.cancun import CancunVM

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
    print(f"VM: {vm}, nonce: {vm.state.get_nonce(ZERO_ADDRESS)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # catch keyboard interrupt
        print("Keyboard interrupt, exiting...")
    except Exception as e:
        raise

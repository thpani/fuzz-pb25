# Smart Contract Fuzzing Workshop

This repository contains materials for the workshop ["25-Minute Solidity Fuzzer:
Fuzzing Smarter, Not Harder"][Fuzzing talk] workshop presented at [Protocol Berg
v2][].

The workshop is designed to introduce participants to the basics of smart
contract fuzzing, focusing on how to create a simple fuzzer using Python. The
goal is to provide a practical understanding of fuzzing techniques and their
application in the context of Ethereum smart contracts.

## 🎥 Workshop Recording

[![workshop recording still](https://img.youtube.com/vi/Z7oMWser1JU/maxresdefault.jpg)](https://www.youtube.com/watch?v=Z7oMWser1JU)

## Repository Structure

- `pbfuzz.py`: The main fuzzer implementation.
- `contract/`: Directory containing the example smart contract to be fuzzed.

⚠️ The contract is intentionally vulnerable to demonstrate the fuzzer's capabilities.
Do **not** use this contract in production or with real funds.

## Follow Along

To follow along with the workshop, you can start at the `start_here` tag and
step through the commits to see the development of the fuzzer. Each commit
represents a step in building the fuzzer — though explanations are provided in
the workshop talk, not in the commit messages.

## Requirements

To run the fuzzer, you only need Python 3.x and the `py-evm` package installed.

To build the sample contract, you will need Foundry installed.

A fully-configured environment is available via the devcontainer in this
repository. You can use it with Visual Studio Code or any compatible editor that
supports devcontainers.

[Protocol Berg v2]: https://protocol.berlin/
[Fuzzing talk]: https://blltprf.xyz/blog/25-min-solidity-fuzzer/

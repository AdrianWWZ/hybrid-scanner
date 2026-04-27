# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Final Year Project (FYP) research codebase for detecting vulnerabilities in DeFi smart contracts. The focus is on **price manipulation attacks** using a combination of static analysis (Gigahorse + Datalog taint analysis) and dynamic analysis (Echidna fuzzing). The project is early-stage — most directories (`datasets/`, `harnesses/`, `scripts/`, `contracts/`, `results/`) are currently empty scaffolding.

## Environment Setup

```bash
source .venv/bin/activate  # Python 3.10 venv
```

Key packages already installed: `web3`, `slither-analyzer`, `solc-select`, `pandas`.

Environment variables (`.env`, gitignored):
- `MAINNET_RPC_URL` — Alchemy Ethereum mainnet endpoint
- `ETHERSCAN_API_KEY` — for contract source/ABI lookup

## Scanners

### DeFiTainter (`scanners/defitainter/`)

Static inter-contract taint analysis tool for price manipulation detection. Requires Gigahorse installed as a submodule at `scanners/defitainter/gigahorse-toolchain/`.

```bash
cd scanners/defitainter
python3 defi_tainter.py -bp <ETH|BSC|Avalanche|Polygon|Fantom|Gnosis> \
  -la <logic_address> -sa <storage_address> \
  -fs <function_signature_hex> -bn <block_number>
```

- `-la` / `-sa` split: proxy contracts store logic at one address and data at another (for `DELEGATECALL` patterns)
- The tool auto-downloads bytecode from hardcoded RPC URLs, decompiles via Gigahorse, then runs taint propagation across the cross-contract call graph
- Outputs `True`/`False` to stdout indicating whether a price manipulation vulnerability was detected
- Intermediate decompilation artifacts land in `gigahorse-toolchain/.temp/<address>/out/*.csv`

### Gigahorse (`scanners/gigahorse/`)

EVM bytecode lifter — decompiles `.hex` contract files to three-address code (TAC), then runs Datalog (Souffle) client analyses.

**Prerequisites** (non-Python):
- Souffle 2.3 or 2.4.1
- Boost libraries (`apt install libboost-all-dev`)
- Z3 (`apt install libz3-dev`)
- Build Souffle custom functors: `cd souffle-addon && make WORD_SIZE=$(souffle --version | sed -n 3p | cut -c12,13)`

```bash
# Single contract
cd scanners/gigahorse
./gigahorse.py examples/long_running.hex

# With a client analysis (Datalog or Python)
./gigahorse.py -C clients/price_manipulation_analysis.dl <contracts_dir>

# Tests
pytest test_gigahorse.py
```

Results go to `.temp/<contract_name>/out/` (CSV relation files) and `results.json`.

### Echidna (`scanners/echidna/`) and FlashDefier (`scanners/flashdefier/`)

Currently empty — intended for Echidna fuzz testing harnesses and flash loan vulnerability detection respectively.

## Architecture: How DeFiTainter Works

1. **Cross-contract call graph construction** (`construct_cross_contract_call_graph`): Starting from an entry point contract+function, recursively resolves external calls (handling `DELEGATECALL`, storage-stored callees, proxy patterns) to build a graph of `Contract` objects keyed by `caller_callsite_logicAddr_funcSign`.

2. **Gigahorse decompilation**: Each contract's bytecode is decompiled via `gigahorse-toolchain/gigahorse.py -C clients/price_manipulation_analysis.dl`. This produces CSV facts under `.temp/<addr>/out/` including taint flow relations (`FLA_TaintedVarToSensitiveVar`, `FLA_TaintedFuncRet`, `FLA_TaintedCallArg`, etc.) and spread relations (`FLA_Spread_*`).

3. **Taint reachability analysis** (`detect`): Computes program points (PPs) near taint sources (price oracle reads) and sinks (sensitive variable writes), then checks reachability via a `transfer` function that propagates taint across call boundaries using the spread CSV relations.

## Results Layout

```
results/
  static/    # Output from Gigahorse/DeFiTainter static analyses
  dynamic/   # Output from Echidna fuzzing runs
  combined/  # Aggregated/merged results
```

## Datasets

`scanners/defitainter/dataset/`:
- `incident.csv` — 23 DeFi protocols exploited in real-world price manipulation attacks
- `high_value.csv` — 1,195 high-value DeFi protocols

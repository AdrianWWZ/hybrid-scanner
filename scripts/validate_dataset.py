#!/usr/bin/env python3
"""Check every row of incident.csv: does the (logic_addr, block_number) actually have bytecode?"""

import csv
import os
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

INCIDENT_CSV = PROJECT_ROOT / "scanners" / "defitainter" / "dataset" / "incident.csv"

PLATFORM_TO_ENV = {
    "ETH": "ETH_RPC_URL",
    "BSC": "BSC_RPC_URL",
    "Polygon": "POLYGON_RPC_URL",
    "Avalanche": "AVAX_RPC_URL",
    "Solana": "SOLANA_RPC_URL",
    "Fantom": "FANTOM_RPC_URL",
    "Gnosis": "GNOSIS_RPC_URL",
}

def main():
    with open(INCIDENT_CSV) as f:
        rows = list(csv.DictReader(f))

    print(f"{'idx':>3}  {'project':20s}  {'platform':10s}  {'verdict':12s}  size")
    print("-" * 70)

    for idx, row in enumerate(rows, start=1):
        project = row["expolited_project"]
        platform = row["platform"]
        addr = row["logic_addr"]
        block = int(row["block_number"])

        env_var = PLATFORM_TO_ENV.get(platform)
        if not env_var:
            print(f"{idx:3d}  {project:20s}  {platform:10s}  UNKNOWN_PLAT")
            continue

        rpc_url = os.getenv(env_var)
        if not rpc_url:
            print(f"{idx:3d}  {project:20s}  {platform:10s}  NO_RPC")
            continue

        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            code = w3.eth.get_code(Web3.to_checksum_address(addr), block_identifier=block)
            size = len(code)
            if size <= 2:  # 0x or empty
                verdict = "EMPTY"
            elif size < 100:
                verdict = "TINY"
            else:
                verdict = "OK"
            print(f"{idx:3d}  {project:20s}  {platform:10s}  {verdict:12s}  {size}")
        except Exception as e:
            err = str(e)[:40]
            print(f"{idx:3d}  {project:20s}  {platform:10s}  ERROR        {err}")

if __name__ == "__main__":
    main()
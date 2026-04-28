#!/usr/bin/env python3
"""
Sweep DeFiTainter across every row of dataset/incident.csv.
Records True/False/error and runtime per incident.
"""

import csv
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFITAINTER_DIR = PROJECT_ROOT / "scanners" / "defitainter"
INCIDENT_CSV = DEFITAINTER_DIR / "dataset" / "incident.csv"
GIGAHORSE_DIR = DEFITAINTER_DIR / "gigahorse-toolchain"
TEMP_DIR = GIGAHORSE_DIR / ".temp"
CONTRACTS_DIR = GIGAHORSE_DIR / "contracts"
RESULTS_DIR = PROJECT_ROOT / "results" / "static"
LOG_DIR = RESULTS_DIR / "sweep_logs"

# Per-incident timeout (in seconds). Generous enough for cross-contract chains.
PER_INCIDENT_TIMEOUT = 600  # 10 minutes


def clear_state():
    """Clear bytecode cache and analysis temp, but PRESERVE Souffle cache/."""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    if CONTRACTS_DIR.exists():
        shutil.rmtree(CONTRACTS_DIR)
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)


def run_one(row, log_file):
    """Run DeFiTainter on a single incident. Return (verdict, seconds)."""
    cmd = [
        "python3", "defi_tainter.py",
        "-bp", row["platform"],
        "-la", row["logic_addr"],
        "-sa", row["storage_addr"],
        "-fs", row["func_sign"],
        "-bn", row["block_number"],
    ]
    start = time.time()
    try:
        with open(log_file, "w") as f:
            proc = subprocess.run(
                cmd,
                cwd=DEFITAINTER_DIR,
                stdout=f,
                stderr=subprocess.STDOUT,
                timeout=PER_INCIDENT_TIMEOUT,
            )
        elapsed = time.time() - start
        # DeFiTainter prints the final verdict ("True" / "False") as its last line
        with open(log_file) as f:
            lines = [line.strip() for line in f if line.strip()]
        verdict = lines[-1] if lines else "EMPTY"
        if verdict not in ("True", "False"):
            verdict = f"UNKNOWN: {verdict[:60]}"
        return verdict, elapsed
    except subprocess.TimeoutExpired:
        return "TIMEOUT", PER_INCIDENT_TIMEOUT
    except Exception as e:
        return f"ERROR: {type(e).__name__}", time.time() - start


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = RESULTS_DIR / f"sweep_summary_{timestamp}.csv"

    with open(INCIDENT_CSV) as f:
        rows = list(csv.DictReader(f))

    print(f"Running DeFiTainter on {len(rows)} incidents.")
    print(f"Per-incident timeout: {PER_INCIDENT_TIMEOUT}s")
    print(f"Logs: {LOG_DIR}")
    print(f"Summary: {summary_path}")
    print("-" * 70)

    summary_fields = ["idx", "project", "logic_addr", "verdict", "seconds", "log_file"]
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()

        for idx, row in enumerate(rows, start=1):
            project = row["expolited_project"]  # note: typo is in the CSV
            short_addr = row["logic_addr"][:10]
            print(f"[{idx:2d}/{len(rows)}] {project:20s} {short_addr}...", end=" ", flush=True)

            clear_state()
            log_file = LOG_DIR / f"{idx:02d}_{project.replace(' ', '_')}.log"
            verdict, elapsed = run_one(row, log_file)

            print(f"-> {verdict:8s} ({elapsed:.1f}s)")
            writer.writerow({
                "idx": idx,
                "project": project,
                "logic_addr": row["logic_addr"],
                "verdict": verdict,
                "seconds": f"{elapsed:.1f}",
                "log_file": log_file.name,
            })
            f.flush()  # write incrementally so we don't lose data on crash

    print("-" * 70)
    print(f"Done. Summary: {summary_path}")


if __name__ == "__main__":
    main()
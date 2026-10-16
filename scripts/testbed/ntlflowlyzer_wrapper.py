#!/usr/bin/env python3
"""
XFlowLyzer Parity Experiment - NTLFlowLyzer Comparator Wrapper
--------------------------------------------------------------
Extracts flow features from sequential PCAP captures using NTLFlowLyzer.
Dynamically constructs config.json per capture and invokes the CLI engine.

Usage: sudo python3 scripts/testbed/ntlflowlyzer_wrapper.py
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import tempfile
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NTL_DIR = "/opt/NTLFlowLyzer"
NTL_BIN = "ntlflowlyzer"
DATA_RAW = os.path.join(BASE_DIR, "data/raw")
DATA_INTERIM = os.path.join(BASE_DIR, "data/interim/NTL_RAW")
EXPERIMENT_ORDER = ["PCAPv6", "PCAP"]


def process_pcap_dir(pcap_dir, category, smoke_test=False):
    """Processes all PCAP files within the designated directory using NTLFlowLyzer."""
    rel_path = os.path.relpath(pcap_dir, os.path.join(DATA_RAW, category))
    output_dir = os.path.normpath(os.path.join(DATA_INTERIM, category, rel_path))
    os.makedirs(output_dir, exist_ok=True)

    pcaps = sorted(glob.glob(os.path.join(pcap_dir, "*.pcap*")))
    if not pcaps:
        return

    if smoke_test:
        pcaps = [pcaps[0]]

    metrics_csv = os.path.join(output_dir, "resource_metrics.csv")
    experiment_name = f"{category}/{rel_path}"

    print(f"\n[*] Processing NTLFlowLyzer: {experiment_name}")

    total_flows = 0
    t0 = time.time()

    for pcap in pcaps:
        base_name = os.path.basename(pcap)
        out_csv = os.path.join(output_dir, f"{base_name}.csv")

        config = {
            "pcap_path": pcap,
            "export_path": out_csv,
            "format": "csv",
            "features": "all",
            "capturer_updating_flows_min_value": 100,
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            cfg_path = f.name
            json.dump(config, f, indent=4)

        try:
            cmd = [NTL_BIN, "--config", cfg_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=600)

            tmp_out = out_csv
            if result.returncode != 0 and not os.path.exists(tmp_out):
                # Fallback: attempt execution as Python module
                cmd_fb = ["python3", "-m", "ntlflowlyzer", "--config", cfg_path]
                subprocess.run(cmd_fb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=600)

            if os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 0:
                with open(tmp_out, "r") as fp:
                    lines = sum(1 for _ in fp) - 1
                total_flows += max(0, lines)
                print(f"  [+] {base_name}: {lines} flows generated")
            else:
                print(f"  [-] {base_name}: No output generated")

        except Exception as e:
            print(f"  [-] ERROR on {base_name}: {e}")
        finally:
            if os.path.exists(cfg_path):
                os.remove(cfg_path)

    elapsed = time.time() - t0
    summary = {
        "tool": "NTLFlowLyzer",
        "category": category,
        "rel_path": rel_path,
        "total_flows": total_flows,
        "elapsed_seconds": elapsed,
        "timestamp": time.time(),
    }
    with open(os.path.join(output_dir, "extraction_summary.json"), "w") as f:
        json.dump(summary, f, indent=4)

    print(f"[+] DONE: {total_flows} flows extracted in {elapsed:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="NTLFlowLyzer Extraction Wrapper")
    parser.add_argument("--smoke-test", action="store_true", help="Run smoke test on first PCAP only")
    parser.add_argument("--output", type=str, help="Override interim output directory")
    args = parser.parse_args()

    if args.output:
        global DATA_INTERIM
        DATA_INTERIM = os.path.abspath(args.output)

    print(f"=== NTLFlowLyzer Parity Extraction Wrapper [Output: {DATA_INTERIM}] ===")

    for category in EXPERIMENT_ORDER:
        category_path = os.path.join(DATA_RAW, category)
        if not os.path.exists(category_path):
            continue

        for root, dirs, files in os.walk(category_path):
            if any(f.endswith(".pcap") or f.endswith(".pcapng") for f in files):
                process_pcap_dir(root, category, smoke_test=args.smoke_test)


if __name__ == "__main__":
    main()

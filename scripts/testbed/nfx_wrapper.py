#!/usr/bin/env python3
"""
XFlowLyzer Parity Experiment - NetFeatureXtract (NFX) Comparator Wrapper
------------------------------------------------------------------------
Executes extraction of flow features using NetFeatureXtract (XFAST eBPF).
Applies virtual network pair (veth) and tcpreplay ingestion.
"""

import argparse
import glob
import json
import os
import re
import signal
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NFX_DIR = "/opt/NetFeatureXtract"
if not os.path.exists(NFX_DIR):
    NFX_DIR = "/opt/XFAST/ebpf"

NFX_BIN = os.path.join(NFX_DIR, "xdp_user")
INTERIM_DIR = os.path.join(BASE_DIR, "data/interim/NFX_RAW")
PCAP_DIR = os.path.join(BASE_DIR, "data/raw")


def _sanitize_nfx_csv(raw_path, clean_path):
    """Parses raw text outputs from NFX into standardized CSV records."""
    if not os.path.exists(raw_path):
        return
    with open(raw_path, "r") as f:
        content = f.read()
    pattern = r"Flow:\s+([\d\.]+):(\d+)\s+->\s+([\d\.]+):(\d+)\s+\(IPv4, Proto:\s+(\d+)\)\s+Packets:\s+(\d+)\s+Bytes:\s+(\d+)"
    matches = re.findall(pattern, content)
    with open(clean_path, "w") as f:
        f.write("src_ip,src_port,dst_ip,dst_port,protocol,packets,bytes\n")
        for m in matches:
            f.write(f"{m[0]},{m[1]},{m[2]},{m[3]},{m[4]},{m[5]},{m[6]}\n")


def run_nfx_extraction(smoke_test=False, max_events=0, skip_labeling=False, skip_ipv6=False):
    """Executes NFX extraction across available PCAP datasets."""
    global INTERIM_DIR
    if not os.path.exists(NFX_BIN):
        print(f"[-] ERROR: NFX binary not found at: {NFX_BIN}")
        return

    print("================================================================================")
    print("  NetFeatureXtract (NFX) Extraction Harness                                     ")
    print("================================================================================")

    categories = ["PCAPv6", "PCAP"]
    if skip_ipv6:
        categories = ["PCAP"]

    for category in categories:
        cat_dir = os.path.join(PCAP_DIR, category)
        if not os.path.exists(cat_dir):
            continue

        pcaps = sorted(glob.glob(os.path.join(cat_dir, "**", "*.pcap*"), recursive=True))
        if smoke_test and pcaps:
            pcaps = [pcaps[0]]

        for pcap in pcaps:
            rel = os.path.relpath(pcap, PCAP_DIR)
            out_target_dir = os.path.join(INTERIM_DIR, os.path.dirname(rel))
            os.makedirs(out_target_dir, exist_ok=True)

            base_name = os.path.basename(pcap)
            raw_out = os.path.join(out_target_dir, f"{base_name}.raw.txt")
            clean_out = os.path.join(out_target_dir, f"{base_name}.csv")

            print(f"[*] Processing: {rel}")
            subprocess.run("ip link delete veth0 2>/dev/null || true", shell=True)
            subprocess.run("ip link add veth0 type veth peer name veth1", shell=True, check=True)
            subprocess.run("ip link set veth0 up", shell=True, check=True)
            subprocess.run("ip link set veth1 up", shell=True, check=True)

            t0 = time.time()
            try:
                with open(raw_out, "w") as f_raw:
                    proc_nfx = subprocess.Popen(
                        [NFX_BIN, "veth1"],
                        stdout=f_raw,
                        stderr=subprocess.STDOUT,
                        cwd=NFX_DIR,
                        preexec_fn=os.setsid
                    )
                    time.sleep(2)

                    cmd_replay = f"tcpreplay --topspeed -i veth0 {pcap}"
                    subprocess.run(cmd_replay, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(2)

                    os.killpg(os.getpgid(proc_nfx.pid), signal.SIGINT)
                    proc_nfx.wait(timeout=10)

                _sanitize_nfx_csv(raw_out, clean_out)
                elapsed = time.time() - t0
                print(f"  [+] Completed in {elapsed:.2f}s")
            except Exception as e:
                print(f"  [-] ERROR on {rel}: {e}")
            finally:
                subprocess.run("ip link delete veth0 2>/dev/null || true", shell=True)


def main():
    parser = argparse.ArgumentParser(description="NetFeatureXtract Parity Wrapper")
    parser.add_argument("--smoke-test", action="store_true", help="Run smoke test on first PCAP only")
    parser.add_argument("--output", type=str, help="Override output directory")
    args = parser.parse_args()

    if args.output:
        global INTERIM_DIR
        INTERIM_DIR = os.path.abspath(args.output)

    run_nfx_extraction(smoke_test=args.smoke_test)


if __name__ == "__main__":
    main()

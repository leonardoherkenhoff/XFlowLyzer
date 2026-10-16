#!/usr/bin/env python3
"""
XFlowLyzer Research Pipeline - Group 1: Native In-Kernel Offline PCAP Ingestion Benchmark
----------------------------------------------------------------------------------------
Benchmark harness evaluating offline PCAP processing performance:
1. XFlowLyzer Native Ingestion: mmap + bpf_prog_test_run_opts (in-kernel XDP)
2. RustiFlow: User-space PCAP ingestion mode
"""

import argparse
import os
import re
import statistics
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XFLOWLYZER_BIN = os.path.join(BASE_DIR, "build/xflowlyzer")
RUSTIFLOW_BIN = os.environ.get("RUSTIFLOW_BIN", "/usr/local/bin/rustiflow")


def run_command(cmd, timeout=600):
    """Executes a command and returns returncode, stdout, stderr, and elapsed time."""
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        t1 = time.time()
        return proc.returncode, proc.stdout, proc.stderr, (t1 - t0)
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT", timeout
    except Exception as e:
        return -1, "", str(e), 0.0


def parse_xflowlyzer_output(stderr_text):
    """Parses PPS and packet count from XFlowLyzer output."""
    pps = None
    pkts = None
    pps_match = re.search(r"Speed\s*:\s*([\d\.]+)\s*PPS", stderr_text)
    if pps_match:
        pps = float(pps_match.group(1))
    pkts_match = re.search(r"(\d+)\s+packets injected", stderr_text)
    if pkts_match:
        pkts = int(pkts_match.group(1))
    return pps, pkts


def benchmark_xflowlyzer(pcap_path, runs=10):
    """Runs XFlowLyzer native ingestion benchmark across N repetitions."""
    if not os.path.isfile(XFLOWLYZER_BIN):
        print(f"[-] ERROR: XFlowLyzer binary not found at {XFLOWLYZER_BIN}. Run 'make' first.")
        return None

    print(f"\n[*] Benchmarking XFlowLyzer Native Ingestion (N={runs}): {pcap_path}")
    durations = []
    pps_list = []
    pkts_list = []

    for r in range(1, runs + 1):
        # Drop kernel page caches before each run
        subprocess.run("sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null", shell=True)
        time.sleep(1)

        cmd = f"sudo {XFLOWLYZER_BIN} --pcap {pcap_path} > /dev/null"
        rc, out, err, elapsed = run_command(cmd)

        if rc != 0:
            print(f"[-] Run {r}/{runs} failed with code {rc}: {err.strip()[:200]}")
            continue

        pps, pkts = parse_xflowlyzer_output(err)
        durations.append(elapsed)
        if pps:
            pps_list.append(pps)
        if pkts:
            pkts_list.append(pkts)

        print(f"  Run {r:2d}/{runs}: Time = {elapsed:.2f}s | Speed = {pps if pps else 0.0:.2f} PPS | Packets = {pkts if pkts else 0}")

    if not durations:
        return None

    mean_time = statistics.mean(durations)
    std_time = statistics.stdev(durations) if len(durations) > 1 else 0.0
    mean_pps = statistics.mean(pps_list) if pps_list else 0.0
    std_pps = statistics.stdev(pps_list) if len(pps_list) > 1 else 0.0

    print(f"\n[+] XFlowLyzer Summary (N={len(durations)}):")
    print(f"    Execution Time : {mean_time:.3f}s ± {std_time:.3f}s")
    print(f"    Ingestion Rate : {mean_pps:.2f} PPS ± {std_pps:.2f} PPS")

    return {
        "engine": "XFlowLyzer",
        "mean_time": mean_time,
        "std_time": std_time,
        "mean_pps": mean_pps,
        "std_pps": std_pps,
        "packets": pkts_list[0] if pkts_list else 0
    }


def benchmark_rustiflow(pcap_path, runs=10):
    """Runs RustiFlow offline ingestion benchmark across N repetitions."""
    if not os.path.isfile(RUSTIFLOW_BIN) and subprocess.run(f"which {RUSTIFLOW_BIN}", shell=True).returncode != 0:
        print(f"[!] WARNING: RustiFlow binary not found at {RUSTIFLOW_BIN}. Skipping RustiFlow.")
        return None

    print(f"\n[*] Benchmarking RustiFlow Ingestion (N={runs}): {pcap_path}")
    durations = []

    for r in range(1, runs + 1):
        subprocess.run("sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null", shell=True)
        time.sleep(1)

        cmd = f"sudo {RUSTIFLOW_BIN} -f rustiflow -o print pcap {pcap_path} > /dev/null"
        rc, out, err, elapsed = run_command(cmd)

        if rc != 0:
            print(f"[-] Run {r}/{runs} failed with code {rc}: {err.strip()[:200]}")
            continue

        durations.append(elapsed)
        print(f"  Run {r:2d}/{runs}: Time = {elapsed:.2f}s")

    if not durations:
        return None

    mean_time = statistics.mean(durations)
    std_time = statistics.stdev(durations) if len(durations) > 1 else 0.0

    print(f"\n[+] RustiFlow Summary (N={len(durations)}):")
    print(f"    Execution Time : {mean_time:.3f}s ± {std_time:.3f}s")

    return {
        "engine": "RustiFlow",
        "mean_time": mean_time,
        "std_time": std_time
    }


def main():
    parser = argparse.ArgumentParser(description="XFlowLyzer Native In-Kernel Offline PCAP Benchmark (Group 1)")
    parser.add_argument("--pcap", type=str, required=True, help="Path to input PCAP file")
    parser.add_argument("--runs", type=int, default=10, help="Number of benchmark repetitions (default: 10)")
    parser.add_argument("--skip-rustiflow", action="store_true", help="Skip RustiFlow comparison")
    args = parser.parse_args()

    if not os.path.isfile(args.pcap):
        print(f"[-] ERROR: PCAP file not found: {args.pcap}")
        sys.exit(1)

    print("================================================================================")
    print("  XFlowLyzer Empirical Protocol: Group 1 - Native Offline PCAP Ingestion        ")
    print("================================================================================")
    print(f"Target PCAP : {args.pcap}")
    print(f"Repetitions : N = {args.runs}")

    res_xflow = benchmark_xflowlyzer(args.pcap, runs=args.runs)
    res_rustiflow = None
    if not args.skip_rustiflow:
        res_rustiflow = benchmark_rustiflow(args.pcap, runs=args.runs)

    print("\n" + "=" * 80)
    print("FINAL COMPARATIVE RESULTS (GROUP 1)")
    print("=" * 80)
    if res_xflow:
        print(f"XFlowLyzer : {res_xflow['mean_time']:.3f}s ± {res_xflow['std_time']:.3f}s | {res_xflow['mean_pps']:.2f} PPS ± {res_xflow['std_pps']:.2f} PPS")
    if res_rustiflow:
        print(f"RustiFlow  : {res_rustiflow['mean_time']:.3f}s ± {res_rustiflow['std_time']:.3f}s")
        if res_xflow and res_rustiflow['mean_time'] > 0:
            speedup = res_rustiflow['mean_time'] / res_xflow['mean_time']
            print(f"Speedup    : {speedup:.2f}x faster with XFlowLyzer in-kernel engine")
    print("=" * 80)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
XFlowLyzer Research Pipeline - Group 2: Line-Rate Telemetry Retention Benchmark
-------------------------------------------------------------------------------
Evaluates telemetry retention, sustained PPS throughput, and memory stationarity
under continuous line-rate packet injection (CICDDoS2019 / CIC-IDS-2017).

Measures:
1. Telemetry Ingress Events vs Dropped Events (Kernel & User-space).
2. Retention Rate: R = (Events / (Events + Drops)) * 100.0%.
3. Memory Footprint: Peak Resident Set Size (RSS) across N=10 repetitions.
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


def run_command(cmd, timeout=600):
    """Executes a shell command and returns rc, stdout, stderr, elapsed time."""
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        t1 = time.time()
        return proc.returncode, proc.stdout, proc.stderr, (t1 - t0)
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT", timeout
    except Exception as e:
        return -1, "", str(e), 0.0


def benchmark_linerate_retention(iface_or_pcap, is_pcap=False, runs=10):
    """Executes N runs of line-rate telemetry retention evaluation."""
    if not os.path.isfile(XFLOWLYZER_BIN):
        print(f"[-] ERROR: XFlowLyzer binary not found at {XFLOWLYZER_BIN}. Run 'make' first.")
        return None

    print(f"\n[*] Evaluating Line-Rate Telemetry Retention (N={runs}): {iface_or_pcap}")
    retention_rates = []
    pps_rates = []
    rss_peaks = []

    for r in range(1, runs + 1):
        subprocess.run("sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null", shell=True)
        time.sleep(1)

        log_file = f"/tmp/xflow_retention_run_{r}.log"
        if os.path.exists(log_file):
            os.remove(log_file)

        if is_pcap:
            cmd = f"/usr/bin/time -v sudo {XFLOWLYZER_BIN} --pcap {iface_or_pcap} > /dev/null 2> {log_file}"
        else:
            cmd = f"/usr/bin/time -v sudo {XFLOWLYZER_BIN} {iface_or_pcap} > /dev/null 2> {log_file}"

        rc, out, err, elapsed = run_command(cmd)

        # Parse metrics from log file
        events = 0
        drops = 0
        pps = 0.0
        rss_kb = 0

        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                content = f.read()
                m_ev = re.search(r"Kernel-Space Ingress Events\s*:\s*(\d+)", content)
                if m_ev:
                    events = int(m_ev.group(1))
                m_dr = re.search(r"Kernel-Space Telemetry Drops\s*:\s*(\d+)", content)
                if m_dr:
                    drops = int(m_dr.group(1))
                m_pps = re.search(r"Speed\s*:\s*([\d\.]+)\s*PPS", content)
                if m_pps:
                    pps = float(m_pps.group(1))
                m_rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", content)
                if m_rss:
                    rss_kb = int(m_rss.group(1))

        total_frames = events + drops
        retention = (events / total_frames * 100.0) if total_frames > 0 else 100.0
        rss_mb = rss_kb / 1024.0

        retention_rates.append(retention)
        if pps > 0:
            pps_rates.append(pps)
        if rss_mb > 0:
            rss_peaks.append(rss_mb)

        print(f"  Run {r:2d}/{runs}: Events = {events:,} | Drops = {drops:,} | Retention = {retention:.4f}% | Speed = {pps:.2f} PPS | Peak RSS = {rss_mb:.2f} MB")

    if not retention_rates:
        return None

    mean_ret = statistics.mean(retention_rates)
    std_ret = statistics.stdev(retention_rates) if len(retention_rates) > 1 else 0.0
    mean_pps = statistics.mean(pps_rates) if pps_rates else 0.0
    std_pps = statistics.stdev(pps_rates) if len(pps_rates) > 1 else 0.0
    mean_rss = statistics.mean(rss_peaks) if rss_peaks else 0.0
    std_rss = statistics.stdev(rss_peaks) if len(rss_peaks) > 1 else 0.0

    print("\n" + "=" * 80)
    print("FINAL STATISTICAL SUMMARY: GROUP 2 LINE-RATE RETENTION")
    print("=" * 80)
    print(f"Telemetry Retention Rate : {mean_ret:.4f}% ± {std_ret:.4f}%")
    print(f"Sustained Processing Rate: {mean_pps:.2f} PPS ± {std_pps:.2f} PPS")
    print(f"Peak Resident Set Size   : {mean_rss:.2f} MB ± {std_rss:.2f} MB")
    print("=" * 80)

    return {
        "mean_retention": mean_ret,
        "std_retention": std_ret,
        "mean_pps": mean_pps,
        "std_pps": std_pps,
        "mean_rss": mean_rss,
        "std_rss": std_rss
    }


def main():
    parser = argparse.ArgumentParser(description="XFlowLyzer Group 2 Line-Rate Telemetry Retention Benchmark")
    parser.add_argument("--target", type=str, required=True, help="Network interface name (e.g. eth0) or PCAP file path")
    parser.add_argument("--pcap", action="store_true", help="Treat target as offline PCAP capture")
    parser.add_argument("--runs", type=int, default=10, help="Number of repetitions (default: 10)")
    args = parser.parse_args()

    benchmark_linerate_retention(args.target, is_pcap=args.pcap, runs=args.runs)


if __name__ == "__main__":
    main()

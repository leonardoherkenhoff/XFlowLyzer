#!/usr/bin/env python3
"""
XFlowLyzer Research Pipeline - Group 3: Live In-Kernel Pktgen Multi-Core Stress Benchmark
----------------------------------------------------------------------------------------
Evaluates maximum packet processing throughput under extreme multi-threaded in-kernel
synthetic injection via Linux pktgen across 48 physical SMP cores:
1. XFlowLyzer: Native driver-mode XDP hook (XDP_DRV)
2. RustiFlow: Linux Traffic Control (TC) sched_cls hook
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


def setup_veth(peer_ns="rustiflow-peer", if_target="rustiflow-t0", if_peer="rustiflow-p0"):
    """Configures isolated network namespace and veth pair with all hardware offloads disabled."""
    print("[*] Provisioning isolated network namespace and veth pair...")
    subprocess.run(f"sudo ip netns del {peer_ns} 2>/dev/null || true", shell=True)
    subprocess.run(f"sudo ip link del {if_target} 2>/dev/null || true", shell=True)

    subprocess.run(f"sudo ip netns add {peer_ns}", shell=True, check=True)
    subprocess.run(f"sudo ip link add {if_target} type veth peer name {if_peer}", shell=True, check=True)
    subprocess.run(f"sudo ip link set {if_peer} netns {peer_ns}", shell=True, check=True)
    subprocess.run(f"sudo ip link set {if_target} up", shell=True, check=True)
    subprocess.run(f"sudo ip netns exec {peer_ns} ip link set lo up", shell=True, check=True)
    subprocess.run(f"sudo ip netns exec {peer_ns} ip link set {if_peer} up", shell=True, check=True)

    # Disable all hardware offloads to expose raw packet processing limits
    offload_cmd = "rx off tx off tso off gro off gso off lro off"
    subprocess.run(f"sudo ethtool -K {if_target} {offload_cmd} 2>/dev/null || true", shell=True)
    subprocess.run(f"sudo ip netns exec {peer_ns} ethtool -K {if_peer} {offload_cmd} 2>/dev/null || true", shell=True)

    mac_cmd = f"ip link show {if_target} | grep link/ether | awk '{{print $2}}'"
    mac = subprocess.check_output(mac_cmd, shell=True).decode().strip()
    return mac


def get_rx_stats(iface="rustiflow-t0"):
    """Extracts RX packet and drop counts from kernel interface statistics."""
    try:
        res = subprocess.check_output(f"ip -s -s link show {iface}", shell=True).decode()
        lines = res.strip().split("\n")
        for idx, line in enumerate(lines):
            if "RX:" in line and "packets" in line and "dropped" in line:
                parts = lines[idx + 1].split()
                return int(parts[1]), int(parts[3])
    except Exception:
        pass
    return 0, 0


def create_pktgen_script(dst_mac, delay=0, count=5000000, pkt_size=60, if_peer="rustiflow-p0", cores=48):
    """Generates the pktgen configuration script binding threads to physical CPU cores."""
    script_lines = [
        "modprobe pktgen",
        "for f in /proc/net/pktgen/kpktgend_*; do echo 'rem_device_all' > $f 2>/dev/null; done"
    ]
    for i in range(cores):
        script_lines.extend([
            f"echo 'add_device {if_peer}@{i}' > /proc/net/pktgen/kpktgend_{i} 2>/dev/null",
            f"dev='/proc/net/pktgen/{if_peer}@{i}'",
            f"[ ! -f \"$dev\" ] && dev='/proc/net/pktgen/{if_peer}'",
            "echo 'flag QUEUE_MAP_CPU' > $dev 2>/dev/null",
            f"echo 'queue_map_min {i}' > $dev 2>/dev/null",
            f"echo 'queue_map_max {i}' > $dev 2>/dev/null",
            f"echo 'count {count}' > $dev 2>/dev/null",
            "echo 'clone_skb 1000' > $dev 2>/dev/null",
            f"echo 'pkt_size {pkt_size}' > $dev 2>/dev/null",
            f"echo 'delay {delay}' > $dev 2>/dev/null",
            f"echo 'dst_mac {dst_mac}' > $dev 2>/dev/null",
            "echo 'dst 192.168.100.1' > $dev 2>/dev/null"
        ])

    script_path = "/tmp/setup_pktgen.sh"
    with open(script_path, "w") as f:
        f.write("\n".join(script_lines) + "\n")
    return script_path


def run_pktgen(duration=10, peer_ns="rustiflow-peer"):
    """Starts pktgen, waits for duration, then stops and gathers injection rate."""
    subprocess.run(f"sudo ip netns exec {peer_ns} bash /tmp/setup_pktgen.sh", shell=True)
    subprocess.Popen(f"sudo ip netns exec {peer_ns} bash -c 'echo start > /proc/net/pktgen/pgctrl'", shell=True)
    time.sleep(duration)
    subprocess.run(f"sudo ip netns exec {peer_ns} bash -c 'echo stop > /proc/net/pktgen/pgctrl'", shell=True)
    total_pps = 0
    try:
        res = subprocess.check_output(f"sudo ip netns exec {peer_ns} bash -c 'cat /proc/net/pktgen/rustiflow-p0*'", shell=True).decode()
        pps_matches = re.findall(r"(\d+)pps", res)
        if pps_matches:
            total_pps = sum(int(p) for p in pps_matches)
            print(f"    [PktGen] Injected Rate: {total_pps:,} PPS across {len(pps_matches)} threads")
    except Exception:
        pass
    return total_pps


def benchmark_xflowlyzer_pktgen(dst_mac, duration=10, runs=10):
    """Evaluates XFlowLyzer under pktgen high-rate stress across N runs."""
    print(f"\n[*] Evaluating XFlowLyzer (Native XDP Hook) under Pktgen Stress (N={runs})...")
    results = []

    for r in range(1, runs + 1):
        create_pktgen_script(dst_mac, delay=0, count=10000000, pkt_size=64)
        pkts0, drops0 = get_rx_stats("rustiflow-t0")
        log_file = f"/tmp/xflow_pktgen_{r}.log"
        if os.path.exists(log_file):
            os.remove(log_file)

        proc = subprocess.Popen(
            f"sudo {XFLOWLYZER_BIN} rustiflow-t0 > /dev/null 2> {log_file}",
            shell=True
        )
        time.sleep(2)
        injected_pps = run_pktgen(duration)
        subprocess.run("sudo pkill -INT xflowlyzer 2>/dev/null || sudo pkill -INT loader 2>/dev/null", shell=True)
        time.sleep(2)

        pkts1, drops1 = get_rx_stats("rustiflow-t0")
        rx_delivered = pkts1 - pkts0
        rx_dropped = drops1 - drops0

        kernel_events = 0
        kernel_drops = 0
        speed_pps = 0.0
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                content = f.read()
                m_ev = re.search(r"Kernel-Space Ingress Events\s*:\s*(\d+)", content)
                if m_ev:
                    kernel_events = int(m_ev.group(1))
                m_dr = re.search(r"Kernel-Space Telemetry Drops\s*:\s*(\d+)", content)
                if m_dr:
                    kernel_drops = int(m_dr.group(1))
                m_sp = re.search(r"Speed\s*:\s*([\d\.]+)\s*PPS", content)
                if m_sp:
                    speed_pps = float(m_sp.group(1))

        drop_rate = (kernel_drops / (kernel_events + kernel_drops) * 100.0) if (kernel_events + kernel_drops) > 0 else 0.0
        results.append({
            "run": r,
            "rx_delivered": rx_delivered,
            "rx_dropped": rx_dropped,
            "kernel_events": kernel_events,
            "kernel_drops": kernel_drops,
            "speed_pps": speed_pps,
            "drop_rate": drop_rate
        })
        print(f"  Run {r:2d}/{runs}: RX = {rx_delivered:,} | Kernel Drops = {kernel_drops:,} ({drop_rate:.4f}%) | Speed = {speed_pps:.2f} PPS")

    return results


def main():
    parser = argparse.ArgumentParser(description="XFlowLyzer Group 3 Live In-Kernel Pktgen Benchmark")
    parser.add_argument("--runs", type=int, default=10, help="Number of repetitions (default: 10)")
    parser.add_argument("--duration", type=int, default=10, help="Duration of pktgen burst in seconds (default: 10)")
    args = parser.parse_args()

    dst_mac = setup_veth()

    print("================================================================================")
    print("  XFlowLyzer Empirical Protocol: Group 3 - In-Kernel Pktgen Multi-Core Stress   ")
    print("================================================================================")
    print(f"Target Interface : rustiflow-t0 (MAC: {dst_mac})")
    print(f"Repetitions      : N = {args.runs}")
    print(f"Burst Duration   : {args.duration}s")

    benchmark_xflowlyzer_pktgen(dst_mac, duration=args.duration, runs=args.runs)


if __name__ == "__main__":
    main()

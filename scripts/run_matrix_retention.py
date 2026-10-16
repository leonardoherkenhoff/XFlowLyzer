#!/usr/bin/env python3
import subprocess
import time
import sys
import re
import os
import argparse

SPEEDS_GBPS = [1, 10, 25, 100]
IFACE = "eno12399np0"
XFLOW_BIN = "./build/xflowlyzer"
RF_BIN = "/home/leonardo.herkenhoff/RustiFlow/target/release/rustiflow"
SERVER_A = "10.50.1.92"

def sh(cmd, ignore_err=False, timeout=1200):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip()

def get_rx_missed():
    out, _ = sh(f"ethtool -S {IFACE} | grep rx_missed_errors")
    m = re.search(r'rx_missed_errors:\s+(\d+)', out)
    return int(m.group(1)) if m else 0

def get_avg_bytes(pcap):
    out, _ = sh(f"ssh -o KexAlgorithms=curve25519-sha256 -o StrictHostKeyChecking=no leonardo.herkenhoff@{SERVER_A} 'capinfos -z {pcap}'")
    m = re.search(r'Average packet size:\s+([0-9\.]+)\s+bytes', out)
    return float(m.group(1)) if m else 800.0

def kill_all():
    sh("sudo pkill -SIGINT xflowlyzer", True)
    sh("sudo pkill -SIGINT loader", True)
    sh("sudo pkill -SIGINT rustiflow", True)
    time.sleep(1)
    sh("sudo pkill -9 xflowlyzer", True)
    sh("sudo pkill -9 loader", True)
    sh("sudo pkill -9 rustiflow", True)
    sh(f"sudo ip link set dev {IFACE} xdp off 2>/dev/null", True)
    sh(f"sudo tc qdisc del dev {IFACE} clsact 2>/dev/null", True)
    time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Group 2: Line-Rate Replay and Telemetry Retention Benchmark")
    parser.add_argument("--pcap-glob", default="/dados/CICDDoS2019/randomized/*.pcap", help="Remote PCAP glob on Server A")
    parser.add_argument("--output", default="benchmark_results/matrix_retention.csv", help="Output CSV file")
    parser.add_argument("--rounds", type=int, default=1, help="Number of rounds")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    sh(f"sudo ethtool -L {IFACE} combined 12 2>/dev/null", True)
    sh(f"sudo ip link set dev {IFACE} promisc on up 2>/dev/null", True)
    pcaps_raw, _ = sh(f"ssh -o KexAlgorithms=curve25519-sha256 -o StrictHostKeyChecking=no leonardo.herkenhoff@{SERVER_A} 'ls {args.pcap_glob}'")
    PCAPS = [p for p in pcaps_raw.split('\n') if p.endswith('.pcap')]
    if not PCAPS:
        print(f"FATAL: No PCAPs matched {args.pcap_glob} on Server A", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.output):
        with open(args.output, 'w') as f:
            f.write("Round,Dataset,Vector,Speed_Gbps,Extractor,SW_Matched,SW_Dropped,L2_Drops,Retention_pct\n")

    for r in range(1, args.rounds + 1):
        print(f"\n=== [GROUP 2 RETENTION] Starting Round {r}/{args.rounds} ===", flush=True)
        for pcap in PCAPS:
            dataset = "CICDDoS2019" if "CICDDoS" in pcap else "CIC-IDS-2017"
            vector = os.path.basename(pcap).replace('.pcap', '')
            avg_bytes = get_avg_bytes(pcap)
            print(f"\n--- [Round {r}] {dataset} / {vector} (avg_bytes={avg_bytes:.1f}) ---", flush=True)

            for speed in SPEEDS_GBPS:
                target_pps = (speed * 1_000_000_000) / (avg_bytes * 8)
                ipg_usec = 1_000_000 / target_pps

                # 1. XFlowLyzer
                kill_all()
                log_xf = "/tmp/xflow_matrix.log"
                if os.path.exists(log_xf): os.remove(log_xf)
                rx_missed_start = get_rx_missed()
                subprocess.Popen(f"sudo taskset -c 8-23 {XFLOW_BIN} {IFACE} > /dev/null 2>{log_xf}", shell=True)
                for _ in range(20):
                    o, _ = sh(f"cat {log_xf}")
                    if "XDP attached" in o:
                        break
                    time.sleep(0.5)
                time.sleep(1)
                sh(f"ssh -o KexAlgorithms=curve25519-sha256 -o StrictHostKeyChecking=no leonardo.herkenhoff@{SERVER_A} 'python3 /home/leonardo.herkenhoff/trex_test.py {pcap} {ipg_usec}'")
                sh("sudo pkill -SIGINT xflowlyzer", True)
                time.sleep(3)
                rx_missed_end = get_rx_missed()
                l2_drops = max(0, rx_missed_end - rx_missed_start)

                out, _ = sh(f"cat {log_xf}")
                m_ing = re.search(r'Kernel-Space Total Ingress:\s*(\d+)', out)
                m_drp = re.search(r'Telemetry Drops.*?:\s*(\d+)', out)
                if m_ing:
                    ing = int(m_ing.group(1))
                    drp = int(m_drp.group(1)) if m_drp else 0
                    total_injected = ing + l2_drops
                    ret = ((ing - drp) / total_injected * 100) if total_injected > 0 else 0
                    res = f"{r},{dataset},{vector},{speed},XFlowLyzer,{ing},{drp},{l2_drops},{ret:.4f}"
                else:
                    res = f"{r},{dataset},{vector},{speed},XFlowLyzer,ERR,ERR,ERR,ERR"
                with open(args.output, 'a') as f: f.write(res + "\n")
                print("    -> " + res, flush=True)

                # 2. RustiFlow
                kill_all()
                log_rf = "/tmp/rf_matrix.log"
                if os.path.exists(log_rf): os.remove(log_rf)
                rx_missed_start = get_rx_missed()
                subprocess.Popen(f"sudo systemd-run --scope -p MemoryMax=24G --setenv=RUST_LOG=info taskset -c 8-23 {RF_BIN} -f rustiflow -o print realtime {IFACE} > /dev/null 2>{log_rf}", shell=True)
                time.sleep(2)
                sh(f"ssh -o KexAlgorithms=curve25519-sha256 -o StrictHostKeyChecking=no leonardo.herkenhoff@{SERVER_A} 'python3 /home/leonardo.herkenhoff/trex_test.py {pcap} {ipg_usec}'")
                sh("sudo pkill -SIGINT rustiflow", True)
                time.sleep(3)
                rx_missed_end = get_rx_missed()
                l2_drops = max(0, rx_missed_end - rx_missed_start)

                out, _ = sh(f"cat {log_rf}")
                matches = [int(x) for x in re.findall(r'matched_packets=(\d+)', out)]
                drops = [int(x) for x in re.findall(r'dropped_packets=(\d+)', out)]
                if matches:
                    match = sum(matches)
                    drop = sum(drops)
                    total_injected = match + l2_drops
                    ret = ((match - drop) / total_injected * 100) if total_injected > 0 else 0
                    res = f"{r},{dataset},{vector},{speed},RustiFlow,{match},{drop},{l2_drops},{ret:.4f}"
                else:
                    res = f"{r},{dataset},{vector},{speed},RustiFlow,0,OOM_24G,{l2_drops},0.0000"
                with open(args.output, 'a') as f: f.write(res + "\n")
                print("    -> " + res, flush=True)

    kill_all()

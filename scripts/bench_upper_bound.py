#!/usr/bin/env python3
import os
import subprocess
import time
import re
import argparse
import csv
from datetime import datetime

PCAP_PATH = "/root/CIC-IDS-2017/Monday-WorkingHours.pcap"
RUSTIFLOW_BIN = "/home/leonardo.herkenhoff/RustiFlow/target/release/rustiflow"
XFLOWLYZER_BIN = "./build/xflowlyzer"

def setup_veth():
    print("[*] Setting up 48-queue veth pair (GRO/TSO/GSO strictly disabled)...")
    subprocess.run("sudo ip link delete rustiflow-t0", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("sudo ip netns del rustiflow-peer", shell=True, stderr=subprocess.DEVNULL)

    subprocess.run("sudo ip netns add rustiflow-peer", shell=True)
    subprocess.run("sudo ip link add rustiflow-t0 numtxqueues 48 numrxqueues 48 type veth peer name rustiflow-p0 numtxqueues 48 numrxqueues 48 netns rustiflow-peer", shell=True)
    subprocess.run("sudo ip link set rustiflow-t0 up", shell=True)
    subprocess.run("sudo ip netns exec rustiflow-peer ip link set lo up", shell=True)
    subprocess.run("sudo ip netns exec rustiflow-peer ip link set rustiflow-p0 up", shell=True)

    # Strictly disable GRO/LRO/TSO/GSO
    subprocess.run("sudo ethtool -K rustiflow-t0 rx off tx off tso off gro off gso off lro off", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("sudo ip netns exec rustiflow-peer ethtool -K rustiflow-p0 rx off tx off tso off gro off gso off lro off", shell=True, stderr=subprocess.DEVNULL)

    mac_cmd = "ip link show rustiflow-t0 | grep link/ether | awk '{print $2}'"
    mac = subprocess.check_output(mac_cmd, shell=True).decode().strip()
    return mac

def get_rx_stats(iface="rustiflow-t0"):
    try:
        res = subprocess.check_output(f"ip -s -s link show {iface}", shell=True).decode()
        lines = res.strip().split("\n")
        for idx, line in enumerate(lines):
            if "RX:" in line and "packets" in line and "dropped" in line:
                parts = lines[idx+1].split()
                return int(parts[1]), int(parts[3])
    except Exception:
        pass
    return 0, 0

def run_pktgen_round(round_id, target_mac, output_csv, duration=10):
    print(f"\n=== [GROUP 3 UPPER BOUND] Round {round_id} ===")
    pktgen_script = f"""
modprobe pktgen
for f in /proc/net/pktgen/kpktgend_*; do
    echo "rem_device_all" > $f 2>/dev/null
done

for i in $(seq 0 7); do
    echo "add_device rustiflow-p0@$i" > /proc/net/pktgen/kpktgend_$i 2>/dev/null
    dev="/proc/net/pktgen/rustiflow-p0@$i"
    if [ ! -f "$dev" ]; then
        dev="/proc/net/pktgen/rustiflow-p0"
    fi
    echo "flag QUEUE_MAP_CPU" > $dev 2>/dev/null
    echo "queue_map_min $i" > $dev 2>/dev/null
    echo "queue_map_max $i" > $dev 2>/dev/null
    echo "count 7000000" > $dev 2>/dev/null
    echo "clone_skb 1000" > $dev 2>/dev/null
    echo "pkt_size 60" > $dev 2>/dev/null
    echo "dst_mac {target_mac}" > $dev 2>/dev/null
    echo "dst 10.203.0.1" > $dev 2>/dev/null
    echo "delay 1000" > $dev 2>/dev/null
done
"""
    script_path = "/tmp/setup_pktgen_group3.sh"
    with open(script_path, "w") as f:
        f.write(pktgen_script)

    def run_pktgen():
        subprocess.run(f"sudo ip netns exec rustiflow-peer bash {script_path}", shell=True)
        subprocess.run(f"sudo ip netns exec rustiflow-peer bash -c '(sleep {duration}; echo stop > /proc/net/pktgen/pgctrl) &'", shell=True)
        subprocess.Popen("sudo ip netns exec rustiflow-peer bash -c 'echo start > /proc/net/pktgen/pgctrl'", shell=True)
        time.sleep(duration + 1)
        total_pps = 0
        try:
            res = subprocess.check_output("sudo ip netns exec rustiflow-peer bash -c 'cat /proc/net/pktgen/rustiflow-p0*'", shell=True).decode()
            pps_matches = re.findall(r"(\d+)pps", res)
            if pps_matches:
                total_pps = sum(int(p) for p in pps_matches)
                print(f"    [PktGen] Injected at {total_pps:,} PPS across {len(pps_matches)} threads", flush=True)
        except Exception as e:
            print(f"    [PktGen] Error reading stats: {e}", flush=True)
        return total_pps

    # 1. XFlowLyzer (Native XDP)
    print(f"[*] [Round {round_id}] Running XFlowLyzer Network Upper Bound...", flush=True)
    subprocess.run("sudo pkill -9 xflowlyzer rustiflow 2>/dev/null || true", shell=True)
    pkts0, drops0 = get_rx_stats("rustiflow-t0")
    if os.path.exists("/tmp/xflow_net.log"):
        os.remove("/tmp/xflow_net.log")
    subprocess.Popen(f"sudo taskset -c 8-47 {XFLOWLYZER_BIN} rustiflow-t0 > /dev/null 2> /tmp/xflow_net.log", shell=True)
    time.sleep(2)
    t0 = time.time()
    pktgen_pps_xf = run_pktgen()
    elapsed_xf = max(1.0, time.time() - t0 - 1.0)
    subprocess.run("sudo pkill -INT xflowlyzer", shell=True)
    time.sleep(2)
    pkts1, drops1 = get_rx_stats("rustiflow-t0")
    xf_ing, xf_drp = 0, 0
    if os.path.exists("/tmp/xflow_net.log"):
        with open("/tmp/xflow_net.log", "r") as logf:
            content = logf.read()
            m_ing = re.search(r"Kernel-Space Total Ingress:\s*(\d+)", content)
            m_drp = re.search(r"Telemetry Drops.*?:\s*(\d+)", content)
            if m_ing: xf_ing = int(m_ing.group(1))
            if m_drp: xf_drp = int(m_drp.group(1))
    xf_loss_pct = (xf_drp / xf_ing * 100.0) if xf_ing > 0 else 0.0
    xf_mpps = (xf_ing / elapsed_xf) / 1e6
    print(f"    [XFlowLyzer Telemetry] Ingress: {xf_ing:,} | Drops: {xf_drp:,} ({xf_loss_pct:.4f}%) | Rate: {xf_mpps:.2f} Mpps", flush=True)
    with open(output_csv, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now().isoformat(), round_id, "XFlowLyzer", pktgen_pps_xf, xf_ing, xf_drp, f"{xf_loss_pct:.4f}", f"{xf_mpps:.4f}"])

    # 2. RustiFlow (TC)
    print(f"[*] [Round {round_id}] Running RustiFlow Network Upper Bound...", flush=True)
    subprocess.run("sudo pkill -9 xflowlyzer rustiflow 2>/dev/null || true", shell=True)
    pkts0, drops0 = get_rx_stats("rustiflow-t0")
    if os.path.exists("/tmp/rf_net.log"):
        os.remove("/tmp/rf_net.log")
    subprocess.Popen(f"sudo RUST_LOG=info taskset -c 8-47 {RUSTIFLOW_BIN} -f rustiflow -o print realtime rustiflow-t0 > /dev/null 2> /tmp/rf_net.log", shell=True)
    time.sleep(2)
    t0 = time.time()
    pktgen_pps_rf = run_pktgen()
    elapsed_rf = max(1.0, time.time() - t0 - 1.0)
    subprocess.run("sudo pkill -INT rustiflow", shell=True)
    time.sleep(2)
    rf_matched, rf_submitted, rf_dropped = 0, 0, 0
    if os.path.exists("/tmp/rf_net.log"):
        with open("/tmp/rf_net.log", "r") as logf:
            for l in logf:
                if "eBPF counters" in l and "matched_packets=" in l:
                    m = re.search(r"matched_packets=(\d+), submitted_events=(\d+), dropped_packets=(\d+)", l)
                    if m:
                        rf_matched += int(m.group(1))
                        rf_submitted += int(m.group(2))
                        rf_dropped += int(m.group(3))
    rf_loss_pct = (rf_dropped / rf_matched * 100.0) if rf_matched > 0 else 0.0
    rf_mpps = (rf_submitted / elapsed_rf) / 1e6
    print(f"    [RustiFlow Telemetry] Matched: {rf_matched:,} | Submitted: {rf_submitted:,} | Dropped: {rf_dropped:,} ({rf_loss_pct:.4f}%) | Rate: {rf_mpps:.2f} Mpps", flush=True)
    with open(output_csv, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now().isoformat(), round_id, "RustiFlow", pktgen_pps_rf, rf_matched, rf_dropped, f"{rf_loss_pct:.4f}", f"{rf_mpps:.4f}"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Group 3: Upper Bound Saturation Confrontation (XDP vs TC)")
    parser.add_argument("--rounds", type=int, default=10, help="Number of benchmark rounds")
    parser.add_argument("--duration", type=int, default=10, help="Duration per burst in seconds")
    parser.add_argument("--output", default="benchmark_results/group3_upper_bound.csv", help="CSV output path")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    if not os.path.exists(args.output):
        with open(args.output, "w", newline="") as f:
            csv.writer(f).writerow(["Timestamp", "Round", "Extractor", "PktGen_PPS", "Ingress_Pkts", "Dropped_Pkts", "Drop_Pct", "Processed_Mpps"])

    mac = setup_veth()
    for r in range(1, args.rounds + 1):
        run_pktgen_round(r, mac, args.output, duration=args.duration)
    print("\n[*] Group 3 Upper Bound Benchmarks Completed!")

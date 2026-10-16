#!/usr/bin/env python3
import os
import glob
import subprocess
import time
import sys
import argparse

DEFAULT_INPUT_DIR = "/home/leonardo.herkenhoff/CICDDoS2019"
DEFAULT_OUTPUT_DIR = "benchmark_results/group1_offline"
XFLOWLYZER_EXEC = "./build/xflowlyzer"

def run_cmd(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, cwd=cwd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Group 1: Baseline Offline PCAP Ingestion Benchmark (CICDDoS2019)")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR, help="Directory containing merged CICDDoS2019 PCAPs")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory for CSVs and logs")
    parser.add_argument("--rounds", type=int, default=1, help="Number of benchmark rounds to execute")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    merged_pcaps = sorted(glob.glob(os.path.join(args.input_dir, "*.pcap")))
    if not merged_pcaps:
        print(f"FATAL: No .pcap files found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    for r in range(1, args.rounds + 1):
        total_pkts = 0
        total_time = 0.0
        log_path = os.path.join(args.output_dir, f"global_benchmark_round{r}.log")
        print(f"\n=== [GROUP 1 OFFLINE PCAP] Starting Round {r}/{args.rounds} ===", flush=True)

        with open(log_path, "w") as log_f:
            for pcap in merged_pcaps:
                attack_name = os.path.basename(pcap).replace(".pcap", "")
                output_csv = os.path.join(args.output_dir, f"XFlowLyzer_{attack_name}.csv")
                if os.path.exists(output_csv):
                    os.remove(output_csv)

                print(f"[Round {r} | {attack_name}] Running XFlowLyzer on {pcap}...", flush=True)
                start_time = time.time()
                cmd = f"sudo {XFLOWLYZER_EXEC} --pcap {pcap} > {output_csv}"
                res = run_cmd(cmd)
                end_time = time.time()
                elapsed = end_time - start_time

                attack_pkts = 0
                for line in res.stderr.split('\n'):
                    if "Kernel-Space Total Ingress:" in line:
                        attack_pkts = int(line.split()[4])

                pps = attack_pkts / elapsed if elapsed > 0 else 0
                msg = f"XFlowLyzer - {attack_name}: {attack_pkts} pkts | {elapsed:.2f}s | {pps:.2f} pps"
                print("  -> " + msg, flush=True)
                log_f.write(msg + "\n")
                log_f.flush()

                total_pkts += attack_pkts
                total_time += elapsed
                # Remove large CSV after verifying to save disk across 10 rounds
                if os.path.exists(output_csv):
                    os.remove(output_csv)

            global_pps = total_pkts / total_time if total_time > 0 else 0
            summary = (
                f"\nGLOBAL XFLOWLYZER BENCHMARK (ROUND {r})\n"
                f"Total Packets: {total_pkts}\n"
                f"Total Time: {total_time:.2f}s ({total_time/60.0:.2f} min)\n"
                f"Global PPS: {global_pps:.2f} pps\n"
            )
            print(summary, flush=True)
            log_f.write(summary)

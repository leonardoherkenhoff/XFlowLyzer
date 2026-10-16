#!/usr/bin/env bash
# ==============================================================================
# XFlowLyzer Performance Benchmark - Group 1: Native Ingestion Stress Test
# ------------------------------------------------------------------------------
# Measures sustained offline packet processing rate (PPS), execution wall time,
# and peak Resident Set Size (RSS) overhead under zero-copy in-kernel ingestion.
# ==============================================================================

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <path_to_merged_pcap>"
    exit 1
fi

PCAP_FILE="$1"

echo "================================================================================"
echo "=== XFlowLyzer Native Ingestion Benchmark (Group 1: Offline PCAP)            ==="
echo "================================================================================"
echo "[INFO] Target PCAP File: $PCAP_FILE"

if ! command -v /usr/bin/time &> /dev/null; then
    echo "[INFO] GNU time utility not found. Installing package 'time'..."
    sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y time
fi

echo "[INFO] Recompiling XFlowLyzer engine..."
make clean && make -j"$(nproc)"

echo "[INFO] Starting system resource monitor (1s interval)..."
vmstat 1 > resource_metrics.txt 2>&1 &
VMSTAT_PID=$!
trap 'kill $VMSTAT_PID 2>/dev/null || true' EXIT

echo "[INFO] Initiating native in-kernel BPF packet injection (mmap + bpf_prog_test_run_opts)..."
/usr/bin/time -v ./build/xflowlyzer --pcap "$PCAP_FILE" 2> xflowlyzer_audit.log

echo "[INFO] Ingestion completed."
kill "$VMSTAT_PID" 2>/dev/null || true

echo "================================================================================"
echo "=== Performance Benchmark Completed                                         ==="
echo "================================================================================"
echo "[INFO] Wall-clock time and memory overhead logged above via GNU /usr/bin/time."
echo "[INFO] Global resource metrics saved to: resource_metrics.txt."
echo "[INFO] Ingestion speed (PPS) and kernel telemetry saved to: xflowlyzer_audit.log."

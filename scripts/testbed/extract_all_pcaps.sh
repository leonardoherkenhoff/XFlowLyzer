#!/usr/bin/env bash
# ==============================================================================
# XFlowLyzer Testbed - Sequential Batch PCAP Feature Extractor
# ------------------------------------------------------------------------------
# Sequentially extracts high-fidelity 495-feature flow telemetry vectors from
# PCAP directories using the native in-kernel XFlowLyzer engine.
# ==============================================================================

set -euo pipefail

PCAP_DIR="${1:-${DATASET_DIR:-/data/datasets/CIC-IDS-2017-sliced}}"
OUT_DIR="${2:-./data/interim/EBPF_RAW}"
ENGINE_BIN="./build/xflowlyzer"

if [ ! -d "$PCAP_DIR" ]; then
    echo "[ERROR] PCAP source directory not found: $PCAP_DIR"
    exit 1
fi

echo "========================================================="
echo "=== XFlowLyzer Batch Feature Extractor (495 Features) ==="
echo "========================================================="
echo "[INFO] Source PCAP Directory : $PCAP_DIR"
echo "[INFO] Output CSV Directory  : $OUT_DIR"

mkdir -p "$OUT_DIR"

if [ ! -f "$ENGINE_BIN" ]; then
    echo "[INFO] Recompiling XFlowLyzer engine..."
    make clean && make -j"$(nproc)"
fi

# Clean up any lingering virtual network interfaces from previous runs
ip link delete veth0 2>/dev/null || true
ip link delete veth1 2>/dev/null || true

FILES=$(find "$PCAP_DIR" -type f \( -iname "*.pcap" -o -iname "*.pcapng" \) | sort)

if [ -z "$FILES" ]; then
    echo "[ERROR] No PCAP files found in $PCAP_DIR."
    exit 1
fi

for PCAP in $FILES; do
    BASE_PCAP=$(basename "$PCAP")
    CSV_NAME="${BASE_PCAP}.csv"
    CSV_PATH="$OUT_DIR/$CSV_NAME"
    LOG_PATH="$OUT_DIR/${BASE_PCAP}.log"

    if [ -f "$CSV_PATH" ] && [ -s "$CSV_PATH" ]; then
        echo "[INFO] Cache hit: $CSV_NAME already extracted. Skipping."
        continue
    fi

    echo ""
    echo "[*] Extracting: $BASE_PCAP -> $CSV_NAME"
    t0=$(date +%s)

    # Ingest native in-kernel via bpf_prog_test_run_opts
    "$ENGINE_BIN" --pcap "$PCAP" > "$CSV_PATH" 2> "$LOG_PATH"

    t1=$(date +%s)
    elapsed=$((t1 - t0))

    if [ -f "$CSV_PATH" ] && [ -s "$CSV_PATH" ]; then
        flow_count=$(wc -l < "$CSV_PATH" || echo 0)
        echo "    [+] Success: $((flow_count - 1)) flows extracted in ${elapsed}s."
    else
        echo "    [-] ERROR: Output CSV empty or not generated."
    fi
done

echo ""
echo "[SUCCESS] Batch PCAP feature extraction completed."

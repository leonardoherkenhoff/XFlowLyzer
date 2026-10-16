#!/usr/bin/env bash
# ==============================================================================
# XFlowLyzer Testbed - High-Volume PCAP Aggregator & Merger
# ------------------------------------------------------------------------------
# Merges sequential PCAP captures into a single consolidated packet trace
# for multi-gigabit line-rate throughput evaluation.
# ==============================================================================

set -euo pipefail

PCAP_DIR="${1:-${DATASET_DIR:-/data/datasets/CIC-IDS-2017-sliced}}"
OUTPUT_FILE="${2:-$PCAP_DIR/merged_linerate.pcap}"

echo "========================================================="
echo "=== XFlowLyzer Testbed: PCAP Consolidation Engine     ==="
echo "========================================================="

if ! command -v mergecap &> /dev/null; then
    echo "[INFO] mergecap utility not found. Installing wireshark-common..."
    sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y wireshark-common
fi

if [ ! -d "$PCAP_DIR" ]; then
    echo "[ERROR] Source directory not found: $PCAP_DIR"
    exit 1
fi

FILES=$(find "$PCAP_DIR" -maxdepth 2 -type f \( -name "*.pcap" -o -name "*.pcapng" \) ! -name "$(basename "$OUTPUT_FILE")" | sort)

if [ -z "$FILES" ]; then
    echo "[ERROR] No PCAP files located in $PCAP_DIR!"
    exit 1
fi

FILE_COUNT=$(echo "$FILES" | wc -l)
echo "[INFO] Located $FILE_COUNT PCAP captures to consolidate."
echo "[INFO] Target output archive: $OUTPUT_FILE"

mergecap -w "$OUTPUT_FILE" $FILES

echo "[SUCCESS] Successfully generated consolidated PCAP archive: $OUTPUT_FILE"

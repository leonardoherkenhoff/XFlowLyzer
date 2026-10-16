#!/usr/bin/env bash
# ==============================================================================
# XFlowLyzer Testbed - Full Master Pipeline Orchestrator (CIC-IDS-2017)
# ------------------------------------------------------------------------------
# Fully automated end-to-end evaluation pipeline without manual intervention:
# 1. Verification / Download -> 2. Temporal Slicing -> 3. In-Kernel Extraction ->
# 4. Ground-Truth Labeling -> 5. ML Benchmark -> 6. Line-Rate PPS Benchmark
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PCAP_DIR="${1:-${DATASET_DIR:-/data/datasets/CIC-IDS-2017}}"
SLICED_DIR="${2:-${DATASET_DIR:-/data/datasets/CIC-IDS-2017-sliced}}"
RAW_OUT_DIR="$BASE_DIR/data/interim/EBPF_RAW"
LABELED_OUT_DIR="$BASE_DIR/data/processed/CIC_LABELED"
LOG_DIR="$BASE_DIR/logs_pipeline"

mkdir -p "$LOG_DIR" "$RAW_OUT_DIR" "$LABELED_OUT_DIR"
cd "$BASE_DIR"

echo "================================================================================"
echo "=== XFlowLyzer Master Pipeline: CIC-IDS-2017 Full Benchmark                  ==="
echo "================================================================================"
echo "[INFO] Repository Root    : $BASE_DIR"
echo "[INFO] Raw PCAP Source    : $PCAP_DIR"
echo "[INFO] Sliced PCAP Target : $SLICED_DIR"
echo "[INFO] Pipeline Logs Dir  : $LOG_DIR"

# ------------------------------------------------------------------------------
# Phase 1: Dataset Verification & Acquisition
# ------------------------------------------------------------------------------
echo ""
echo "[Phase 1/6] Dataset Verification..."
if [ ! -d "$PCAP_DIR" ] || [ -z "$(find "$PCAP_DIR" -type f -name '*.pcap' 2>/dev/null)" ]; then
    echo "    -> Initiating automated dataset acquisition (50GB+)..."
    bash "$BASE_DIR/scripts/testbed/download_cic_ids_2017.sh" "$PCAP_DIR" 2>&1 | tee "$LOG_DIR/1_download.log"
else
    echo "    -> PCAP captures detected in $PCAP_DIR. Skipping download."
fi

# ------------------------------------------------------------------------------
# Phase 2: High-Precision Temporal Attack Slicing
# ------------------------------------------------------------------------------
echo ""
echo "[Phase 2/6] High-Precision Temporal Attack Slicing..."
bash "$BASE_DIR/scripts/testbed/slice_pcaps.sh" "$PCAP_DIR" "$SLICED_DIR" 2>&1 | tee "$LOG_DIR/2_slicing.log"

# ------------------------------------------------------------------------------
# Phase 3: High-Throughput In-Kernel XDP Extraction
# ------------------------------------------------------------------------------
echo ""
echo "[Phase 3/6] In-Kernel Feature Extraction (C-eBPF/XDP)..."
bash "$BASE_DIR/scripts/testbed/extract_all_pcaps.sh" "$SLICED_DIR" "$RAW_OUT_DIR" 2>&1 | tee "$LOG_DIR/3_extraction.log"

# ------------------------------------------------------------------------------
# Phase 4: Ground-Truth Topological Labeling
# ------------------------------------------------------------------------------
echo ""
echo "[Phase 4/6] Topological Ground-Truth Labeling..."
python3 "$BASE_DIR/scripts/preprocessing/cic_ids_2017_labeler.py" "$RAW_OUT_DIR" "$LABELED_OUT_DIR" 2>&1 | tee "$LOG_DIR/4_labeling.log"

# ------------------------------------------------------------------------------
# Phase 5: Machine Learning Benchmark Evaluation
# ------------------------------------------------------------------------------
echo ""
echo "[Phase 5/6] Machine Learning Classification Benchmark (Random Forest)..."
python3 "$BASE_DIR/scripts/analysis/run_ids2017_benchmark.py" "$LABELED_OUT_DIR" 2>&1 | tee "$LOG_DIR/5_ml_benchmark.log"

# ------------------------------------------------------------------------------
# Phase 6: Line-Rate Replay & Sustained Throughput Verification
# ------------------------------------------------------------------------------
echo ""
echo "[Phase 6/6] Line-Rate Replay & Sustained Throughput Verification..."
MERGED_PCAP="$SLICED_DIR/merged_stress.pcap"
if [ ! -f "$MERGED_PCAP" ]; then
    echo "    -> Merging PCAP slices for line-rate stress test..."
    bash "$BASE_DIR/scripts/testbed/merge_pcaps.sh" "$SLICED_DIR" "$MERGED_PCAP" 2>&1 | tee "$LOG_DIR/6_merge.log"
fi

if [ -f "$MERGED_PCAP" ]; then
    echo "    -> Executing continuous replay performance benchmark..."
    bash "$BASE_DIR/scripts/testbed/run_performance_test.sh" "$MERGED_PCAP" 2>&1 | tee "$LOG_DIR/7_performance.log"
fi

echo ""
echo "================================================================================"
echo "=== PIPELINE COMPLETED SUCCESSFULLY: All artifacts logged to $LOG_DIR ==="
echo "================================================================================"

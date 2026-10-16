#!/usr/bin/env bash
# ==============================================================================
# XFlowLyzer Testbed - Dataset Ingestion Script for CIC-IDS-2017
# ------------------------------------------------------------------------------
# Automates the authenticated acquisition of the full CIC-IDS-2017 PCAP cohort.
# ==============================================================================

set -euo pipefail

DEST_DIR="${1:-${DATASET_DIR:-/data/datasets/CIC-IDS-2017}}"
mkdir -p "$DEST_DIR"
cd "$DEST_DIR"

COOKIE_FILE="$DEST_DIR/cookies.txt"

if [ ! -f "$COOKIE_FILE" ]; then
    echo "[ERROR] Authentication cookie file not found at: $COOKIE_FILE"
    echo "Please provide your authenticated Netscape cookies from the UNB CIC portal."
    exit 1
fi

URLS=(
    "https://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/PCAPs/Monday-WorkingHours.pcap"
    "https://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/PCAPs/Tuesday-WorkingHours.pcap"
    "https://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/PCAPs/Wednesday-workingHours.pcap"
    "https://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/PCAPs/Thursday-WorkingHours-Morning-WebAttacks.pcap"
    "https://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/PCAPs/Thursday-WorkingHours-Afternoon-Infilteration.pcap"
    "https://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/PCAPs/Friday-WorkingHours-Morning.pcap"
    "https://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/PCAPs/Friday-WorkingHours-Afternoon-PortScan.pcap"
    "https://cicresearch.ca/CICDataset/CIC-IDS-2017/Dataset/PCAPs/Friday-WorkingHours-Afternoon-DDos.pcap"
)

echo "========================================================="
echo "=== XFlowLyzer CIC-IDS-2017 Automated Downloader      ==="
echo "========================================================="
echo "[INFO] Destination Directory: $DEST_DIR"

for URL in "${URLS[@]}"; do
    FILENAME=$(basename "$URL")
    if [ ! -f "$FILENAME" ]; then
        echo "[INFO] Downloading: $FILENAME..."
        curl -b "$COOKIE_FILE" -C - -L -O "$URL"
    else
        echo "[INFO] Skipping already downloaded file: $FILENAME"
    fi
done

echo "[SUCCESS] CIC-IDS-2017 dataset acquisition verified in $DEST_DIR"

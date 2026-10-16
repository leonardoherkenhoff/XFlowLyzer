#!/usr/bin/env bash
# ==============================================================================
# XFlowLyzer Testbed - Deterministic PCAP Temporal Slicer (CIC-IDS-2017)
# ------------------------------------------------------------------------------
# Partitions massive multi-day raw PCAPs into isolated, ground-truth-aligned
# attack windows using wireshark editcap.
# ==============================================================================

set -euo pipefail

SRC="${1:-${DATASET_DIR:-/data/datasets/CIC-IDS-2017}}"
DST="${2:-${DATASET_DIR:-/data/datasets/CIC-IDS-2017-sliced}}"

mkdir -p "$DST"

echo "========================================================="
echo "=== XFlowLyzer Deterministic Attack Window Slicer     ==="
echo "========================================================="
echo "[INFO] Source Directory      : $SRC"
echo "[INFO] Destination Directory : $DST"

if ! command -v editcap &> /dev/null; then
    echo "[INFO] editcap utility not found. Installing wireshark-common..."
    sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y wireshark-common
fi

# 1. Monday (Pure Benign Baseline)
if [ -f "$SRC/Monday-WorkingHours.pcap" ]; then
    echo " -> Slicing Monday-Benign-Normal (09:00 - 17:00)..."
    editcap -F pcap -A "2017-07-03 09:00:00" -B "2017-07-03 17:00:00" "$SRC/Monday-WorkingHours.pcap" "$DST/Monday-Benign-Normal.pcap"
fi

# 2. Tuesday (Brute Force SSH & FTP)
if [ -f "$SRC/Tuesday-WorkingHours.pcap" ]; then
    echo " -> Slicing Tuesday-FTP-Patator (09:20 - 10:20)..."
    editcap -F pcap -A "2017-07-04 09:20:00" -B "2017-07-04 10:20:00" "$SRC/Tuesday-WorkingHours.pcap" "$DST/Tuesday-FTP-Patator.pcap"

    echo " -> Slicing Tuesday-SSH-Patator (14:00 - 15:00)..."
    editcap -F pcap -A "2017-07-04 14:00:00" -B "2017-07-04 15:00:00" "$SRC/Tuesday-WorkingHours.pcap" "$DST/Tuesday-SSH-Patator.pcap"
fi

# 3. Wednesday (DoS / DDoS and Heartbleed)
if [ -f "$SRC/Wednesday-workingHours.pcap" ]; then
    echo " -> Slicing Wednesday-DoS-slowloris (09:47 - 10:10)..."
    editcap -F pcap -A "2017-07-05 09:47:00" -B "2017-07-05 10:10:00" "$SRC/Wednesday-workingHours.pcap" "$DST/Wednesday-DoS-slowloris.pcap"

    echo " -> Slicing Wednesday-DoS-Slowhttptest (10:14 - 10:35)..."
    editcap -F pcap -A "2017-07-05 10:14:00" -B "2017-07-05 10:35:00" "$SRC/Wednesday-workingHours.pcap" "$DST/Wednesday-DoS-Slowhttptest.pcap"

    echo " -> Slicing Wednesday-DoS-Hulk (10:43 - 11:00)..."
    editcap -F pcap -A "2017-07-05 10:43:00" -B "2017-07-05 11:00:00" "$SRC/Wednesday-workingHours.pcap" "$DST/Wednesday-DoS-Hulk.pcap"

    echo " -> Slicing Wednesday-DoS-GoldenEye (11:10 - 11:23)..."
    editcap -F pcap -A "2017-07-05 11:10:00" -B "2017-07-05 11:23:00" "$SRC/Wednesday-workingHours.pcap" "$DST/Wednesday-DoS-GoldenEye.pcap"

    echo " -> Slicing Wednesday-Heartbleed (15:12 - 15:32)..."
    editcap -F pcap -A "2017-07-05 15:12:00" -B "2017-07-05 15:32:00" "$SRC/Wednesday-workingHours.pcap" "$DST/Wednesday-Heartbleed.pcap"
fi

# 4. Thursday (Web Attacks & Infiltration)
if [ -f "$SRC/Thursday-WorkingHours-Morning-WebAttacks.pcap" ]; then
    echo " -> Slicing Thursday-WebAttacks (09:20 - 10:45)..."
    editcap -F pcap -A "2017-07-06 09:20:00" -B "2017-07-06 10:45:00" "$SRC/Thursday-WorkingHours-Morning-WebAttacks.pcap" "$DST/Thursday-WebAttacks.pcap"
fi

if [ -f "$SRC/Thursday-WorkingHours-Afternoon-Infilteration.pcap" ]; then
    echo " -> Slicing Thursday-Infiltration (14:00 - 15:45)..."
    editcap -F pcap -A "2017-07-06 14:00:00" -B "2017-07-06 15:45:00" "$SRC/Thursday-WorkingHours-Afternoon-Infilteration.pcap" "$DST/Thursday-Infiltration.pcap"
fi

# 5. Friday (Botnet, PortScan, DDoS)
if [ -f "$SRC/Friday-WorkingHours-Morning.pcap" ]; then
    echo " -> Slicing Friday-Botnet (09:00 - 10:00)..."
    editcap -F pcap -A "2017-07-07 09:00:00" -B "2017-07-07 10:00:00" "$SRC/Friday-WorkingHours-Morning.pcap" "$DST/Friday-Botnet.pcap"
fi

if [ -f "$SRC/Friday-WorkingHours-Afternoon-PortScan.pcap" ]; then
    echo " -> Slicing Friday-PortScan (13:55 - 15:30)..."
    editcap -F pcap -A "2017-07-07 13:55:00" -B "2017-07-07 15:30:00" "$SRC/Friday-WorkingHours-Afternoon-PortScan.pcap" "$DST/Friday-PortScan.pcap"
fi

if [ -f "$SRC/Friday-WorkingHours-Afternoon-DDos.pcap" ]; then
    echo " -> Slicing Friday-DDoS (15:30 - 17:00)..."
    editcap -F pcap -A "2017-07-07 15:30:00" -B "2017-07-07 17:00:00" "$SRC/Friday-WorkingHours-Afternoon-DDos.pcap" "$DST/Friday-DDoS.pcap"
fi

echo "[SUCCESS] Deterministic PCAP slicing completed in $DST."

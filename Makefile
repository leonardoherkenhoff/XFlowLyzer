# Makefile - XFlowLyzer v1.0.0
# Description: High-Performance eBPF/XDP Network Telemetry and Flow Extraction Engine
# -----------------------------------------------------------------------------
# Objective: Production-grade network feature extraction and real-time telemetry.
# Orchestrates compilation of the XFlowLyzer data plane (C-eBPF/XDP) and
# control plane (C daemon with lockless SPSC queues).
#
# Requirements:
# - Clang/LLVM 14+ (BPF Target)
# - libbpf-dev, libelf-dev, zlib1g-dev, libpcap-dev
# - Linux Kernel 6.1+ (XDP Native Driver, LRU Maps, RingBuffer Support)
# -----------------------------------------------------------------------------

CLANG ?= clang
LLC ?= llc
BPFTOOL ?= bpftool

# --- Workspace Configuration ---
SRC_DIR = src
EBPF_DIR = $(SRC_DIR)/ebpf
DAEMON_DIR = $(SRC_DIR)/daemon
BUILD_DIR = build

# --- Output Artifacts ---
EBPF_OBJ = $(BUILD_DIR)/main.bpf.o
DAEMON_BIN = $(BUILD_DIR)/xflowlyzer

# --- Compilation Flags ---
# User-Space: Standard GNU11 with libbpf, math and pcap linkage
CFLAGS = -g -O3 -march=native -flto -Wall -Wextra -std=gnu11
# Kernel-Space: BPF architecture target with BTF alignment
BPF_CFLAGS = -g -O2 -target bpf -D__TARGET_ARCH_x86 -I$(EBPF_DIR) \
             -Wall -Wno-missing-declarations -Wno-compare-distinct-pointer-types

# --- Linker Dependencies ---
LDFLAGS = -L/usr/local/lib64 -lbpf -lelf -lz -lm -lpcap -Wl,-rpath,/usr/local/lib64

# --- Build Rules ---

all: $(BUILD_DIR) $(EBPF_OBJ) $(DAEMON_BIN)

$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

# Target: Data Plane Interceptor (XDP)
$(EBPF_OBJ): $(EBPF_DIR)/main.bpf.c $(EBPF_DIR)/xflowlyzer.h $(EBPF_DIR)/vmlinux.h
	@echo "[*] Compiling eBPF Data Plane: $<"
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@

# Target: Control Plane Orchestrator (XFlowLyzer Daemon)
$(DAEMON_BIN): $(DAEMON_DIR)/loader.c $(EBPF_DIR)/xflowlyzer.h
	@echo "[*] Compiling User-Space Control Plane: $<"
	$(CLANG) $(CFLAGS) $< -o $@ $(LDFLAGS)

clean:
	@echo "[*] Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)

.PHONY: all clean

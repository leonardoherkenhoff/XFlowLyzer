# Changelog

All notable changes to the **XFlowLyzer** project will be documented in this file.

---

## [1.0.0] - 2026-09-11
### Initial Production Release (Canonical Baseline)
- **High-Performance Data Plane**: 100% C-eBPF/XDP engine with dual-stack support (IPv4-mapped-IPv6).
- **Driver-Mode Hook (`XDP_DRV`)**: Zero-copy packet interception at the physical NIC ring buffer before `sk_buff` allocation.
- **LRU Per-CPU State Tracking**: Migration to `BPF_MAP_TYPE_LRU_PERCPU_HASH` for passive eviction under volumetric floods.
- **Multi-Core Telemetry Array**: Dedicated 16MB per-CPU ring buffers via `BPF_MAP_TYPE_ARRAY_OF_MAPS`, eliminating shared lock contention.
- **Lock-Free SPSC Architecture**: User-space control plane utilizing C11 Atomics (`stdatomic.h`) with dedicated asynchronous writer thread.
- **Native Tunnel Decapsulation**: In-kernel recursive parsing for GRE and VXLAN overlay encapsulations.
- **Kernel-Space L7 Visibility**: Deep parsing for DNS (pointer-compression safe), NTP, SNMP, and SSDP.
- **Statistical Moments in $O(1)$**: Online computation of 4th-order moments (Welford's algorithm) and $P^2$ dynamic quantile estimation.
- **High-Fidelity PCAP Ingestion**: Offline PCAP execution directly in kernel space via `mmap` and `bpf_prog_test_run_opts`.
- **Comprehensive Feature Suite**: Complete 495-feature telemetric matrix with 80-bin behavioral distribution histograms.

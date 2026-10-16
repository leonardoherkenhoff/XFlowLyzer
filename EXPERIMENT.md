# Experiment Specification & Reproducibility Protocol: Group 2 - Line-Rate Telemetry Retention Benchmark

> [!IMPORTANT]
> **Scientific Reproducibility Specification: Group 2 (Line-Rate Retention & Multi-Gbps Stability)**
> This document details the benchmark protocol, execution commands, and comparative telemetry retention metrics for the evaluation of **XFlowLyzer** against user-space extractors (**CICFlowMeter**, **NTLFlowLyzer**, **ALFlowLyzer**) and kernel-space comparators (**RustiFlow**) under continuous line-rate packet injection on the **CICDDoS2019** and **CIC-IDS-2017** datasets.

---

## 1. Research Scope & Architectural Hypothesis

During volumetric distributed denial-of-service (DDoS) events, packet ingestion rates exceed millions of packets per second (Mpps). Under these high-density conditions:
1. **User-Space Memory Collapse**: Tools relying on `libpcap` or user-space socket loops allocate dynamic memory buffers per packet, resulting in exponential memory bloating ($9.13\,\text{GB}$ to $13.38\,\text{GB}$ Peak RSS) and catastrophic termination by the Linux Out-Of-Memory (OOM) killer.
2. **Traffic Control (TC) Spinlock Contention**: Solutions operating at the TC layer incur lock contention on socket buffer (`sk_buff`) allocation, causing severe involuntary packet dropping ($>78\%$ packet loss).
3. **The XFlowLyzer In-Kernel Guarantee**: By executing lockless state aggregation at the driver layer (`XDP_DRV`), XFlowLyzer maintains stationary memory allocation ($128.52\,\text{MB}$ RSS) and guarantees $100.0000\%$ telemetry event retention (zero drops).

---

## 2. Hardware & Environment Specification

| Parameter | Specification |
| :--- | :--- |
| **Processor (CPU)** | Intel(R) Xeon(R) Gold (48 SMP logical cores) |
| **System Memory (RAM)** | $32\,\text{GB}$ DDR4 ECC dedicated, unswappable pages |
| **Operating System** | Linux Kernel $6.8+$ (with BPF CO-RE & native XDP driver support) |
| **Network Interfaces** | Dedicated $100\,\text{Gbps}$ interfaces (Mellanox ConnectX-6 Dx / Broadcom BCM57508) |
| **Hardware Offloads** | Disabled: `ethtool -K ... rx off tx off tso off gro off gso off lro off` |
| **Workload Datasets** | CICDDoS2019 (Reflective UDP Amplification) and CIC-IDS-2017 (Volumetric Floods) |

---

## 3. Empirical Reference Baseline (Paper Table 4)

| Extractor | Execution Plane | Interception Layer | Concurrency Model | Max Packet Rate (PPS) | Peak RAM (RSS) | Multi-Gigabit Stability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CICFlowMeter** | User Space (Java) | Socket / `libpcap` | Mutex / JVM GC | $68,152\,\text{PPS}$ ($0.06\,\text{Mpps}$) | $9.13\,\text{GB}$ (OOM Crash) | Flow Collapse |
| **NTLFlowLyzer** | User Space (Python) | Socket / `dpkt` | Single-process / User Heap | $12,505\,\text{PPS}$ ($0.01\,\text{Mpps}$) | $13.38\,\text{GB}$ (Bloat) | F1 Blindness / Stateless |
| **ALFlowLyzer** | User Space (Python) | Deep L7 Ingestion | Lexical User Parser | $3,118\,\text{PPS}$ ($0.003\,\text{Mpps}$) | $12.19\,\text{GB}$ (Bloat) | L7 Restricted |
| **RustiFlow** | Kernel Space (Rust) | Traffic Control (TC) | Global RingBuffer / **Spinlock** | $\sim 2.51\,\text{Mpps}$ | $> 1.8\,\text{GB}$ | Partial (High Drop Rate) |
| **XFlowLyzer (Proposed)** | **Kernel Space (C)** | **XDP Driver Mode** | **Distributed Lockless SPSC** | **$> 5.03\,\text{Mpps}$** | **$128.52\,\text{MB}$** | **Yes ($100\%$ Retention)** |

---

## 4. Automated Reproduction Pipeline

### Step 1: Compile the XFlowLyzer Engine
```bash
make clean && make -j$(nproc)
```

### Step 2: Run the Line-Rate Retention Benchmark ($N=10$)
```bash
# Line-rate interface capture evaluation
sudo python3 scripts/run_linerate_benchmark.py --target eth0 --runs 10

# High-density volumetric capture evaluation
sudo python3 scripts/run_linerate_benchmark.py --target /path/to/CICDDoS2019.pcap --pcap --runs 10
```

### Step 3: Run the Full End-to-End Pipeline (Ingestion -> Labeling -> ML Evaluation)
```bash
sudo bash scripts/run_cic_ids_2017_full_pipeline.sh /path/to/CIC-IDS-2017
```

---

## 5. Multi-Run Statistical Protocol ($N=10$)

To establish empirical confidence intervals ($\mu \pm \sigma$) across $N=10$ independent repetitions:
```bash
for run in $(seq 1 10); do
    echo "[INFO] Running Group 2 Line-Rate Retention Benchmark ${run}/10..."
    sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
    python3 scripts/run_linerate_benchmark.py --target /path/to/CICDDoS2019.pcap --pcap --runs 1 > "logs_pipeline/linerate_run_${run}.log"
done
```

# Experiment Specification & Reproducibility Protocol: Group 1 - Native Offline PCAP Ingestion Benchmark

> [!IMPORTANT]
> **Scientific Reproducibility Specification: Group 1 (Offline PCAP Ingestion)**
> This document details the benchmark protocol, execution commands, and comparative metrics for the evaluation of **XFlowLyzer's Native Kernel PCAP Ingestion Engine** (`bpf_prog_test_run_opts` and `mmap`) against user-space network feature extractors (**RustiFlow**, **NTLFlowLyzer**, **CICFlowMeter**, and **NetFeatureXtract / NFX**).
>
> Evaluated Workload: Complete consolidated CIC-IDS-2017 dataset ($30.06\,\text{GB}$, $46,872,693$ packets).

---

## 1. Research Scope & Architectural Hypothesis

Traditional network traffic feature extractors execute offline PCAP processing in user-space via libraries such as `libpcap` or raw packet socket loops. This paradigm introduces severe architectural bottlenecks:
* Context-switch overhead and kernel-to-user memory copying for every frame.
* Unbounded memory allocation in user-space flow tables and dynamic heap data structures (*Memory Bloating*).
* High variance in processing latency and low sustained Packet-Per-Second (PPS) ceilings.

### The XFlowLyzer Native In-Kernel Paradigm:
XFlowLyzer eliminates user-space packet parsing by mapping offline PCAP frames directly into kernel memory via `mmap` and dispatching packet buffers directly to the XDP driver program using `bpf_prog_test_run_opts`:
1. **Zero-Copy Ingestion**: Raw packet bytes are injected into the kernel eBPF verification sandbox at physical memory bandwidth.
2. **Stationary Memory Allocation**: State tracking is strictly confined to in-kernel `BPF_MAP_TYPE_LRU_PERCPU_HASH` maps, locking RSS memory to a constant $128.52\,\text{MB}$ ($\sigma^2_{RSS} = 0$).
3. **Execution Determinism**: Eliminates user-space garbage collection and interpreter latency.

---

## 2. Hardware & Environment Specification

| Parameter | Specification |
| :--- | :--- |
| **Processor (CPU)** | Intel(R) Xeon(R) Gold (48 SMP logical cores) |
| **System Memory (RAM)** | $32\,\text{GB}$ DDR4 ECC dedicated, unswappable pages |
| **Operating System** | Linux Kernel $6.8+$ (with BPF CO-RE & `bpf_prog_test_run_opts`) |
| **Offloads** | Hardware acceleration disabled: `ethtool -K ... rx off tx off tso off gro off gso off lro off` |
| **Dataset Benchmark Workload** | Full merged CIC-IDS-2017 capture ($30.06\,\text{GB}$, $46,872,693$ datagrams) |

---

## 3. Empirical Reference Baseline (Paper Table 2)

| Metric | XFlowLyzer (Proposed XDP) | Baseline Tools (CICFlowMeter / NTLFlowLyzer) |
| :--- | :--- | :--- |
| **Execution Wall Time** | **$11.99\,\text{s}$** | $> 1,200\,\text{s}$ (or crashed) |
| **Sustained Throughput** | **$4.17\,\text{GB/s}$** ($\sim 33.36\,\text{Gbps}$) | $< 0.15\,\text{GB/s}$ |
| **Inspection Frequency** | **$1,933,151\,\text{PPS}$** ($\sim 1.93\,\text{Mpps}$) | $< 68,000\,\text{PPS}$ |
| **Peak RAM (Max RSS)** | **$128.52\,\text{MB}$** (Stationary) | $9.13\,\text{GB}$ to $13.38\,\text{GB}$ (OOM crash) |
| **Kernel Retention Rate** | **$100.0000\%$** (Zero Drops) | Degraded / Involuntary Sampling |

---

## 4. Automated Reproduction Pipeline

### Step 1: Compile the XFlowLyzer Engine
```bash
make clean && make -j$(nproc)
```

### Step 2: Run the In-Kernel Ingestion Performance Benchmark
```bash
sudo bash scripts/testbed/run_performance_test.sh /path/to/CIC-IDS-2017-merged.pcap
```

### Step 3: Run the Automated Comparative Benchmark ($N=10$)
```bash
sudo python3 scripts/bench_offline.py --pcap /path/to/CIC-IDS-2017-merged.pcap --runs 10
```

---

## 5. Multi-Run Statistical Protocol ($N=10$)

To establish empirical confidence intervals ($\mu \pm \sigma$) across $N=10$ independent repetitions:
```bash
for run in $(seq 1 10); do
    echo "[INFO] Running Group 1 Ingestion Benchmark ${run}/10..."
    sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
    /usr/bin/time -v ./build/xflowlyzer --pcap /path/to/CIC-IDS-2017-merged.pcap 2> "logs_pipeline/pcap_run_${run}.err"
done
```

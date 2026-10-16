# Experiment Specification & Reproducibility Protocol: Group 3 - Upper Bound Capacity Confrontation

> [!IMPORTANT]
> **Scientific Reproducibility Specification: Group 3 (Upper Bound Capacity & TC Contention)**
> This document details the benchmark protocol, execution commands, and comparative metrics for the physical capacity confrontation between **XFlowLyzer** (Driver-Mode Native XDP Data Plane) and **RustiFlow** (Linux Traffic Control / TC Data Plane) under multi-threaded parallel stress across 48 SMP logical cores without replay bottleneck.

---

## 1. Research Scope & Architectural Hypothesis

Packet capture engines face catastrophic degradation when traffic rates approach multi-million packets per second (Mpps). Under these regimes:
1. **The Traffic Control (TC) Bottleneck**: TC hooks operate after the Linux networking subsystem allocates socket buffers (`sk_buff`). Under concurrent multi-core injection, global memory locks and atomic spinlocks cause massive buffer exhaustion and event loss (`-EBUSY` / `-ENOBUFS`), dropping more than $78\%$ of critical telemetry events.
2. **The XDP Driver Advantage**: Native XDP programs execute directly at the network interface driver (`XDP_DRV`) prior to `sk_buff` instantiation. Memory access is lockless and localized to per-CPU caches (`LRU_PERCPU_HASH`), enabling sustainable multi-Mpps line-rate processing with absolute zero packet loss ($100.0000\%$ retention).

---

## 2. Hardware & Environment Specification

| Parameter | Specification |
| :--- | :--- |
| **Processor (CPU)** | Intel(R) Xeon(R) Gold (48 SMP logical cores) |
| **System Memory (RAM)** | $32\,\text{GB}$ DDR4 ECC dedicated, unswappable pages |
| **Operating System** | Linux Kernel $6.8+$ (with BPF CO-RE & native XDP driver support) |
| **Network Interfaces** | Isolated multi-queue `veth` pair (`rustiflow-t0` $\leftrightarrow$ `rustiflow-p0`, 48 queues) |
| **Network Namespace** | `rustiflow-peer` (isolated network stack) |
| **Hardware Offloads** | Disabled: `ethtool -K ... rx off tx off tso off gro off gso off lro off` |
| **Traffic Generator** | Synthetic multi-threaded UDP injection / Linux In-Kernel `pktgen` (`kpktgend_0` to `kpktgend_47`) |

---

## 3. Empirical Reference Baseline (Paper Table 3)

| Benchmark Metric | RustiFlow (TC Hook) | XFlowLyzer (Proposed XDP Hook) | Metric Differential |
| :--- | :--- | :--- | :--- |
| **Average Ingress Injection Rate** | $2,511,461\,\text{PPS}$ ($\sim 2.51\,\text{Mpps}$) | $5,030,633\,\text{PPS}$ ($\sim 5.03\,\text{Mpps}$) | **$+100.30\%$ Throughput via XDP** |
| **Total Packets Intercepted** | $25,087,735\,\text{packets}$ | $53,819,675\,\text{packets}$ | $2.14\times$ Bandwidth Capacity |
| **Events Received in User Space** | $5,484,110\,\text{events}$ ($21.8598\%$) | $53,819,675\,\text{events}$ ($100.0000\%$) | Complete Statistical Retention |
| **Registered Drops (Kernel eBPF)** | $19,603,625\,\text{packets}$ | **$0\,\text{packets}$** | $19.6\,\text{M}$ drops vs. **ZERO** |
| **Experimental Packet Loss Rate (%)** | **$78.1402\%$** | **$0.0000\%$** | **Absolute Zero Loss** |

---

## 4. Automated Reproduction Pipeline

### Step 1: Compile the XFlowLyzer Engine
```bash
make clean && make -j$(nproc)
```

### Step 2: Run the Upper Bound Physical Confrontation Benchmark ($N=10$)
```bash
sudo python3 scripts/bench_upper_bound.py --duration 10 --runs 10
```

### Step 3: Run the In-Kernel Pktgen Sched-Cls Confrontation Benchmark ($N=10$)
```bash
sudo python3 scripts/bench_pktgen.py --duration 10 --runs 10
```

---

## 5. Multi-Run Statistical Protocol ($N=10$)

To establish empirical confidence intervals ($\mu \pm \sigma$) across $N=10$ independent repetitions:
```bash
for run in $(seq 1 10); do
    echo "[INFO] Running Group 3 Upper Bound Confrontation Run ${run}/10..."
    sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
    python3 scripts/bench_upper_bound.py --duration 10 --runs 1 > "logs_pipeline/upperbound_run_${run}.log"
done
```

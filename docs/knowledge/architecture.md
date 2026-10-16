# XFlowLyzer v1.0.0 — Systems Architecture & Mathematical Specification

## 1. Architectural Overview & Design Philosophy
**XFlowLyzer** is designed to eliminate synchronization bottlenecks and deliver statistical fidelity at multi-gigabit line rates. The architecture enforces an absolute decoupling between the in-kernel **Data Plane (eBPF/XDP)** and the user-space **Control Plane (C Daemon)**:

```
                       [ KERNEL-SPACE (eBPF/XDP Hook) ]
                                      │
          [Physical NIC Rx] ──> Driver-layer XDP hook (PHY-level timestamping)
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
   LRU PERCPU Hash Maps (O(1))                     Array-of-Maps RingBuffer
 (Per-core state isolation & LRU)              (Dedicated 16MB ring per CPU core)
              │                                               │
              └───────────────────────┬───────────────────────┘
                                      │
                                      ▼ [ zero-copy mmap ]
                       [ USER-SPACE (Control Plane Daemon) ]
                                      │
                       Lockless SPSC Queue per Worker (C11)
                                      │
             ┌────────────────────────┴────────────────────────┐
             ▼                                                 ▼
     Welford's Algorithm                               Online P² Estimator
  (Iterative 4th-order moments)                     (Dynamic quantiles & medians)
             │                                                 │
             └────────────────────────┬────────────────────────┘
                                      │
                                      ▼
                        Asynchronous Writer Thread
                                      │
                                      ▼ [ 4MB Stream Buffer ]
                          flows.csv / stdout pipeline
```

---

## 2. Kernel-Space Data Plane (C + eBPF/XDP)

### A. Driver-Level Early Hook (`XDP_DRV`)
* **Zero Socket Buffer Overhead:** Intercepts raw Ethernet frames directly at the NIC ring buffer before memory allocation of Linux `sk_buff` structures, eliminating memory bus pressure.
* **Strict Static Verifier Compliance:** Strict bounds checking is enforced before reading any protocol header:
  ```c
  if ((void *)(eth + 1) > data_end) return XDP_PASS;
  ```
* **Recursive Overlay Dissection:**
  * **GRE (IP Protocol 47):** Parses flags, validates checksums, extracts GRE Keys (Tunnel IDs), and realigns the pointer to inspect the encapsulated inner IP payload.
  * **VXLAN (UDP Destination Port 4789):** Extracts the 24-bit Virtual Network Identifier (VNI / Tunnel ID) via `vxlan->vni >> 8` and shifts inspection to the inner Ethernet frame.

### B. Shared-Nothing State Tracking (`LRU_PERCPU_HASH`)
* **No Spinlock Contention:** State tracking uses `BPF_MAP_TYPE_LRU_PERCPU_HASH`. Each CPU core accesses an exclusive segment of memory without inter-core synchronization locks.
* **Passive LRU Eviction:** Under volumetric saturation or state exhaustion attacks (e.g., SYN Floods), the kernel passively evicts the least recently accessed flow records, preventing Out-of-Memory (OOM) panics.

### C. Multi-Core Telemetry Array (`ARRAY_OF_MAPS`)
* Telemetry events are emitted through an outer array map (`BPF_MAP_TYPE_ARRAY_OF_MAPS`) pointing to private, per-CPU `BPF_MAP_TYPE_RINGBUF` instances ($16\,\text{MB}$ each). This design avoids the contention of shared global ring buffers.

---

## 3. User-Space Control Plane (C Daemon)

### A. Multi-Threaded Lockless SPSC Architecture
* Each worker thread reads from its assigned kernel ring buffer and enqueues formatted flow records into a private **Single-Producer Single-Consumer (SPSC)** circular queue.
* The SPSC queues are synchronized purely via **C11 Atomics** (`stdatomic.h`) with acquire/release memory semantics, eliminating mutex contention.
* A dedicated writer thread (`writer_fn`) continuously drains the queues and outputs records through a $4\,\text{MB}$ buffered stream (`setvbuf`).

### B. $O(1)$ Statistical Pipeline: Welford's Algorithm
Statistical moments are computed iteratively without storing packet histories:
$$\mu_k = \mu_{k-1} + \frac{x_k - \mu_{k-1}}{k}$$
$$M_{2,k} = M_{2,k-1} + (x_k - \mu_{k-1})(x_k - \mu_k)$$
$$\sigma^2 = \frac{M_{2,k}}{k - 1}$$
Higher-order moments (Skewness and Kurtosis) are likewise derived iteratively in $O(1)$ time complexity.

### C. Online Quantile Estimation: $P^2$ Algorithm
Medians and percentiles (Payload, Inter-Arrival Times, Window sizes) are estimated dynamically using the piecewise-parabolic $P^2$ algorithm with 5 dynamic marker positions, maintaining strict $O(1)$ memory.

### D. Memory Stationary Guarantees (Zero-Alloc Hot Path)
* Memory footprint is statically pinned at **$128.52\,\text{MB}$ RSS**.
* All worker queues, buffers, and tables are allocated during the `auto_tune()` initialization phase. Zero `malloc` calls occur in the packet processing loop ($\sigma^2_{RSS} = 0$).

### E. Deterministic Signal Handling & Telemetry Drain
* Interception of `SIGINT` and `SIGTERM` signals triggers an orderly teardown:
  1. Detaches the XDP hook from the network interface to halt new packet ingress.
  2. Sleeps for 2 seconds to allow in-flight events to populate ring buffers.
  3. Joins all worker threads and writer threads, guaranteeing **0% telemetry loss** during shutdown.

---

## 4. Methodological Hygiene & Leakage Prevention
* **Mandatory Feature Sanitization (`IDENTITY_DROP`):**
  To prevent topological overfitting and synthetic data leakage in machine learning pipelines, identification metadata columns are isolated from behavioral features:
  `['flow_id', 'timestamp', 'src_ip', 'dst_ip', 'src_port', 'dst_port', 'src_mac', 'dst_mac', 'protocol', 'ip_ver', 'eth_proto', 'traffic_class', 'flow_label', 'TunnelId', 'TunnelType']`
* Classifiers trained on XFlowLyzer outputs model morphological traffic behavior rather than local network identifiers.

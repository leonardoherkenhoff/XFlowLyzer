# XFlowLyzer — Architectural Roadmap & Evolution Plan

## Phase 1: Canonical Foundation & Production Engine (v1.0.0) — [COMPLETED]
* [x] **Native eBPF/XDP Data Plane**: Zero-copy packet interception at NIC driver layer (`XDP_DRV`) and virtual ethernet (`veth`) interfaces.
* [x] **Advanced Protocol Dissection**: Native encapsulation support for GRE and VXLAN overlay tunnels, plus in-kernel L7 parsers (DNS, NTP, SNMP, SSDP).
* [x] **495-Feature Statistical Matrix**: Online iterative 4th-order statistical moments (Welford's algorithm) and dynamic $P^2$ quantile estimation without dynamic heap allocation.
* [x] **Stationary RSS Footprint**: Memory consumption statically pinned at $128.52\,\text{MB}$ RSS under high-throughput line-rate packet injection ($\sigma^2_{RSS} = 0$).
* [x] **Contention-Free Multi-Core I/O**: Dedicated per-CPU RingBuffers (`ARRAY_OF_MAPS`) and lockless C11 SPSC worker queues feeding an asynchronous writer thread.
* [x] **Production Dual-Stack Processing**: 128-bit unified IPv4-mapped-IPv6 flow identification across all L3/L4/L7 pipelines.

---

## Phase 2: High-Throughput IPC & Vector Acceleration (v2.0) — [IN PROGRESS]
* [ ] **Shared Memory (SHM) Telemetry**: Replacement of IPC queues with a 1GB HugePages-backed shared memory ring buffer for zero-copy handoff to external telemetry consumers.
* [ ] **AVX-512 SIMD Acceleration**: Vectorization of user-space Welford moment accumulation and Shannon entropy computation using native AVX-512 SIMD registers.
* [ ] **High-Performance Binary Serialization**: Introduction of a zero-copy binary export format (FlatBuffers / Cap'n Proto) alongside the streaming CSV pipeline.
* [ ] **Expanded In-Kernel Dissectors**: Fast-path kernel dissection modules for Memcached, CLDAP, and CoAP protocols.

---

## Phase 3: Autonomous Mitigation & Distributed Telemetry (v3.0) — [PLANNED]
* [ ] **Distributed Multi-Node Scrubbing**: Distributed telemetry aggregation engine capable of correlating flow signatures across multi-datacenter leaf-spine fabrics.
* [ ] **In-Kernel Dynamic Mitigation (MAPE-K Closed Loop)**: Integrated feedback control loop configuring dynamic in-kernel `XDP_DROP` and `XDP_REDIRECT` rules based on real-time classification.
* [ ] **Hardware Offload (Zero-Copy AF_XDP & SmartNIC)**: Native driver-level zero-copy AF_XDP queues and SmartNIC firmware offload for line-rate 100G+ operations.

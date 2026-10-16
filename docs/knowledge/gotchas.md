# XFlowLyzer v1.0.0 — Engineering Gotchas & Kernel Troubleshooting

This document compiles non-obvious low-level systems behaviors, BPF verifier edge cases, and architectural learnings obtained during the development and benchmark validation of XFlowLyzer v1.0.0.

---

## 1. Native XDP Loading & VETH MTU Alignment
* **Symptom**: The kernel driver rejects XDP program attachment in native mode (`XDP_DRV`), returning `-EOPNOTSUPP` or peer MTU negotiation failures.
* **Root Cause**: Virtual Ethernet (`veth`) driver pairs require strictly symmetric MTUs across both endpoints. Furthermore, the MTU must not exceed the maximum packet buffer size that fits within a single page without multi-buffer frame allocation (`xdp_buff` linear headroom constraints).
* **Remedy**: Enforce strict MTU alignment to $1500\,\text{bytes}$ on both virtual interfaces prior to program attachment and before executing packet replay via `tcpreplay`:
  ```bash
  sudo ip link set dev veth0 mtu 1500
  sudo ip link set dev veth1 mtu 1500
  ```

---

## 2. Strict Pointer Bounds Checking & In-Kernel Verifier Proofs
* **Symptom**: Clang compiles the BPF object successfully, but the `bpf(BPF_PROG_LOAD)` syscall fails with safety verifier rejections (`invalid access to packet, mem at R1+offset`).
* **Root Cause**: The in-kernel BPF verifier does not permit arbitrary pointer arithmetic or indirect structure dereferences unless every access is bounded by explicit conditional checks against `ctx->data_end`. In variable-length protocols (IP options, TCP options, DNS compression pointers), pointer offsets derived from packet contents must be validated immediately prior to each read.
* **Remedy**: Always enforce adjacent boundary checks before dereferencing any parsed header:
  ```c
  if ((void *)(tcp + 1) > data_end) {
      return XDP_PASS;
  }
  ```
  For iterative Layer-7 parsing (such as DNS label skipping), bounded iteration loops must be statically unrolled using `#pragma unroll` with rigid upper bounds to satisfy the verifier's bounded complexity ceiling ($1\,\text{million}$ instructions).

---

## 3. Machine Learning Topological Leakage (`IDENTITY_DROP`)
* **Symptom**: Downstream machine learning classifiers (e.g., Random Forest, XGBoost) achieve near-perfect evaluation metrics ($F_1 = 1.0000$) on raw exported telemetry, but collapse completely when tested against out-of-distribution network topologies.
* **Root Cause**: Spatial and topological data leakage occurs when models learn static identifier fields (such as static source/destination IPs, MAC addresses, ephemeral ports, or monotonic sequence counters) instead of invariant statistical traffic dynamics.
* **Remedy**: Enforce mandatory sanitization via `IDENTITY_DROP` across all identification features before feature normalization and model training:
  ```python
  IDENTITY_COLUMNS = [
      'flow_id', 'timestamp', 'src_ip', 'dst_ip', 'src_port', 'dst_port',
      'src_mac', 'dst_mac', 'protocol', 'ip_ver', 'eth_proto',
      'traffic_class', 'flow_label', 'TunnelId', 'TunnelType'
  ]
  features_clean = dataset.drop(columns=IDENTITY_COLUMNS, errors='ignore')
  ```

---

## 4. Stationary RSS Memory Stability & Map Pre-Allocation
* **Symptom**: Daemon Resident Set Size (RSS) memory fluctuates unpredictably or exhibits latency spikes during volumetric packet floods.
* **Root Cause**: On-demand dynamic memory allocation in kernel hash maps (`BPF_F_NO_PREALLOC`) introduces non-deterministic page allocation overhead within atomic network context, causing memory fragmentation and vulnerability to volumetric state exhaustion attacks (e.g., SYN Floods).
* **Remedy**: Disable `BPF_F_NO_PREALLOC` across all state-tracking BPF maps, forcing static full pre-allocation of the entire hash space at load time. In user space, allocate all circular SPSC queues, worker buffers, and telemetry hash tables during the initialization phase (`auto_tune()`), locking physical RSS memory consumption at a stationary $128.52\,\text{MB}$ ($\sigma^2_{RSS} = 0$).

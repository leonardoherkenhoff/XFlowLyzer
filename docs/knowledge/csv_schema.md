# XFlowLyzer v1.0.0 — Telemetry Schema & Feature Dictionary

The continuous telemetry stream produced by XFlowLyzer v1.0.0 is serialized into a structured **495-feature telemetric vector**, organized across the following dimensions:

---

## 1. Flow Identification & L2/L3/L4 Metadata (22 Features)
Raw header attributes captured for unique flow identification and baseline volumetrics:
* **Identification 5-Tuple & Protocol Headers**: `flow_id`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`, `ip_ver`, `eth_proto`, `traffic_class`, `flow_label`, `src_mac`, `dst_mac`, `timestamp`
* **Baseline Volumetrics**: `duration`, `PacketsCount`, `FwdPacketsCount`, `BwdPacketsCount`, `TotalBytes`, `FwdBytes`, `BwdBytes`, `FwdBwdPktRatio`, `FwdBwdByteRatio`

---

## 2. High-Resolution Statistical Metric Families (160 Features)
Comprises **16 morphological metric families**. Each family exports **10 statistical moments and dispersion measures**, computed online and iteratively via Welford's algorithm and dynamic $P^2$ quantile tracking:
* **Metrics per Family**: `[Family]_Max`, `[Family]_Min`, `[Family]_Mean`, `[Family]_Std`, `[Family]_Var`, `[Family]_Median`, `[Family]_Skew`, `[Family]_Kurt`, `[Family]_CoV`, `[Family]_Mode`

### Metric Families:
1. `Tot_Pay`: Aggregate flow payload size.
2. `Fwd_Pay`: Forward direction payload size.
3. `Bwd_Pay`: Backward direction payload size.
4. `Tot_Hdr`: Aggregate L3/L4 network and transport header size.
5. `Fwd_Hdr`: Forward direction header size.
6. `Bwd_Hdr`: Backward direction header size.
7. `Tot_IAT`: Aggregate packet inter-arrival time (IAT).
8. `Fwd_IAT`: Forward packet inter-arrival time.
9. `Bwd_IAT`: Backward packet inter-arrival time.
10. `Tot_DeltaLen`: Aggregate packet length variation.
11. `Fwd_DeltaLen`: Forward packet length variation.
12. `Bwd_DeltaLen`: Backward packet length variation.
13. `Win`: TCP transmission window size and fluctuation.
14. `IpId`: IPv4 identification field variance and anomaly tracking.
15. `Frag`: IP fragmentation state and offset counters.
16. `TTL_Var`: Time-to-Live field variability and topology fingerprinting.

---

## 3. L4 Fingerprinting & TCP State Dynamics (26 Features)
Transport-layer behavioral metrics for port scanning, state exhaustion, and handshake analysis:
* `FwdInitWinBytes`, `BwdInitWinBytes`: Initial TCP receive window sizes.
* **Directional TCP Flag Counters**: `FIN_Cnt`, `FIN_Fwd_Cnt`, `FIN_Bwd_Cnt`, `SYN_Cnt`, `SYN_Fwd_Cnt`, `SYN_Bwd_Cnt`, `RST_Cnt`, `RST_Fwd_Cnt`, `RST_Bwd_Cnt`, `PSH_Cnt`, `PSH_Fwd_Cnt`, `PSH_Bwd_Cnt`, `ACK_Cnt`, `ACK_Fwd_Cnt`, `ACK_Bwd_Cnt`, `URG_Cnt`, `URG_Fwd_Cnt`, `URG_Bwd_Cnt`, `ECE_Cnt`, `ECE_Fwd_Cnt`, `ECE_Bwd_Cnt`, `CWR_Cnt`, `CWR_Fwd_Cnt`, `CWR_Bwd_Cnt`.

---

## 4. Application Layer (L7) & Session Timing (27 Features)
Application-layer protocol telemetry and session state tracking:
* **Payload Entropy**: `PayloadEntropy` (computed iteratively across packet payload bytes).
* **Control Protocol Telemetry**: `IcmpType`, `IcmpCode`, `TTL`, `IcmpEchoId`.
* **Session Inactivity Dynamics**:
  * `Active`: 10 statistical moments (`Max` to `Mode`) for active transmission sub-intervals.
  * `Idle`: 10 statistical moments (`Max` to `Mode`) for idle periods between packet bursts.

---

## 5. Volumetric Throughput & Bulk Transfer Rates (22 Features)
Traffic throughput dynamics and bulk transmission statistics:
* **Throughput Rates**: `BytesRate`, `FwdBytesRate`, `BwdBytesRate`, `PacketsRate`, `FwdPacketsRate`, `BwdPacketsRate`, `DownUpRatio`.
* **Bulk Transfer Counters**: `FwdBulkBytes`, `FwdBulkPkts`, `FwdBulkCnt`, `BwdBulkBytes`, `BwdBulkPkts`, `BwdBulkCnt`.
* **Application Infrastructure & Overlay Metadata**: `DNSAnswerCount`, `DNSQueryType`, `DNSQueryClass`, `TunnelId`, `TunnelType`, `NTP_Mode`, `NTP_Stratum`, `SSDP_Method`, `SNMP_PDU_Type`.

---

## 6. High-Fidelity Morphological Histograms (240 Features)
Empirical geometric distributions based on packet size frequency counting, partitioned into 20-byte directional bins spanning $0$ to $1600\,\text{bytes}$:
* `Hist_Tot_0` through `Hist_Tot_79`: Aggregate flow packet size histogram.
* `Hist_Fwd_0` through `Hist_Fwd_79`: Forward packet size histogram.
* `Hist_Bwd_0` through `Hist_Bwd_79`: Backward packet size histogram.

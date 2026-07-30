---
title: Code sandbox
kind: Worker
technology: go-judge
---

## 🛠️ Code sandbox

The only place untrusted code ever executes — and the component the threat model is written
against: **assume the code is hostile.**

**Isolation, layered (each layer assumes the previous one failed)**

1. Fresh Linux namespaces (PID, mount, network, IPC) + cgroup quotas per execution: hard CPU
   ceiling, memory ceiling, wall-clock timeout, output cap.
2. **No network interface at all** — kills exfiltration, coin-mining, and staged payloads in one
   stroke.
3. Its own pod on a tainted, dedicated node pool with `NetworkPolicy` egress-deny: a full container
   escape lands somewhere with nothing to read and nowhere to call.
4. At fleet scale, a gVisor/Firecracker-class outer wall — the ratchet rule: capacity increases
   ship with matching isolation hardening, in the same step.

**Capacity (the napkin math)**

~7 runs/s at the 1M-MAU peak × ~1 CPU-second per run → 10–20 dedicated cores with 5× burst
headroom. Autoscales on in-flight runs; **warm process pools per language** keep p95 interactive
(cold interpreter start is the latency budget's enemy); per-user concurrency caps stop one griefer
from occupying the fleet. The only cost line that grows superlinearly with engagement.

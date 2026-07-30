---
title: Coordination service
kind: Coordination service
technology: ZooKeeper / etcd
---

## 🗳️ Coordination service

The **Coordination service** answers exactly one question — *who is the scheduler right now?* — and answers it **linearizably**: all nodes agree on the leaseholder however the network mangles timing, which is what consensus-backed services like ZooKeeper and etcd exist to provide. DDIA lists *"choosing a leader among the instances of a job scheduler"* as a canonical use case for exactly this component.

**Responsibilities**

- Grant the scheduler **lease** as an ephemeral node tied to a heartbeat session: the winner ticks and renews; if its heartbeats stop past the session timeout, the lease releases automatically and a standby takes over. Failure detection is built in — no extra monitor.
- Issue a **monotonic epoch** with every grant (ZooKeeper's `zxid`, etcd's revision — consensus algorithms call it a term). This is the fencing token: the lease says who *should* act, the epoch lets downstream stores reject whoever *shouldn't anymore*.
- Stay small: a fixed 3-or-5-node cluster regardless of how large the scheduler and worker fleets grow — coordination traffic here is lease renewals, not per-job writes.

**Where it breaks.** The lease alone does not prevent double-firing — that's the famous hole. A GC-paused leader can be declared dead, lose the lease, and resume still believing it holds the crown. The coordination service cannot stop the zombie from *acting*; it can only ensure the zombie's epoch is stale so the executions DB bounces its writes. Never let a design review end at *"we use ZooKeeper for locking"* — the epoch, carried on every side effect, is the actual guarantee.

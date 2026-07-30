---
title: LeaderLease
kind: Code
technology: Python
---

## 🧩 LeaderLease

**LeaderLease** owns `is_leader() bool` and `epoch() int` — the scheduler's claim to be *the* scheduler, and the number that makes that claim safe to be wrong about. It acquires the lease in the coordination service, renews it on a heartbeat session, and exposes the lease's monotonically increasing epoch (ZooKeeper's `zxid`, etcd's revision) so every side effect the tick performs can carry it as a **fencing token**.

**Responsibilities**

- Race for the lease as an ephemeral node; hold leadership only while renewals succeed, so a crashed leader's lease lapses on its own and a standby takes over.
- Gate the tick: WindowPoller runs only while `is_leader()` is true.
- Surface `epoch()` for the Dispatcher to stamp on every enqueue and every conditional state write.

**The invariant it maintains:** **a stale epoch is rejected downstream — the double-fire guard.** `is_leader()` alone is a lie waiting to happen: a GC pause, VM migration, or page fault can freeze the process *between the check and the act*; the lease expires, a new leader starts ticking, and the old one resumes — unaware any time passed — and finishes its tick. That zombie cannot be prevented, only defanged: its writes carry epoch *n* while the store has already seen *n+1*, so they bounce. The lease decides who should act; the epoch is what actually stops whoever shouldn't anymore.

**Where it breaks.** Fencing protects only stores that check the token — whatever the zombie pushed into the queue before bouncing is a duplicate delivery, absorbed by ExecutionClaimer. Lands in the forthcoming POC at `06-case-studies/examples/job-scheduler/scheduler/leader_lease.py`.

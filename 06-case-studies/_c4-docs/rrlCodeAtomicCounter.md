---
title: AtomicCounter
kind: Code
technology: Python + Redis Lua
---

## 🧩 AtomicCounter

**AtomicCounter** is the race-killer. The natural implementation — read the bucket (`HMGET`), compute the refill, decide, write back in a `MULTI`/`EXEC` transaction — is wrong in a precisely nameable way: the transaction makes the *writes* atomic, but the read happened outside it. Two requests for the same key land on two gateways in the same millisecond; both read one token, both allow, both write back a bucket decremented from the state *they* read. That anomaly is a **lost update** — two concurrent read-modify-write cycles where one modification overwrites the other as if it never happened — and counter increments are its canonical victim.

**Responsibilities**

- `check_and_increment(key, window) → (allowed, remaining)`: ship the *entire* read-refill-decide-write sequence to Redis as a Lua script invoked via `EVALSHA`, executing as one indivisible step with no other command interleaving.
- Set `EXPIRE` (~1 hour, refreshed per check) inside the same script, so idle keys self-delete instead of leaking.
- Keep the state round-trip to exactly one, over pooled connections — the check's share of the < 5 ms budget is network, not Redis.

**The invariant it protects:** the atomic boundary covers the **whole read-modify-write cycle** — one atomic round-trip kills the race. Concurrent checks serialize inside Redis; the second sees the first's decrement. No bigger transaction fixes a gap that begins at the read; moving the cycle *into* the store does.

**Where it breaks.** Atomicity holds *on the shard's primary*; replication is async, so a failover can resurrect recently spent tokens — bounded over-admission, accepted knowingly. Implemented in the forthcoming POC at `06-case-studies/examples/rate-limiter/app/atomic_counter.py`.

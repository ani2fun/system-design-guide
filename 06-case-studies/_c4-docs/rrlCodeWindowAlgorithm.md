---
title: WindowAlgorithm
kind: Code
technology: Python
---

## 🧩 WindowAlgorithm

**WindowAlgorithm** is the algorithm zoo behind one interface: `check(key, rule) → Decision`. It's a strategy class because the algorithms differ in **what they promise, not just what they cost** — each has its own *burst personality*, and choosing one is choosing a contract:

- **Fixed window** promises only *"no window exceeds N"* — and its personality is the **boundary burst**: spend the full limit at 12:00:59 and again at 12:01:00, and 200 requests pass in two seconds against a *"100/minute"* rule. No window exceeded its count; the rule as a user understands it was violated by 2×.
- **Sliding window counter** smooths that boundary by weighting the previous window's counter — but it *assumes even spread*; front-loaded traffic skews the estimate. An approximation, and the senior move is saying so.
- **Token bucket** (this design's pick) makes burst a **first-class dial, not a bug**: capacity *B* is the burst, refill rate *r* the sustained rate — *"burst to 100, sustain 10/minute"* — fitting naturally bursty API traffic. Its quirk: idle clients always hold a full bucket, so every quiet client is entitled to one burst.

**Responsibilities**

- Translate the resolved rule into algorithm parameters and delegate the actual state mutation to `AtomicCounter` — this class computes *nothing* against local state, because shared-not-local counters are the design's first law.
- Return the full decision payload: allowed, remaining, reset, retry-after.

**Where it breaks.** Only by misuse: implementing the read-refill-decide logic *here*, in application code, reopens the read-modify-write gap that `AtomicCounter` exists to close. Implemented in the forthcoming POC at `06-case-studies/examples/rate-limiter/app/window_algorithm.py`.

---
title: RuleResolver
kind: Code
technology: Python
---

## 🧩 RuleResolver

**RuleResolver** answers *"which policy governs this key?"* — mapping a user ID, IP, or API key to the applicable rule: tier, limit, window or refill rate. Where several rules cover one request (per-user, per-IP, per-endpoint), it resolves to the **most restrictive** — Alice with budget left is still blocked if her IP hit its cap.

**Responsibilities**

- `resolve(key) → Rule`: look up the governing rule from a **local in-memory cache**, refreshed from the rule store asynchronously (polling, ~every 30 s).
- Layer rules correctly: evaluate every matching scope, enforce the tightest.
- Hand `WindowAlgorithm` the resolved parameters — algorithm choice, limit, window/refill — so policy and mechanism stay separate concerns.

**The invariant it protects:** the decision path **never blocks on the rule store**. Rules are configuration — tiny, read-heavy, rarely changed — so a check must never spend its < 5 ms budget on a config lookup, and a rule-store outage must degrade rule *freshness*, never check *availability*. The cost of that invariant is honest and bounded: a rule change propagates in up to one polling interval (~30 s), which is the worst-case delay for an emergency limit cut — the number that motivates push-based config when seconds matter.

**Where it breaks.** Stale-cache edges: a limiter that can't reach the rule store keeps enforcing its last-known rules — usually the right failure mode, but it means a bad rule also *lingers* for the polling interval after the fix. Versioned rules and rollback exist for exactly this. Implemented in the forthcoming POC at `06-case-studies/examples/rate-limiter/app/rule_resolver.py`.

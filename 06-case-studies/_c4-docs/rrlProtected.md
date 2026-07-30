---
title: Protected services
kind: Service
technology: Internal APIs
---

## ⚙️ Protected services

The **Protected services** are the reason the limiter exists — the downstream application fleet whose capacity, database connections, and latency SLOs the limiter defends from traffic they never agreed to serve. In this design they are deliberately passive: by the time a request reaches them, the rate-limit decision is already made and paid for at the edge.

**Responsibilities**

- Serve only *admitted* traffic: the gateway forwards allowed requests and turns denials around as 429s at the edge, so a rejected request costs this fleet nothing — no thread, no connection, no database read. That asymmetry is the entire argument for edge placement.
- Stay out of the limiting business: no per-service counters, no local hash maps. Any counting done here re-derives the per-node accuracy bug the design exists to kill.
- Provide the *demand signal* for tuning: these services' capacity and high-percentile legitimate usage are what the rule store's limits should be set just above.

**Where it breaks.** In exactly one scenario — the limiter's own failure. If Redis goes down and the platform failed *open*, the flood these services were being protected from arrives at the worst possible moment, because limiter failures correlate with traffic spikes. That correlation is why this design fails **closed**: brief 429s at the edge beat cascading collapse here. The monitoring corollary: an alert on entering fail-open mode, because from this fleet's perspective a silently disabled limiter is indistinguishable from a healthy one — until it isn't.

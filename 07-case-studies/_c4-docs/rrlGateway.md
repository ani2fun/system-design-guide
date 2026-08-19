---
title: API gateway (enforcement point)
kind: API gateway
technology: Gateway middleware
---

## 🚪 API gateway (enforcement point)

The **API gateway** is where the limiter's placement decision landed — the most common production pattern, and the one that makes rejected traffic *free*. Every request passes here before routing, so a 429 turns around at the edge and the application fleet never sees it; the alternative placements (in-process counters, a dedicated limit service) either re-derive the per-node accuracy bug or add a network hop and a new critical service to every request.

**Responsibilities**

- Extract the limiting key from what the HTTP request exposes: auth token → user ID, `X-Forwarded-For` → IP, `X-API-Key` — and call the limiter middleware before any routing decision.
- Forward allowed requests with `X-RateLimit-Limit` / `Remaining` / `Reset` attached; answer denials immediately with **429 + Retry-After** — reject, never queue.
- Keep the check inside its single-digit-millisecond budget: **pooled, persistent connections** to Redis (a fresh TCP handshake costs 20–50 ms — several times the entire < 5 ms budget on its own) and **geographic co-location** with the counter shards.

The placement's honest limitation is *context*: the gateway sees only the HTTP request, so *"premium users get 10× limits"* works only if the tier is readable from it — e.g. encoded in the JWT.

**Where it breaks.** When Redis is unreachable, this container is where the fail-open/fail-closed stance executes. This design fails **closed**: limiter failures correlate with traffic spikes, so the moments you'd fail open are precisely the moments it's most dangerous.

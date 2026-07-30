---
title: Calling client
kind: Actor
technology: HTTP clients · SDKs · scripts
---

## 👤 Calling client

The **Calling client** is any API consumer — a mobile app, a partner integration, a broken retry loop, a scraper, a DDoS source. The limiter's founding assumption is that it *cannot tell these apart by intent*: it counts requests per key (user ID, IP, or API key) and enforces the rule, treating intent as unknowable.

**Responsibilities**

- Identify itself through whatever the gateway can extract: an auth token (user ID), `X-Forwarded-For` (IP), or `X-API-Key`.
- Honor the contract's other half when denied: a **429 Too Many Requests** with `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and `Retry-After` — enough to back off intelligently instead of hammering with doomed retries.
- Well-built SDKs go further and rate-limit *client-side*, reading `Remaining` and slowing down before hitting the wall — a genuine complement, never a substitute, since clients can't be trusted for security.

**Where it breaks.** The adversarial tail: a client that ignores every header and retries in a tight loop becomes a **hot key**, concentrating load on one Redis shard while every answer is *"no"* — checks cost capacity even when the verdict is deny. That's why the design pairs limits with an automatic blocklist for repeat offenders and upstream DDoS protection: past a certain rate, the cheapest correct answer is not counting at all.

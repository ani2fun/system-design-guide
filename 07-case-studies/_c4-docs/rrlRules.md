---
title: Rule store
kind: Relational database
technology: Config DB
---

## 🗄️ Rule store

The **Rule store** holds the policies — which clients and endpoints a rule covers, the limit, the window or refill rate: *"Search API: 10/minute per IP."* Rules are configuration, not data: tiny, read-heavy, rarely changed — which is why they are the one piece of state deliberately kept **off** the decision path. Limiters cache rules locally and refresh them asynchronously (polled every ~30 s); a check never waits on this container.

**Responsibilities**

- Express layered policy the way real platforms do: per-user, per-IP, global, and per-endpoint rules evaluated together, **most-restrictive wins** — search runs tight, cheap reads run loose, premium tiers buy higher ceilings.
- Support rule changes *without deploys*: limits change under pressure — a launch needs a temporary raise, an attack an emergency cut. Polling is the default shape; push (pub/sub) earns its complexity only when seconds matter, e.g. active security incidents.
- Version rules so a bad limit can be rolled back — a mistyped rule is a self-inflicted outage, and the rollback path is part of the design.

**Where it grows.** Tuning limits is ongoing operational work, not a launch-time constant: the rules table encodes a guess about what *"abusive"* means, and production teaches the real answer — start permissive, watch the per-key distribution, ratchet down. The ~30 s polling interval is the worst-case delay for an emergency change; if that's too slow for your threat model, this container grows a push channel.

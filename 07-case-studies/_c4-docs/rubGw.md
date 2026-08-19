---
title: API gateway
kind: API gateway
technology: Gateway
---

## 🚪 API gateway

The **API gateway** fronts both apps and terminates the realtime channels — one entry point, two radically different traffic shapes behind it. Rider traffic is low-rate and transactional (a fare quote, a ride request, an occasional cancel); driver traffic is the ping firehose, high-frequency and fire-and-forget. The gateway's most important routing decision is keeping those apart: pings go straight to the Location service's dedicated write path, ride requests go to the Matching service, and neither queue ever blocks the other.

**Responsibilities**

- Authenticate every request and attach identity server-side — the client never supplies a `userId`, a timestamp, or (above all) a fare amount; anything the client could edit, the gateway's session context or a server-side lookup provides instead.
- Rate-limit per client, which matters most on the ping path: a misbehaving driver app re-sending at 10× the interval is throttled at the edge, not absorbed downstream.
- Route by traffic class: high-frequency location writes to the Location service, ride lifecycle calls to Matching and Trip, and hold the persistent connections the Realtime channel pushes through.

**Where it grows.** Horizontally and statelessly — the gateway holds no ride state, so instances multiply behind a load balancer as the fleet grows. The pressure point is connection count, not CPU: every online driver and every waiting rider holds a realtime connection, so the gateway tier's sizing follows the fleet, not the request rate.

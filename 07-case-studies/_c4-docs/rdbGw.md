---
title: LB / API gateway
kind: API gateway
technology: L7 gateway
---

## 🚪 LB / API gateway

The **LB / API gateway** fronts the metadata plane — and the most important fact about it is what *doesn't* pass through: file bytes. Only fingerprints, chunk manifests, share operations, and the change feed cross this hop; the heavy tonnage flows client ↔ blob storage on presigned URLs, entirely outside this container's world.

**Responsibilities**

- Terminate TLS, authenticate the session token/JWT riding in headers (identity never travels in request bodies), and route metadata operations to File Service instances.
- Spread load across a stateless File Service fleet — trivially, because no request here carries payload weight or session affinity.
- Enforce the boring edge concerns: rate limits, request-size limits, timeouts.

That last point is why this design works at all. Default request-body limits — under 2 GB on Apache/NGINX, as low as 10 MB on managed API gateways — would strangle any architecture that tried to POST a 50 GB file through here. Rather than fighting those limits, the design embraces them as a feature: the gateway *should* refuse large bodies, because a large body arriving here means a client is misbehaving. Every legitimate request through this hop is small, fast, and cheap — a fingerprint list, a manifest commit, a share grant.

**Where it breaks.** It mostly doesn't — that's the point of keeping it byte-free. Its failure modes are the generic L7 ones (connection exhaustion under a reconnect storm, misconfigured timeouts killing slow metadata queries), not anything this design created. If this gateway is your bottleneck, something upstream has leaked bytes into the metadata plane.

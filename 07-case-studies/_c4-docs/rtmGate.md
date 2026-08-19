---
title: API gateway + waiting room
kind: API gateway
technology: Gateway + queue
---

## 🚪 API gateway + waiting room

**Admission control** — the answer to why *"autoscale the booking path"* fails an on-sale. The spike is a step function that outruns any autoscaler; more booking servers just add transactions converging on the same ~50k ticket rows; and even infinite capacity leaves the seat map a demoralizing blur. So instead of absorbing the crowd, this container *meters* it.

**Responsibilities**

- Route ordinary traffic: browse and search requests to the browse service, admitted checkout traffic to the booking service.
- During an on-sale (admin-enabled per event), place arriving fans in a **virtual waiting room** — a queue with a connection per waiting user — and dequeue at a controlled rate.
- Push queue position and estimated wait to those in line; opaque waits convert demand into rage.
- Record admission so the booking path can enforce that only admitted users book.

The quiet win: the seat map an *admitted* user sees is fresh enough to act on, because only a few thousand others are looking at it. Admission control is a product-shaped solution to a problem (*"render 10M live seat maps"*) that has no technical one.

**Where it breaks.** The queue is a fairness and abuse surface — bots join from thousands of identities to flip inventory, so entry needs rate limits, verification gating, and anomaly scoring. And holding millions of live connections is itself a scaling problem; the trade is deliberate: cheap connection state at the edge instead of contention in the core.

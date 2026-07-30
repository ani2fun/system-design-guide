---
title: Advertiser
kind: Actor
technology: Analytics dashboard
---

## 👤 Advertiser

The **Advertiser** is the party the numbers are *for* — and the party that pays based on them, which is what turns this from an analytics exercise into an integrity problem. A dashboard that lags a few seconds is annoying and self-heals; an invoice computed from a wrong count stays wrong forever unless something detects and repairs it. The advertiser's two demands pull the architecture in opposite directions: sub-second queries over the last minute of traffic (speed), and counts trustworthy enough to be billed against (truth). The design refuses to pick one — the stream path serves the dashboard, the batch reconciliation path backs the invoice.

**Responsibilities**

- Query aggregated click metrics through the Metrics API at **1-minute minimum granularity**, expecting sub-second answers — which is only possible because the rows are pre-aggregated, not computed at query time.
- Accept that the current minute is **provisional**: open windows flush early and incomplete, and late-arriving clicks can revise an already-published number via correction upserts.
- Dispute invoices — the adversarial read path. *"The dashboard says so"* is not an answer; the immutable raw log is what turns a dispute into a replay-and-compare procedure instead of a negotiation.

**Where it grows.** Today's surface is fixed-granularity counts per ad. The pressure is toward richer slices — geography, device, campaign roll-ups — each of which multiplies the pre-aggregation keyspace and pushes the OLAP store toward a real real-time analytics engine.

---
title: Fan
kind: Actor
technology: Web / mobile client
---

## 👤 Fan

The **Fan** browses events, joins on-sales, and books seats — and the single most important fact about them is that they arrive in crowds. When a popular event opens, ~10 million fans show up in the same minute for roughly 50k seats: a 200:1 demand-to-supply ratio, meaning over 99% of them *cannot possibly buy anything*.

**Responsibilities**

- Browse event pages and search the catalog — the 100:1 read-heavy traffic that dominates the system.
- Join an on-sale: queue in the waiting room, watch a live seat map, pick a seat.
- Book: hold a seat, spend human minutes typing payment details, confirm.

That human think-time is a design input, not a detail. A fan holds a seat for up to ten minutes while deciding — which is why the design uses TTL holds (a lease that self-releases when the fan wanders off) instead of a database lock pinned across checkout.

**Where it breaks.** Not every *"fan"* is a fan: bots join the queue from thousands of identities to flip inventory, which makes the waiting-room entrance a fairness and abuse surface — rate limits, verified-fan gating, anomaly scoring. And a fan who loses a race is a fan you must fail *visibly and politely*: *"seat is held, pick another"* beats a mystery error at the payment page.

---
title: Retry & DLQ
kind: Message queue
technology: Queue (DLQ)
---

## 📮 Retry & DLQ

**Retry & DLQ** is where the crawler's optimism ends and its accounting begins. Fetching is the failure-richest stage in the system — servers down, pages moved, connections that trickle — so failure handling is designed, not hoped for. Transient failures get **exponential backoff**: a failed message returns to visibility after 30 seconds, then 2 minutes, 5 minutes, up to 15 — the queue's own redelivery machinery doing the retrying, no hand-rolled timer that a crash would lose.

**Responsibilities**

- Bound the retries: after **5 attempts** (the queue's receive count), stop. Retries without a ceiling are how one bad page eats a fleet.
- Quarantine **poison messages**: the malformed HTML that crashes its parser on every attempt, the 2 GB *"page"*, the one-byte-per-second server. Without a DLQ these would redeliver in a loop forever — wasting resources or blocking progress; moving them aside unblocks the pipeline.
- Be the ledger of the written-off web: a URL landing here means the site is declared offline and unscrapable — a *decision*, recorded, not a silent drop.

**Where it breaks.** A DLQ that nobody watches is just a slower way to lose data — it exists to be **monitored**, and its depth is the operator's direct gauge of how much web the crawl is abandoning. A sudden climb is a signal worth triaging: one distressed megasite, an IP-reputation problem on our side, or a parser bug masquerading as a hostile internet.

---
title: Inbox store
kind: Wide-column store
technology: Wide-column store
---

## 🧱 Inbox store

The **Inbox store** is where durability lives — the only place in the design that promises a message won't be lost. It is a per-*client* durable message queue: one row per undelivered message per recipient device, written inside the send transaction (that commit is what the sender's *"sent"* tick means), and **deleted the moment the device acks**.

**Responsibilities**

- Hold one Inbox row per recipient *client* — per device, not per user, because your phone acking a message says nothing about the laptop asleep in a bag.
- Survive the recipient being offline for days; on reconnect, the client drains its rows as replayed `newMessage` pushes, each deleted on ack.
- Age out anything unacked after 30 days via a sweep job.

Why drain-and-delete: this is the classic message-broker model — hold until acknowledged, delete on ack, deliberately unsuitable for long-term storage. Here that *"unsuitability"* is the *requirement*, achieved for free: the server holds a message exactly as long as necessary and not a moment longer. Delivery **is** deletion — the retention rule and the delivery mechanism are one thing seen from two sides.

The delete-on-ack loop is also the exactly-once construction's second half: a crash between push and delete means the row survives and the message replays — a missing ack *must* trigger redelivery, or crashes lose messages — and the client's dedup-by-message-id absorbs the duplicate.

**Where it grows.** Linearly with group fan-out: one message to a full 100-person group writes up to ~300 rows (99 recipients × ~3 devices) inside one transaction. The 100-member cap is what keeps that write amplification — and the transaction's failure surface — bounded.

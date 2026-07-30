---
title: Delay queue
kind: Message queue
technology: SQS-style queue
---

## 📮 Delay queue

The **Delay queue** is the second layer of the two-layer core, and it exists because polling can't be both cheap and precise: a 2-second poll at 10k executions/second fetches ~20k rows per query and makes the poll period the precision ceiling, melting the database first. So the scheduler polls a lazy 5-minute window, and the queue converts *"rows due soon"* into *"messages that appear exactly on time"* — **the queue holds the countdown**, per-message delay = due − now, instead of anything busy-waiting.

**Responsibilities**

- Release each message at its due moment (native per-message delay), giving second-level precision decoupled from poll frequency.
- Run the **visibility timeout** protocol: on delivery the message is hidden (~30 s); the worker extends the window by heartbeating; silence means the window lapses and the message reappears for a healthy worker — failure detection with no extra infrastructure.
- Deliver **at-least-once**: the broker cannot know whether a missing ack means *"died before the work"* or *"died after, before the ack,"* so it redelivers in both cases. Duplicates are the worker's problem by design.
- Shunt a message to the DLQ after max receives — the poison-job circuit breaker.

Note the family: a per-message broker with acks, *not* a log. A Kafka-style log delivers in append order, so a job due in 30 seconds would sit behind five minutes of earlier messages; here order rides in the delay, not the log.

**Where it breaks.** Quotas before architecture: an SQS-style default of ~3k messages/second (with batching) needs a quota increase at 10k/s. And redelivery reorders — harmless only because executions are independent and self-timed.

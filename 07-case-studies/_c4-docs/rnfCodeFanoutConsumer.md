---
title: FanoutConsumer
kind: Code
technology: Python
---

## 🧩 FanoutConsumer

**FanoutConsumer** is the queue discipline of the fan-out pipeline: the loop that turns *"there's an event on the stream"* into *"TimelineFanout has fully handled it,"* without ever losing a post.

**Responsibilities**

- `run()`: consume `{postId, authorId}` events from the **fan-out queue** (Redis Stream consumer group) in a long-lived loop.
- `handle(event)`: pass each event to **TimelineFanout**, and acknowledge the event only *after* the fan-out completes.
- On crash or timeout, let the queue redeliver the unacknowledged event to another consumer — at-least-once, never at-most-once.

The ack-after-processing ordering is the entire class. Acknowledge first and a crash mid-fan-out silently loses deliveries — and a materialized timeline is never reconciled, so a lost delivery is a post that *permanently* never appears for some followers. Acknowledge after, and a crash means the event is processed again — duplicates instead of holes. The design chooses duplicates deliberately, because the downstream insert is idempotent: redelivery converges to the same timeline, which is how at-least-once plus idempotency composes into the effectively-exactly-once pipeline the fault-tolerance requirement demands.

**The invariant it protects:** no post event is ever dropped — every event is either fully fanned out or redelivered; duplicates are permitted, holes are not.

**Where it breaks.** A poison event that fails every redelivery blocks its consumer forever without a dead-letter escape, and a slow celebrity-sized job holds its event unacknowledged long enough to look dead. Implemented in the forthcoming POC at `06-case-studies/examples/news-feed/worker/fanout_consumer.py`.

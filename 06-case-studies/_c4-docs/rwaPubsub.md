---
title: Pub/sub bus
kind: Event bus
technology: Redis pub/sub
---

## 🚌 Pub/sub bus

The **Pub/sub bus** answers the question the socket fleet can't: *which chat server holds Bob's connection right now?* Its trick is that nobody ever computes the answer — **the subscription itself is the registry.** When Bob's socket lands on server B, B subscribes to the topic `bob`; when any server accepts a message for Bob, it publishes to `bob`; Redis forwards to whoever is subscribed. Placement stays free, and scaling the fleet stops being a re-hashing event.

**Responsibilities**

- Keep a lightweight in-memory map from per-user topic to subscribed chat servers, updated as a side effect of connect/disconnect.
- Forward each published message to the subscribers of the recipient's topic — an extra single-digit-millisecond hop on the delivery path.

The lesson earns this rung by rejecting two others: a Kafka topic per user drowns in per-topic overhead (~50 KB × billions of users, and log brokers shard few-huge topics, not billions of tiny ones), and consistent hashing works but makes every fleet resize a delicate user-migration event.

The catch is printed on the tin: Redis Pub/Sub is **at-most-once**. No subscriber at publish time — recipient offline, server mid-restart — and the message is simply gone *from this layer*. That's fine, because durability never lived here: the Inbox row committed before the publish, and reconnect drains it. Buy the cheap lossy thing for the hot path; pay for durability exactly once, in storage.

**Where it breaks.** The all-to-all connection mesh doesn't disappear — it moves to chat-servers↔Redis-nodes. And any transient gap between a publish and a subscribe drops the push silently, which is why a periodic Inbox sweep backstops this bus.

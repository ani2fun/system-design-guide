---
title: "Kafka"
summary: "An append-only log split into partitions — how that one choice gives you ordering, replay and a hard ceiling on consumer parallelism, and what you must build yourself because Kafka won't."
essential: true
---

# 🪵 Kafka

> **Prerequisites:** [Queues & Brokers](/synapse/system-design-from-first-principles/building-blocks/queues-and-brokers), [Sharding & Consistent Hashing](/synapse/system-design-from-first-principles/distributed-data/sharding-and-consistent-hashing) | **You'll be able to:** explain why a consumer group can never have more workers than partitions; choose an `acks` setting and an offset-commit point and defend both; and build the retry path Kafka does not give you.

---

## 🧨 The problem (why this exists)

**A traditional message queue deletes a message once somebody has read it.**

That single behaviour decides a surprising amount. If the message is gone, a second team cannot consume the same stream, a bug fixed on Tuesday cannot be replayed over Monday's data, and the broker must track acknowledgement for every individual message.

Kafka makes the opposite choice: **reading does not delete**. Everything that follows — replay, independent consumers, the partition ceiling, the ordering rules — falls out of that one decision.

---

## 💡 Intuition first

**Think of a ship's logbook rather than an inbox.**

An inbox is a pile you work through and empty; once handled, an item is gone. A logbook is written in order, never erased, and any number of people read it at once — each keeping their own bookmark of how far they have got.

Kafka is the logbook. A producer appends to the end; a consumer reads forward and remembers its position. Two teams reading the same log do not interfere, because neither is consuming anything — they are reading at their own pace from their own bookmark.

<div style="border-left:4px solid #195045;background:rgba(25,80,69,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

💡 **The bookmark is the whole trick.** DDIA puts it exactly: the broker need only periodically record **consumer offsets** rather than acknowledge every message, because consumption is sequential — everything below the offset is processed, everything above is unseen <abbr title="(p. 498)">[i]</abbr>. One number replaces per-message bookkeeping.

</div>

**One logbook is not enough, so it is split.**

A single log lives on a single disk and is capped by it. Kafka shards a topic into **partitions**, each an independent append-only sequence <abbr title="(p. 496)">[i]</abbr>. That is what buys the throughput — and it is the source of every constraint below.

---

## ⚙️ How it works

### 🧱 Partitions, offsets and the ordering rule

Within one partition the broker assigns a monotonically increasing **offset**, and messages are **totally ordered**. Across partitions there is **no ordering guarantee at all** <abbr title="(pp. 496–497)">[i]</abbr>.

```d2
direction: right
classes: {
  client: {style: {fill: "#f3f4f6"; stroke: "#6b7280"}}
  svc:    {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  async:  {style: {fill: "#f3e8ff"; stroke: "#9333ea"}}
}
prod: "Producer\npartition key decides the partition" {class: client}
topic: "Topic: orders  ·  replication factor 3" {
  style: {stroke: "#9333ea"; stroke-dash: 4; fill: "#faf5ff"}
  p0: "partition 0  (leader)\n0 1 2 3 4 ->" {class: async}
  p1: "partition 1  (leader)\n0 1 2 ->" {class: async}
  p2: "partition 2  (leader)\n0 1 2 3 ->" {class: async}
}
foll: "Follower replicas\non other brokers" {class: async}
cg1: "Consumer group: billing\nat most 3 workers" {class: svc}
cg2: "Consumer group: analytics\nits own offsets, reads everything" {class: svc}
prod -> topic.p0: "key hash"
prod -> topic.p1
prod -> topic.p2
topic.p0 -> foll: "replicate; acks=all waits for these" {style.stroke-dash: 3}
topic.p0 -> cg1: "offset 4"
topic.p1 -> cg1
topic.p2 -> cg1
topic.p0 -> cg2: "offset 1 — its own bookmark"
```

This is the consequence people miss: **ordering is something you buy with the partition key**, not something the topic gives you. To keep a user's events in order, make the user ID the partition key <abbr title="(p. 498)">[i]</abbr>. Choose a random key and you have thrown ordering away.

Partition choice is also the single biggest performance lever. Even distribution across partitions is what turns partition count into real parallelism; a skewed key concentrates traffic on one partition and the rest idle.

### 👥 Consumer groups, and the ceiling they carry

A consumer group load-balances a topic across its members; two different groups each receive **every** message <abbr title="(p. 493)">[i]</abbr>. One mechanism covers both *"share the work"* and *"fan out to independent teams."*

But the balancing is coarse: whole partitions are assigned to members, so **the number of nodes sharing a topic is at most the number of partitions** <abbr title="(p. 497)">[i]</abbr>.

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **Partition count is a capacity decision you make early and regret late.** A topic with 6 partitions can never be consumed by more than 6 workers in a group, however far behind it falls. Adding partitions later is possible, but it changes which partition a key lands in — breaking the per-key ordering the partition key was chosen to provide.

</div>

### 🛡️ Durability: replication and the `acks` setting

Each partition is replicated across brokers: one **leader** takes writes, **followers** copy them. A replication factor of 3 is the common choice — two followers, so one broker can die and a follower is promoted with the data intact.

The producer's `acks` setting decides how much of that replication you wait for, and it is a direct latency-versus-durability dial:

| `acks` | The producer waits for | You lose a message when |
| --- | --- | --- |
| `0` | nothing — fire and forget | anything goes wrong at all |
| `1` | the leader's own write | the leader dies before followers copy it |
| `all` | every in-sync replica | you would need to lose every replica |

`acks=all` with replication factor 3 is the configuration people mean when they say Kafka has strong durability. It is not the default, and saying so unprompted is a cheap senior signal.

Kafka is built to stay up: a replicated partition survives broker loss, and availability is the property it protects hardest. Which makes *"what if the cluster goes down?"* the least interesting question you can be asked about it — **a consumer failing is far more likely**, and that is where the real design decisions live.

### 📍 When to commit the offset — the decision people get wrong

Committing an offset is the consumer saying *"I have processed this."* On restart it resumes from the last committed offset, so **offsets are recorded periodically and work done after the last commit is repeated** <abbr title="(p. 498)">[i]</abbr>.

That makes *when* you commit a real design choice:

- **Commit before doing the work** and a crash loses the message entirely — nobody will reprocess it.
- **Commit after the work is durable** and a crash merely repeats it, which is safe if the consumer is idempotent.

The second is almost always right, and it has a corollary worth carrying: **keep consumer work small**. The more a consumer does between commits, the more is redone after a failure. [The web crawler](/synapse/system-design-from-first-principles/case-studies/web-crawler) splits fetching from parsing for exactly this reason — so a crash mid-parse does not re-download the page.

### 🔁 Retries: the part Kafka does not give you

This is the gap that surprises people.

**Producer side, Kafka helps.** Producers retry automatically on transient network or broker errors. Enable **idempotent producer mode** alongside retries, or a retry that succeeded-but-looked-failed writes the message twice.

**Consumer side, Kafka gives you nothing.** There is no built-in redelivery or backoff — unlike <abbr title="Amazon Simple Queue Service — a managed queue that ships redelivery and dead-lettering as features">SQS</abbr>, which ships both. The standard pattern you build yourself:

1. The main consumer fails a message.
2. It publishes that message to a **retry topic**, consumed by a separate worker with backoff.
3. After N attempts, the message moves to a **<abbr title="Dead Letter Queue — a holding topic for messages that failed every retry, kept for inspection rather than dropped">DLQ</abbr>**, where an operator can inspect, fix or replay it.

DDIA notes the same mechanism: dead letter queues unblock consumers by moving the poison message aside, monitored so someone can drop, fix or reprocess it <abbr title="(p. 495)">[i]</abbr>. This is a legitimate reason to pick a managed queue instead — if redelivery and a dead-letter path are most of what you need, <abbr title="Amazon Simple Queue Service">SQS</abbr> hands you both with no machinery to write.

### ♻️ Retention makes replay possible — and bounded

The log is split into **segments**, and old segments are deleted or archived, making the log a bounded on-disk ring buffer that discards old messages when full <abbr title="(p. 498)">[i]</abbr>. The default retention is **7 days**, tunable by time or by bytes.

Two things follow. Replay is available for as long as retention holds, which is what lets you fix a consumer and re-run it over history. And a consumer that falls behind by more than the retention window **skips data permanently** — those messages are simply gone.

### 📦 Message size, and the blob anti-pattern

There is no hard message-size limit — it is configurable — but the practical guidance is to stay **under about 1 MB** for memory and network reasons.

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **Never put large blobs in Kafka.** The tempting version of [YouTube](/synapse/system-design-from-first-principles/case-studies/youtube) pushes uploaded videos into a topic so transcoding workers can pull them asynchronously. Don't. Put the video in object storage and publish a **pointer** — the object key — as the message. The message stays small, the log stays fast, and the blob lives where blobs belong. Kafka is a transport with a memory, not a filesystem.

</div>

Two more throughput levers are worth naming: **batching** — the producer accumulates records and ships them as one request — and **compression** (GZIP, Snappy or LZ4). Both trade a little latency and CPU for markedly better network utilisation.

---

## ⚖️ Trade-offs

| Option | Gives you | Costs you | Use when |
| --- | --- | --- | --- |
| **Log broker (Kafka)** | Replay, many independent consumers, high throughput, per-partition ordering | Partition count caps parallelism; retention windows; you build retry yourself | High throughput, ordering matters, more than one consumer |
| **Traditional queue (SQS, JMS/AMQP)** | Per-message acknowledgement, redelivery and dead-lettering out of the box, parallelism unbounded by shards | No replay; a message is gone once consumed | Expensive per-message work, retry semantics matter more than ordering |
| **`acks=all`, replication 3** | Survives a broker loss with no data loss | Higher write latency | Anything you cannot reconstruct |
| **`acks=1`** | Lower latency | A leader failure loses recent writes | Telemetry and metrics where some loss is tolerable |
| **More partitions** | A higher ceiling on consumer parallelism | More open file handles; slower rebalances | You expect consumer count to grow |

DDIA states the broader choice as a rule of thumb: JMS/AMQP style suits expensive-per-message work where ordering matters less; log-based suits high throughput with fast per-message processing where ordering is important <abbr title="(p. 497)">[i]</abbr>.

---

## 🔢 Numbers that matter

| Quantity | Value |
| --- | --- |
| Log-broker throughput | millions of messages/second, despite writing everything to disk <abbr title="(p. 497)">[i]</abbr> |
| Per-broker throughput | up to ~1M messages/second |
| End-to-end latency | 1–5 ms |
| Recommended message size | under ~1 MB |
| Default retention | 7 days |
| Common replication factor | 3 |
| Retention per broker | up to ~50 TB |
| Shard the cluster when | ~800k messages/second, or ~200k partitions |
| Max consumers in a group | **exactly the partition count** |

Per-broker rungs are `industry practice` figures from [Numbers Quick Reference](/synapse/system-design-from-first-principles/reference/numbers-quick-reference). The throughput claim is DDIA's, and the reason it surprises people is worth stating: sequential appends to disk are fast, and the disk is not the bottleneck people assume.

---

## 🏭 In production

**The failure that actually pages people is consumer lag.**

Lag is the gap between the newest offset and the consumer's offset. It is the most important Kafka metric because it becomes two different disasters depending on size: a small lag is latency, and a lag exceeding the retention window is **silent data loss**. Alert on lag as a *duration* — "40 minutes behind" means something to everyone; "12 million messages" means nothing without context.

**Rebalances are the other recurring pain.** When a consumer joins or leaves, partitions are reassigned across the group, and naive configurations stop the world while it happens. A consumer that takes too long between polls is declared dead, triggering a rebalance, which makes it slower, which triggers another — a feedback loop that looks like broker failure but is really a slow message handler.

**Where it sits in this book.** Kafka is the concrete instance behind [Queues & Brokers](/synapse/system-design-from-first-principles/building-blocks/queues-and-brokers) and [Stream Processing](/synapse/system-design-from-first-principles/building-blocks/stream-processing), the change-data-capture transport in [Event-Driven, CQRS, Outbox & CDC](/synapse/system-design-from-first-principles/patterns/event-driven-cqrs-outbox-cdc), and the ingestion spine of [the ad-click aggregator](/synapse/system-design-from-first-principles/case-studies/ad-click-aggregator).

---

## 🪤 Pitfalls & interview traps

- **Claiming Kafka gives you global ordering.** It gives per-partition ordering. Saying so unprompted is one of the cheapest senior signals available.
- **Assuming durability is on by default.** Strong durability is `acks=all` plus a replication factor above 1. Neither is the default.
- **Assuming consumer retries exist.** They don't. If you need redelivery and a dead-letter path, you build a retry topic — or pick a queue that ships one.
- **Putting blobs in the log.** Store the object, publish the pointer.
- **Adding partitions to fix lag without naming the cost.** It raises the ceiling *and* rehomes keys, breaking the ordering the partition key existed to protect.
- **Committing offsets before the work is durable.** That converts at-least-once into at-most-once, and the loss is silent.
- **Reaching for Kafka at low volume.** Below roughly 50k writes/second, a database table or a simple queue is less machinery — the same over-engineering trap as premature sharding.

---

## ✅ Check yourself

```quiz
{"prompt": "A topic has 6 partitions. You add a 10th worker to the consumer group to clear a backlog faster. What happens?", "options": ["All 10 workers share the load evenly, each taking part of every partition", "Only 6 workers get partitions; the other 4 sit idle", "Kafka automatically splits partitions to match the worker count", "The group rebalances into 10 partitions and throughput rises"], "answer": "Only 6 workers get partitions; the other 4 sit idle"}
```

```quiz
{"prompt": "A producer uses acks=1 with replication factor 3. The partition leader accepts a write, acknowledges it, then crashes before any follower copies it. What is the outcome?", "options": ["No loss — a follower is promoted and already has the message", "The message is lost, because the producer was told it succeeded before replication happened", "The producer automatically resends it when the new leader is elected", "The message is duplicated across the two surviving replicas"], "answer": "The message is lost, because the producer was told it succeeded before replication happened"}
```

```quiz
{"prompt": "A consumer fails to process a message because a downstream API is down. What does Kafka do about the retry?", "options": ["It redelivers the message with exponential backoff automatically", "Nothing — Kafka has no consumer retry; you publish to a retry topic and eventually a DLQ yourself", "It moves the message to a built-in dead letter queue after 3 attempts", "It pauses the partition until the consumer reports success"], "answer": "Nothing — Kafka has no consumer retry; you publish to a retry topic and eventually a DLQ yourself"}
```

```quiz
{"prompt": "You are designing video upload processing. Where should the video bytes go?", "options": ["Into a Kafka topic, so transcoding workers can consume them asynchronously", "Into object storage, with a Kafka message carrying the object key as a pointer", "Split into 1 MB chunks across multiple Kafka partitions", "Into a Kafka topic with compression enabled to keep messages small"], "answer": "Into object storage, with a Kafka message carrying the object key as a pointer"}
```

<details>
<summary>Retention is 7 days and a consumer group has been down for 9 days. What exactly is lost, and what should you do?</summary>

Roughly two days of messages have been deleted from the log and are unrecoverable from Kafka — the segments holding them are gone, and no amount of restarting the consumer brings them back. On restart the consumer's stored offset points into a range that no longer exists, so it will be reset according to `auto.offset.reset`: to the earliest surviving message, or to the newest, depending on configuration.

The operational lesson is that retention is a *recovery budget*, not an archive. If a consumer being down for a week must not lose data, either retention must exceed your worst realistic outage or the data must also land somewhere durable — which is exactly what a sink consumer writing to object storage is for.

</details>

<details>
<summary>Why can a log broker write everything to disk and still be faster than an in-memory queue?</summary>

Because the access pattern is sequential, not random. A producer appends to the end of a segment file and a consumer reads forward, so the disk never seeks and the operating system's read-ahead works perfectly — sequential disk throughput is orders of magnitude better than random. Kafka also avoids copying data through user space on the read path, and batches and compresses on the producer side. DDIA records the outcome plainly: log-based brokers achieve millions of messages per second *despite* writing all messages to disk <abbr title="(p. 497)">[i]</abbr>. The lesson generalises — "disk is slow" is only true for random access.

</details>

<details>
<summary>When is a traditional queue the better answer, even at scale?</summary>

When each message is expensive and independent, and retry semantics matter more than ordering. If a job takes 30 seconds of CPU and order is irrelevant, a queue lets you run 500 workers and acknowledge messages individually, while Kafka caps you at the partition count and forces over-partitioning to compensate. Redelivery and dead-lettering as managed features are the other half of the argument — with Kafka you write that layer yourself. DDIA's rule of thumb is the same: message-by-message parallelism with expensive work and weak ordering needs favours the traditional broker; high-throughput, fast-per-message, ordering-sensitive work favours the log <abbr title="(p. 497)">[i]</abbr>.

</details>

---

## 🔬 PoC — Proof of concepts

- [apache/kafka](https://github.com/apache/kafka) — the implementation; the on-disk log and index files are simpler than the documentation suggests.
- [Kafka design documentation](https://kafka.apache.org/documentation/#design) — the authoritative statement of the log, partition and consumer-group model, including why sequential disk access carries the throughput.
- [Kafka producer configuration reference](https://kafka.apache.org/documentation/#producerconfigs) — `acks`, `enable.idempotence`, batching and compression settings, in one place.
- [redpanda-data/redpanda](https://github.com/redpanda-data/redpanda) — a wire-compatible reimplementation; a second take on the same protocol makes clear which parts are essential and which are Kafka's history.

---

## 📚 Sources

- DDIA2 ch. 12 pp. 493–498 — consumer groups combining load balancing and fan-out (p. 493); dead letter queues (p. 495); the log as an append-only sequence (p. 496); partitions and per-partition total ordering with no cross-partition guarantee (pp. 496–497); millions of messages/second and the consumer-count ceiling equal to the shard count (p. 497); partition key for ordering, periodic offset recording, reprocessing after failover, and segment-based retention as a bounded ring buffer (p. 498).
- `[web: Apache Kafka design documentation]` — sequential I/O and the on-disk segment layout.
- `[web: Apache Kafka producer configuration]` — `acks` semantics, idempotent producer mode, batching and compression.
- Per-broker throughput, latency and retention rungs are `industry practice` figures from [Numbers Quick Reference](/synapse/system-design-from-first-principles/reference/numbers-quick-reference). The ~1 MB message-size guidance and the 7-day default retention are Kafka's documented defaults and common practice rather than DDIA claims.

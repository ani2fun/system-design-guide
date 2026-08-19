---
title: "Redis"
summary: "The single-threaded loop that makes Redis atomic for free, the seven things you can build with its data structures, and the asynchronous replication that will lose your writes."
essential: true
---

# 🧰 Redis

> **Prerequisites:** [Caching](/synapse/system-design-from-first-principles/building-blocks/caching), [Data Models](/synapse/system-design-from-first-principles/data-foundations/data-models) | **You'll be able to:** explain why Redis commands are atomic without locks; pick the right data structure for locks, leaderboards, rate limits, geo search and queues; size a Redis deployment and name what breaks first.

---

## 🧨 The problem (why this exists)

**"We'll put Redis in front of it" is the most-said sentence in system design, and the least examined.**

Naming a technology only earns marks if you can say what it buys and what it costs. Redis is the extreme case: it is so easy to add that people add it without noticing they have introduced a second source of truth with weaker durability than the first.

This lesson answers four questions about it, and every later technology lesson answers the same four:

- What it actually is, underneath the word *"cache."*
- The mechanisms worth knowing.
- What it costs you.
- When to name it, and when naming it is wrong.

---

## 💡 Intuition first

**Think of a bank with exactly one teller and no queue-jumping.**

Every customer is served start to finish before the next begins. Nobody needs a rulebook for two people touching the same account at once, because that situation cannot arise. The teller is the bottleneck *and* the safety mechanism, and those are the same fact.

That is Redis. Commands from thousands of connections arrive at a **single-threaded** execution loop and run one at a time, to completion. This is why `INCR` is atomic, why `SET NX` is a usable lock primitive, and why Redis needs no row locks, no transactions in the database sense, and no deadlock detector.

<div style="border-left:4px solid #195045;background:rgba(25,80,69,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

💡 **Atomicity here is not a feature that was built — it is a property of the shape.** One teller means one operation at a time. Every *"how does Redis handle concurrent writes to the same key?"* question dissolves into *"it doesn't have concurrent writes."*

</div>

**The second surprise is where the speed comes from.**

The obvious answer — *"it avoids disk"* — is wrong, and DDIA says so plainly: a disk-based engine with enough <abbr title="Random-Access Memory — the machine's main working memory">RAM</abbr> may never read from disk either, because the operating system caches recently used blocks anyway <abbr title="(p. 134)">[i]</abbr>. The real advantage is that Redis never pays to **encode its in-memory structures into a form that can be written to disk** <abbr title="(p. 134)">[i]</abbr>. A hash map stays a hash map, rather than being serialised into pages.

---

## ⚙️ How it works

### 🔁 One loop, many connections

Redis multiplexes every client socket onto one event loop. A command is read, executed to completion, and its reply queued — then the next.

```d2
direction: right
classes: {
  client: {style: {fill: "#f3f4f6"; stroke: "#6b7280"}}
  svc:    {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:   {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
  async:  {style: {fill: "#f3e8ff"; stroke: "#9333ea"}}
}
c1: "Client A" {class: client}
c2: "Client B" {class: client}
c3: "Client C" {class: client}
loop: "Single-threaded command loop\none command runs to completion,\nthen the next" {class: svc}
ds: "In-memory data structures\nstrings, hashes, lists,\nsets, sorted sets, streams" {class: data}
persist: "RDB snapshots / AOF log\nfsync policy decides what survives" {class: data}
repl: "Replica\nasynchronous — never waited on" {class: async}
c1 -> loop: "INCR counter"
c2 -> loop: "SET NX lock"
c3 -> loop: "ZADD leaderboard"
loop -> ds: "mutate in place"
ds -> persist: "persist (configurable)" {style.stroke-dash: 3}
ds -> repl: "replicate" {style.stroke-dash: 3}
```

Two consequences follow directly, and both show up in design discussions:

- **Any slow command stalls everything.** `KEYS *` on a large keyspace, a big `SORT`, or deleting a huge collection blocks every other client for the duration. There is no other thread to make progress.
- **Round trips are cheap enough to change your instincts.** Firing 100 queries at a relational database to build one list is a mistake; you write one query instead. Against Redis the per-command overhead is low enough that the same pattern is merely inelegant rather than fatal — and pipelining collapses those 100 round trips into one anyway.

### 🧱 The data structures are the product

Treating Redis as a string-to-string map wastes most of it. DDIA makes the same point from the other side: in-memory storage makes data models practical that are awkward on disk, naming **Redis's priority queues and sets** as the example <abbr title="(p. 134)">[i]</abbr>.

| Structure | The operation it makes cheap | Representative commands |
| --- | --- | --- |
| String | atomic increment, set-if-absent with expiry | `INCR`, `SET NX PX` |
| Hash | update one field of an object | `HSET`, `HGET` |
| List | push/pop at either end | `LPUSH`, `RPOP` |
| Set | membership, union, intersection | `SADD`, `SISMEMBER`, `SCARD` |
| Sorted set | rank and range by score, in log time | `ZADD`, `ZRANGE`, `ZRANGEBYSCORE` |
| Stream | append-only log with consumer groups | `XADD`, `XREADGROUP`, `XCLAIM` |
| Geospatial | radius and box search over coordinates | `GEOADD`, `GEOSEARCH` |

The command names are worth a glance because they are unusually honest: the wire protocol is plain text, and the set commands are close analogues of any language's set type.

### 🧩 Seven things you can actually build

This is the section that turns *"Redis is a cache"* into a usable toolbox. Each row is a real design answer, not a feature.

**Cache.** The default. Read-through or cache-aside in front of a database, with a <abbr title="Time To Live — how long a key survives before Redis deletes it automatically">TTL</abbr> per key.

**Distributed lock.** `SET key value NX PX 30000` sets the key only if absent and expires it after 30 seconds. The expiry is the important half — it releases a lock whose holder crashed. See the warning about failover below before relying on it for correctness.

**Leaderboard.** A sorted set keeps members ordered by score and answers rank and range queries in logarithmic time. *"Top 100 of five million players"* becomes one command. The same shape solves *"most-liked posts containing this keyword"* — keep a sorted set per keyword and trim the tail periodically to bound memory.

**Rate limiter.** A fixed-window limiter is two commands: `INCR` the counter for this caller, and `EXPIRE` it after the window so it resets. If the returned value exceeds the limit, reject. Because the loop is single-threaded, the increment is atomic without a transaction — this is the whole design in [the rate limiter case study](/synapse/system-design-from-first-principles/case-studies/rate-limiter).

**Proximity search.** `GEOADD` stores coordinates and `GEOSEARCH` returns everything inside a radius or box. This is how [Uber](/synapse/system-design-from-first-principles/case-studies/uber) finds nearby drivers without a specialised spatial database.

**Work queue and event log.** Streams are append-only logs with consumer groups, deliberately close in shape to [Kafka](/synapse/system-design-from-first-principles/key-technologies/kafka) topics. Producers `XADD`; a consumer group tracks which entries have been handed out; and when a worker dies mid-message, another worker can `XCLAIM` it and finish the job. That claim mechanism is what makes streams a real queue rather than a list you pop from.

**Pub/Sub.** Publishers send to a channel and every connected subscriber receives it. It is ideal for chat fan-out and live notifications — and it is **at-most-once**: messages are never stored, so a subscriber that is offline misses them permanently.

<div style="border-left:4px solid #15448e;background:rgba(21,68,142,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

📘 **Streams versus Pub/Sub is the distinction to get right.** Pub/Sub broadcasts to whoever is listening *now* and remembers nothing. Streams persist entries, track per-group progress, and let a replacement worker claim an abandoned message. If losing a message is unacceptable, you want a stream — or a broker built for retention.

</div>

One practical note on Pub/Sub connections: a client uses one connection per *node*, not per channel. A million channels does not mean a million connections.

### 💾 Persistence: RDB and AOF

Redis writes to disk two ways, and the acronyms hide what they are.

- **<abbr title="Redis Database file — a compact point-in-time binary snapshot of the whole keyspace">RDB</abbr>** takes point-in-time snapshots of the entire dataset. The file is compact and loads fast on restart, but everything written since the last snapshot is lost in a crash.
- **<abbr title="Append-Only File — a log of every write command, replayed on restart to rebuild the dataset">AOF</abbr>** appends every write command to a log and replays it at startup. The loss window is far smaller, and the `fsync` policy sets it: every write is safest and slowest, once per second is the usual default.

Many deployments run both — <abbr title="Redis Database file — a compact point-in-time binary snapshot">RDB</abbr> for fast restarts, <abbr title="Append-Only File — a log of every write command">AOF</abbr> for a tighter loss window. DDIA classifies Redis exactly here: among in-memory stores it provides **weak durability by writing to disk asynchronously** <abbr title="(p. 134)">[i]</abbr>. That is a description, not a criticism — it is the trade that buys the speed.

### 🖧 Deployment: single node, replica, or cluster

Three topologies, and the jump between them is bigger than it looks.

| Topology | What it gives you | What it costs |
| --- | --- | --- |
| Single node | Simplest thing that works; no coordination at all | One process is the whole availability story |
| Primary + <abbr title="High Availability — a standby replica that can be promoted when the primary fails">HA</abbr> replica | Automatic failover; reads can be served from the replica | Failover can lose recent writes (see below) |
| Cluster | Capacity and throughput beyond one machine | Multi-key operations must stay on one node |

A cluster splits the keyspace into **16,384 hash slots**, and each node owns a range of them. Clients cache the slot map so they connect straight to the node holding the key; nodes gossip enough to redirect a misdirected request, but hitting the right node first is the design goal.

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **A Redis cluster is deliberately basic, and that pushes work onto you.** With few exceptions, all data for one request must live on a single node — so a multi-key operation across slots simply fails. Redis hands you primitives, not a distributed query planner. **Capacity planning here is key-layout planning** — deciding which values must sit together is a design job the cluster will never do for you.

</div>

### 🔗 Replication is asynchronous, and that is the whole risk

A primary does not wait for replicas to acknowledge a write before replying to the client. So a write can be acknowledged, the primary can die, and a replica with no knowledge of that write can be promoted.

That is fine for a cache, where the fallback is a slower read from the database. It is not fine for anything you cannot reconstruct — which is why *"Redis as the only record of a payment, a booking, or a lock you rely on for correctness"* is a design smell. If two clients can believe they hold the same lock after a failover, you need [consensus](/synapse/system-design-from-first-principles/distributed-data/consensus-and-coordination), not a <abbr title="Time To Live — the automatic expiry on the lock key">TTL</abbr>.

---

## ⚖️ Trade-offs

| Option | Gives you | Costs you | Use when |
| --- | --- | --- | --- |
| **Cache** | Sub-millisecond reads; removes most load from the database | A second system; invalidation and staleness questions | The default, and what it is best at |
| **Data-structure server** | Leaderboards, rate limiters, geo search, dedup sets | Memory is the hard ceiling; weak durability | The structure fits and the data is reconstructable |
| **Distributed lock** | One-line mutual exclusion (`SET NX PX`) | Failover can hand the same lock to two holders | Losing the lock occasionally is survivable |
| **Streams as a queue** | Consumer groups, `XCLAIM` recovery, at-least-once | Weaker retention and tooling than a log broker | The workload is modest and already inside Redis |
| **Pub/Sub** | Trivial real-time fan-out | **At-most-once** — offline subscribers miss messages | Loss is acceptable: presence, live counters, chat relay |
| **System of record** | — | Asynchronous replication can drop acknowledged writes | **Don't.** Put the truth in a durable store |

---

## 🔢 Numbers that matter

| Quantity | Value |
| --- | --- |
| Throughput, single node | ~100k operations/second |
| Read latency | microseconds to well under 1 ms |
| Practical memory per node | up to ~1 TB |
| Shard when | ~1 TB, or 100k+ operations/second |
| Hash slots in a cluster | 16,384 `[web: Redis cluster specification]` |
| Sorted-set rank/range cost | O(log N) |
| Replication acknowledgement | none — the primary never waits |

The capacity rungs are this book's standard cache figures and are `industry practice` rather than sourced — see [Numbers Quick Reference](/synapse/system-design-from-first-principles/reference/numbers-quick-reference). The point of memorising them is the *comparison*: at 20k operations/second you are nowhere near one node's limit, and proposing a cluster is over-engineering.

---

## 🏭 In production

### 🔥 The hot key problem

Imagine caching product details across a 100-node cluster, evenly spread. One item goes viral, and traffic for that single item matches the traffic for everything else combined.

Sharding does not help. That key lives in one hash slot on **one node**, and that node now carries half the fleet's load while ninety-nine others idle. Unless every node was heavily over-provisioned, it starts failing.

Three remediations, each with a real cost:

- **Cache the hot key in the client**, so most requests never reach Redis. Cheapest, at the price of a second staleness window you now have to reason about.
- **Write the same value under several key names** and have clients pick one at random, spreading it across slots. Effective, and every write must now update every copy.
- **Add read replicas and scale them with load.** Straightforward, and it only helps reads.

What matters in a design discussion is recognising the risk *before* being asked, and naming a remediation with its trade-off.

### 💣 Eviction is the failure people actually hit

When Redis reaches `maxmemory` it applies an eviction policy, and the default in many deployments evicts nothing and starts refusing writes. The two worth knowing are `allkeys-<abbr title="Least Recently Used — evicts whatever has gone longest without access">lru</abbr>` (evict anything — treat it as a pure cache) and `volatile-lru` (evict only keys carrying a <abbr title="Time To Live — an expiry set on the key">TTL</abbr>). Choosing a `volatile-*` policy while writing keys without expiry produces a cache that fills up and then rejects writes — a slow-motion outage that looks like an application bug.

### 🛠️ Two habits that separate operators from readers

- **Never run `KEYS` in production.** It scans the whole keyspace on the single thread. `SCAN` exists precisely because it returns a cursor and yields between batches.
- **Watch the slow log.** Because one command can block every client, the tail latency of the *slowest* command is the latency of the whole server.

**Where it sits in this book.** Redis is the concrete instance behind [Caching](/synapse/system-design-from-first-principles/building-blocks/caching), the seat-hold store in [Ticketmaster](/synapse/system-design-from-first-principles/case-studies/ticketmaster), the counter in [the rate limiter](/synapse/system-design-from-first-principles/case-studies/rate-limiter), and the geospatial index in [Uber](/synapse/system-design-from-first-principles/case-studies/uber). Four lessons, four different data structures — which is the argument against thinking of it as one thing.

---

## 🪤 Pitfalls & interview traps

- **Calling it "just a cache."** It is a data-structure server whose most common use is caching. The sorted set and the geospatial index are why it wins problems a memcached-shaped store cannot touch.
- **Claiming Redis is atomic *because* it is fast.** The causation runs the other way: it is atomic because it is single-threaded, and that same property makes one slow command catastrophic.
- **Relying on a Redis lock for correctness.** Asynchronous replication means two clients can hold the same lock after a failover.
- **Using Pub/Sub where you needed a stream.** At-most-once delivery loses messages for anyone offline. If that matters, use streams or a real broker.
- **Forgetting that a cluster cannot span slots in one operation.** Multi-key commands need their keys co-located, which is a key-design problem, not a configuration flag.
- **Reaching for a cluster too early.** Below roughly 1 TB or 100k operations/second, one node with a replica is simpler and faster to reason about.

---

## ✅ Check yourself

```quiz
{"prompt": "Two clients issue INCR on the same key at the same instant. What does Redis do?", "options": ["Takes a row lock on the key, so one waits for the other", "Runs them one after the other on its single command loop — no lock exists or is needed", "Rejects the second with a contention error the client must retry", "Applies both concurrently and resolves the conflict with a vector clock"], "answer": "Runs them one after the other on its single command loop — no lock exists or is needed"}
```

```quiz
{"prompt": "A notification service uses Redis Pub/Sub. A subscriber is restarted for 30 seconds. What happens to messages published during that window?", "options": ["They are queued and delivered when the subscriber reconnects", "They are lost — Pub/Sub is at-most-once and stores nothing", "They are written to the AOF and replayed on reconnect", "Redis blocks publishers until every subscriber is back"], "answer": "They are lost — Pub/Sub is at-most-once and stores nothing"}
```

```quiz
{"prompt": "One product goes viral and its cache key now serves half of all traffic across a 100-node cluster. Why does adding nodes not fix it?", "options": ["It does — resharding spreads the hot key across the new nodes", "A single key maps to one hash slot on one node, so only that node's capacity matters", "The cluster gossip protocol rebalances hot keys automatically", "Redis splits hot keys across slots once they exceed a size threshold"], "answer": "A single key maps to one hash slot on one node, so only that node's capacity matters"}
```

```quiz
{"prompt": "You need a work queue where a crashed worker's in-flight message is picked up by another worker. Which Redis feature fits?", "options": ["Pub/Sub, because subscribers all receive the message", "A list with LPUSH and RPOP", "Streams with a consumer group, using XCLAIM to take over an abandoned message", "A sorted set keyed by timestamp"], "answer": "Streams with a consumer group, using XCLAIM to take over an abandoned message"}
```

<details>
<summary>What is the practical difference between RDB and AOF, and why do many deployments run both?</summary>

**RDB** (Redis Database file) is a periodic binary snapshot of the whole keyspace. It is compact and restores quickly, but a crash loses everything written since the last snapshot — potentially minutes of data. **AOF** (Append-Only File) logs every write command and replays it at startup, so the loss window is bounded by the `fsync` policy rather than the snapshot interval: `everysec` loses about a second, `always` loses essentially nothing but costs a disk sync per write.

Running both gets the best of each — restart from the compact snapshot, then replay the tail of the log to recover the writes after it. Neither makes Redis a system of record, because replication to other nodes remains asynchronous regardless of how carefully the local disk is written.

</details>

<details>
<summary>Your cache is configured <code>volatile-lru</code> and writes start failing with out-of-memory errors, even though it is "just a cache." What happened?</summary>

`volatile-lru` evicts only keys that carry a TTL. If the application writes keys without expiry — easy to do accidentally — those keys are permanently ineligible for eviction. Redis fills to `maxmemory`, finds nothing it is allowed to evict, and starts rejecting writes. The fix is either `allkeys-lru`, so anything can be evicted, or a discipline that every key written gets a TTL. It is worth knowing because the symptom (write errors) points at the application while the cause is a one-word configuration choice.

</details>

<details>
<summary>When is "use Redis" the wrong answer to a caching question?</summary>

Three cases. When the data is small, unchanging and per-process — an in-process map is faster and adds no network hop or extra system to operate. When read volume is already inside what the database serves comfortably (a well-tuned Postgres node handles tens of thousands of reads per second), a cache buys headroom you already had in exchange for an invalidation problem. And when what you actually need is durability, retention or ordering, a log broker is the right shape, and forcing Redis into that role trades a correctness property for familiarity.

</details>

---

## 🔬 PoC — Proof of concepts

- [redis/redis](https://github.com/redis/redis) — the implementation. `t_zset.c` and `t_string.c` are short enough to read, and the single-threaded loop is easier to follow in source than in prose.
- [Redis persistence documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/) — the authoritative statement of what RDB and AOF each guarantee and what the `fsync` settings cost.
- [Redis command reference](https://redis.io/commands/) — grouped by data structure; skimming the sorted-set and stream groups is the fastest way to see what the toolbox actually contains.
- [codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x) — collects "write your own Redis" walkthroughs; implementing `SET`, `GET`, `EXPIRE` and the wire protocol makes the event loop concrete.

---

## 📚 Sources

- DDIA2 ch. 4 p. 134 — in-memory databases: the performance advantage comes from avoiding the encoding of in-memory structures for disk, not from avoiding disk reads; Redis and Couchbase provide weak durability via asynchronous disk writes; in-memory storage enables data models such as Redis's priority queues and sets.
- DDIA2 ch. 6 pp. 197–213 — asynchronous replication and what a leader failover can lose.
- `[web: Redis cluster specification]` — the 16,384 hash-slot scheme and client-side slot caching.
- `[web: Redis persistence documentation]` — RDB versus AOF and the `fsync` policies.
- Throughput, latency and capacity rungs are `industry practice` figures carried from [Numbers Quick Reference](/synapse/system-design-from-first-principles/reference/numbers-quick-reference), not sourced from DDIA.

---
title: "Probabilistic Data Structures"
summary: "Four sublinear-memory structures that answer big-data questions approximately — Bloom filter (membership), HyperLogLog (cardinality), Count-Min sketch (frequency), t-digest (quantiles) — trading a small, tunable error for enormous space savings."
essential: true
---

# 🎲 Probabilistic Data Structures

> **Prerequisites:** [Storage Engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines), [Estimation & Numbers](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers) | **You'll be able to:** recognise the four big-data questions — *have I seen this?*, *how many distinct?*, *how often?*, *what's the p99?* — whose exact answer needs memory proportional to the data; name the probabilistic structure that answers each in tiny, bounded space (Bloom filter, HyperLogLog, Count-Min sketch, t-digest); and decide when a small, one-sided, tunable error is a bargain and when it's a silent correctness bug.

---

## 🧨 The problem (why this exists)

Some questions look trivial until you attach a scale to them.

*Have I crawled this URL before?* Keep a set of the URLs you've seen. At ten billion URLs of ~80 bytes each, that *"set"* is **800 GB** — it no longer fits in memory on any one machine, and the whole point of the check was to be fast.

*How many distinct users visited today?* `COUNT(DISTINCT user_id)`. To be exact, the database must remember every user_id it has already counted so it doesn't double-count — so the memory grows with the number of *distinct* users, into the gigabytes for a large site, per time bucket, per dimension you slice by.

*Which URLs are being requested most often right now?* Keep a counter per URL. Across hundreds of millions of distinct URLs in a sliding window, that hash map is again gigabytes — most of it counting things you don't care about, to find the handful you do.

*What is the p99 latency of this service?* The textbook answer sorts every latency sample and takes the 99th percentile — but sorting means *storing every sample*, and a busy service emits millions per minute.

Every one of these has an exact answer, and every exact answer needs memory proportional to the data — which at scale means it doesn't fit, or fitting it costs more than the answer is worth. The escape is the same each time: **give up exactness for a small, bounded, tunable error, and the memory collapses** — often from linear to logarithmic, sometimes to a fixed constant that never grows no matter how much data flows through. This lesson is a tour of the four canonical structures that make that trade, one per question. The through-line: **when memory, not correctness, is the binding constraint, an approximate answer in kilobytes beats an exact answer in gigabytes.**

---

## 💡 Intuition first

You already met the idea in passing. When an [LSM storage engine](/synapse/system-design-from-first-principles/data-foundations/storage-engines) wants to know whether a key might live in a particular SSTable, it doesn't read the file — it asks a tiny **Bloom filter** that answers *"definitely not here"* or *"probably here"* in a handful of bits per key [DDIA2 pp. 122–123]. That is the whole genre in miniature: a structure far smaller than the data it summarises, answering a specific question with a **one-sided, quantifiable error**.

The trick behind all four is the same two-move idea:

1. **Hash the input to destroy identity.** Once you hash an item, you no longer store *what it was* — only a fingerprint. Fingerprints are fixed-size and collide in predictable, mathematically describable ways. You've traded the item for a smudge.
2. **Summarise the smudges, not the items.** Keep a small fixed-size sketch — a bit array, a set of registers, a grid of counters — and update it from the fingerprints. The sketch's size is chosen up front for a target error; it does **not** grow with the data.

The result is a structure whose memory is decoupled from the data volume, and whose error is a knob you set. The four differ only in *which question* they answer and *which way* the error leans:

| Question | Structure | Memory | Error shape |
| --- | --- | --- | --- |
| Have I seen X? (membership) | **Bloom filter** | ~bits per item | Only false *positives* — never a false negative |
| How many distinct? (cardinality) | **HyperLogLog** | fixed (KBs) | ~±0.8% of the true count |
| How often is X? (frequency) | **Count-Min sketch** | fixed (grid) | Only *over*-counts — never under |
| What's the p99? (quantiles) | **t-digest** | small, bounded | Tightest at the tails (p99, p999) |

Notice the recurring gift: the error is usually **one-sided**. A Bloom filter never says *"not seen"* about something it saw; a Count-Min sketch never *undercounts*. Knowing which way the error can only lean is what lets you use these safely — you design around the one direction it can hurt you.

---

## ⚙️ How it works

### 🧽 Bloom filter — "have I seen this?" (membership)

A Bloom filter is a bit array of `m` bits, all zero to start, plus `k` independent hash functions. To **add** an item, hash it `k` ways, and set those `k` bits to 1. To **test** an item, hash it the same `k` ways and look: if *any* of those bits is 0, the item was **definitely never added** (adding it would have set that bit); if *all* `k` bits are 1, the item is **probably present** [DDIA2 pp. 122–123].

```d2
direction: right
classes: {
  edge:  {style: {fill: "#dbeafe"; stroke: "#2563eb"}}
  svc:   {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:  {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
}
add: "add('/page-A')\nhash -> bits 2, 5, 9" {class: edge}
bits: "bit array m bits\n[.. 1 .. 1 .. 1 ..]\n(bits 2,5,9 now set)" {class: data}
q1: "test('/page-A')\nbits 2,5,9 all 1" {class: svc}
q2: "test('/page-B')\nbit 7 is 0" {class: svc}
add -> bits: "set k bits"
bits -> q1: "all 1 -> PROBABLY seen"
bits -> q2: "any 0 -> DEFINITELY NOT seen"
```

**The asymmetry is the entire value proposition.**

**False negatives are impossible**; **false positives are possible** — an item you never added can collide onto `k` bits that other items happened to set, and the filter shrugs *"probably present."* As the array fills, collisions rise, so the false-positive rate climbs with the number of items stored. The beautiful part is that it's *exactly* tunable: for `n` items and `m` bits, the optimal number of hash functions is `k = (m/n)·ln 2`, and the practical rule of thumb is **~10 bits per item buys ~1% false positives, and every extra ~5 bits per item cuts the false-positive rate by roughly 10×** [DDIA2 p. 123]. Ten bits — not ten bytes — to represent membership of an item of any size. That 800 GB URL set becomes **~12 GB at 1% error**, or ~18 GB at 0.1%.

Two limits define its shape. A standard Bloom filter supports *add* and *test* but **not delete** (clearing bits could unset a bit shared with another item, creating a false negative — the one error it's not allowed to make); a **counting Bloom filter** replaces each bit with a small counter to allow deletes, at several times the space. And you must size `m` for your expected `n` up front — overshoot and the false-positive rate degrades; **scalable Bloom filters** chain progressively larger filters to grow gracefully. A modern cousin, the **cuckoo filter**, supports deletion natively and is often more space-efficient at low false-positive rates [web: Fan et al., *"Cuckoo Filter"*, CoNEXT 2014].

### 🔭 HyperLogLog — "how many distinct?" (cardinality)

Counting distinct items exactly means remembering which ones you've already seen — memory grows with the number of distinct values. HyperLogLog answers *"roughly how many distinct?"* in **fixed memory that never grows**, using one deliciously strange observation.

Hash each item to a stream of random-looking bits. In a random bitstring, a run of `p` leading zeros appears about once every `2^p` values. So if the longest run of leading zeros you've *ever seen* across all your hashes is 3, you've probably observed on the order of `2^3 = 8` distinct values; if it's 20, you've probably seen ~`2^20` ≈ a million. **The rarest pattern you've encountered estimates how many distinct things you've encountered** — and tracking *"the longest run of leading zeros so far"* takes a single small number, regardless of how many items streamed past [web: Flajolet, Fusy, Gandouet, Meunier, *"HyperLogLog"*, 2007].

One estimate from one run is wildly noisy, so HyperLogLog uses **stochastic averaging**: split items into many buckets (registers) by the first few hash bits, track the max-leading-zeros *per bucket*, then combine the buckets with a harmonic mean. More buckets → tighter estimate. The error is `≈ 1.04/√m` for `m` registers.

```d2
direction: right
classes: {
  edge:  {style: {fill: "#dbeafe"; stroke: "#2563eb"}}
  svc:   {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:  {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
}
stream: "stream of user_ids\n(billions, with repeats)" {class: edge}
hash: "hash each id\nroute by top bits -> bucket\ntrack max leading zeros" {class: svc}
regs: "16384 registers x 6 bits\n= 12 KB, FIXED\n(never grows)" {class: data}
est: "harmonic-mean combine\n-> ~distinct count\n±0.81% error" {class: edge}
stream -> hash
hash -> regs: "update one register"
regs -> est
```

The canonical implementation is **Redis** (`PFADD`/`PFCOUNT`): 16,384 registers of 6 bits ≈ **12 KB**, giving a standard error of **0.81%** for cardinalities up to billions [web: Redis HyperLogLog documentation, redis.io]. Twelve kilobytes to count distinct visitors whose exact set would be gigabytes. And because two HyperLogLogs can be **merged** by taking the per-register maximum (`PFMERGE`), you can count daily uniques per shard and union them for a site-wide total with no re-scan — the property that makes it the reflexive tool for unique-count dashboards.

### 📊 Count-Min sketch — "how often?" (frequency & heavy hitters)

Now the question is frequency: how many times has *this* item appeared, or which items are the *"heavy hitters"*? An exact answer is a counter per distinct item — a hash map that grows with the number of distinct keys. Count-Min gives approximate counts in a **fixed grid**.

The structure is a 2-D array of counters: `d` rows, `w` columns, with one hash function per row. To **record** an item, hash it once per row and increment the counter at `(row, hash_row(item) mod w)` — `d` increments. To **query** its count, hash it the same way and return the **minimum** of those `d` counters [web: Cormode & Muthukrishnan, *"Count-Min Sketch"*, 2005].

**Why the minimum?**

Different items collide onto shared counters, so every counter is inflated by whatever else hashed there — each counter is an **over**-estimate. But collisions differ across rows, so taking the *smallest* of an item's `d` counters returns the one least polluted by collisions. The sketch therefore **never undercounts** and overcounts by a bounded amount: with `w = ⌈e/ε⌉` and `d = ⌈ln(1/δ)⌉`, the error is at most `ε·N` (N = total events) with probability `1−δ`.

```d2
direction: right
classes: {
  edge:  {style: {fill: "#dbeafe"; stroke: "#2563eb"}}
  svc:   {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:  {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
}
ev: "event: hit('/hot-url')" {class: edge}
grid: "d rows x w cols of counters\nrow1: hash1 -> col, +1\nrow2: hash2 -> col, +1\nrow3: hash3 -> col, +1" {class: data}
q: "count('/hot-url')\n= MIN(its d counters)\n(least collision-polluted)" {class: svc}
ev -> grid: "d increments"
grid -> q: "never under, bounded over"
```

Because the sketch itself can't tell you *which* keys are heavy (it only answers "how often is *this* key?"), heavy-hitter detection pairs it with a small **top-K heap**: every update, query the item's estimated count and, if it beats the smallest in the heap, insert it. You get *"the ~K most frequent items"* — trending URLs, hottest products, the source IPs flooding you — in space set by `w`, `d`, and `K`, not by the number of distinct items. Count-Min is also the frequency estimator inside many database query optimisers and the trending/rate-limiting logic behind large-scale feeds.

### 📐 t-digest — "what's the p99?" (quantiles)

The last question is percentiles — p50, p99, p999 latency — which as you saw in [percentiles and tail latency](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers) are the numbers that actually describe user experience. The naïve exact method sorts every sample; over a stream of millions per minute, storing every sample is the cost you can't pay.

A **t-digest** summarises the distribution with a small, bounded set of **centroids** — each a `(mean, count)` pair standing in for a cluster of nearby samples. The clever part is that it deliberately keeps centroids **small near the tails and larger in the middle**: near p50 a centroid can absorb many samples because you don't care whether the median is the 500,000th or 500,010th value, but near p99 and p999 it keeps centroids tiny so tail estimates stay sharp — exactly where you need precision [web: Dunning & Ertl, *"Computing Extremely Accurate Quantiles Using t-Digests"*, 2019]. To estimate a quantile, walk the centroids accumulating counts until you reach the target rank.

The payoff mirrors the others: a few kilobytes of centroids, updatable online, **mergeable** across shards (combine per-node digests into a global one to get fleet-wide p99 without shipping raw samples), and accurate precisely at the tail percentiles that dashboards live on. This is why it's the engine behind percentile aggregations in **Elasticsearch** and most streaming-metrics systems.

<div style="border-left:4px solid #15448e;background:rgba(21,68,142,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

**The unifying property: mergeability.** Three of these four (HyperLogLog, Count-Min, t-digest) can be **combined across shards** — union HyperLogLogs by per-register max, add Count-Min grids cell-by-cell, merge t-digest centroid sets. That is what makes them the native fit for [stream processing](/synapse/system-design-from-first-principles/building-blocks/stream-processing) and map-reduce: each node computes a local sketch over its slice, and a reducer merges them into a global answer with no re-scan of the raw data. Exact `COUNT(DISTINCT)` has no such shortcut — it must see everything in one place.

</div>

---

## ⚖️ Trade-offs

| Structure | Question | Memory | Error direction | Reach for it when | Don't, when |
| --- | --- | --- | --- | --- | --- |
| Bloom filter | Membership: seen X? | ~10 bits/item for 1% FP | False positive only (never false negative) | The set is too big for memory and a false "yes" is cheap to tolerate or double-check | A false positive causes silent data loss, or you need deletes/counts |
| HyperLogLog | Cardinality: how many distinct? | Fixed ~12 KB | ±~0.8% (two-sided) | Unique counts at scale, sliced/merged many ways | You need the exact number, or the actual set of items |
| Count-Min sketch | Frequency / heavy hitters | Fixed grid | Over-count only (never under) | Top-K, trending, rate-limiting over huge key spaces | Rare items matter (their estimates are noisiest), or exact counts are required |
| t-digest | Quantiles (p50–p999) | Small, bounded | Approximate, tightest at tails | Streaming/merged percentile dashboards | You need exact order statistics on a small dataset (just sort) |

The meta-trade cutting across all four: you are spending **correctness you can bound** to buy **memory you otherwise can't afford**. The engineering discipline is (1) knowing which *direction* the error leans and designing so that direction is harmless, and (2) sizing the structure so the error magnitude is acceptable *before* you ship — because unlike a crash, an over-count or a false positive produces no error, just a quietly wrong number.

---

## 🔢 Numbers that matter

Figures to carry into an interview (estimation method in [Estimation & Numbers](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers)):

- **Bloom filter:** ~**10 bits/item ⇒ ~1% false positives**; each **+5 bits/item ⇒ ~10× fewer** [DDIA2 p. 123]. Optimal hash count `k = (m/n)·ln 2` ≈ **7** at 10 bits/item. A 10-billion-item membership set: **~12 GB at 1%**, vs. ~800 GB for the exact set.
- **HyperLogLog:** Redis uses **~12 KB** (16,384 × 6-bit registers) for a **0.81%** standard error at cardinalities into the billions; error scales as **1.04/√m** [web: redis.io]. Fixed size — it does not grow with the data.
- **Count-Min sketch:** width `w = ⌈e/ε⌉`, depth `d = ⌈ln(1/δ)⌉`; error `≤ ε·N` with probability `1−δ`. A `2048 × 5` grid of 32-bit counters ≈ **40 KB** and never grows with the key space.
- **t-digest:** typically a **few KB** of centroids (compression parameter ~100–200) for sub-percent quantile error, sharpest at p99/p999.
- **The shared win:** all four turn **memory ∝ data** into **memory = a constant (or a log) you choose** — the reason they show up wherever *"count/dedup/rank over a firehose"* appears.

---

## 🏭 In production

**Bloom filters** are everywhere the cost of a lookup dwarfs the cost of a few bits. [LSM engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines) — Cassandra, RocksDB, HBase — keep a per-SSTable Bloom filter so a point read skips files that can't hold the key, turning *"read from disk to discover the key is absent"* into an in-memory *"no"* [DDIA2 p. 122]. [CDNs and caches](/synapse/system-design-from-first-principles/building-blocks/caching) use them to guard against **cache penetration** — a Bloom filter of *"keys that exist in the database"* lets the edge reject requests for keys that provably don't exist before they stampede the origin. Google Chrome's Safe Browsing historically checked URLs against a local Bloom filter of known-malicious sites, only calling the server on a *"probably"* hit. And the [web crawler](/synapse/system-design-from-first-principles/case-studies/web-crawler) uses one for URL dedup — with the crucial caveat below.

**HyperLogLog** backs approximate distinct-count everywhere it would otherwise be a memory monster: Redis `PFADD`/`PFCOUNT`, `approx_distinct` in Presto/Trino, `APPROX_COUNT_DISTINCT` in Redshift/BigQuery, and unique-visitor counts across analytics products. The [ad-click aggregator](/synapse/system-design-from-first-principles/case-studies/ad-click-aggregator) *"unique users per campaign per hour"* is a textbook fit — merge per-shard HyperLogLogs into a campaign total for pennies of memory.

**Count-Min sketch** drives heavy-hitter and frequency workloads: detecting the top talkers in network/DDoS monitoring, trending topics in large feeds, frequency-capping in ad serving, and cardinality/frequency estimation inside database query planners. It shines exactly where a per-key counter map would blow past memory.

**t-digest** is the quiet workhorse of [observability](/synapse/system-design-from-first-principles/production-engineering/observability): Elasticsearch percentile aggregations, and most metrics pipelines that report p99/p999 latency, use t-digest (or HDR-histogram) sketches so each node keeps a few KB and a reducer merges them into a fleet-wide tail latency — the alternative, shipping every raw sample to one place to sort, is a non-starter at metric volumes.

### 🛠️ Hands-on: run the sketches

A runnable set of these sketches lives at `_proof-of-concepts/04-building-blocks/11-probabilistic-data-structures/` in the repo root — pure Python, standard library only: a `BloomFilter` (double-hashed bit array), a `HyperLogLog` (14-bit precision, linear-counting correction), and a `CountMinSketch`.

```bash
cd _proof-of-concepts/04-building-blocks/11-probabilistic-data-structures
./run            # accuracy/memory + merge-across-shards demo
./run test       # mypy --strict + unit tests + demo
```

The demo puts numbers on every claim above: the Bloom filter holds 50k items in ~60 KB with **zero** false negatives and a ~0.8% false-positive rate; HyperLogLog counts **1,000,000** distinct visitors within ~0.2% in a flat **16 KB**; Count-Min recovers heavy-hitter frequencies from a noisy stream. Then it makes the distributed property concrete — four *simulated shards* each sketch a disjoint quarter of a 1.2M-event stream, and merging the four (HLL register-max, Count-Min elementwise-add) reproduces the whole-stream answer exactly. The README spells out what is simulated (the shards, as in-process objects) versus what is exactly-as-production (the sketches and their merge operators).

---

## 🪤 Pitfalls & interview traps

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **Using the wrong error direction.** The single most dangerous mistake is putting a probabilistic structure where its error direction causes *silent* harm. A Bloom filter's false positive says "seen" about something new — for a [web crawler](/synapse/system-design-from-first-principles/case-studies/web-crawler) deduping URLs, that means a genuinely new page is **silently skipped**: quiet data loss with no error to alert you. When a false "yes" is unacceptable, either use the filter only as a *fast pre-check* backed by an exact lookup on a hit, or don't use it at all. Always ask: *which way can this error lean, and is that direction safe here?*

</div>

Three more that separate a confident answer from a buzzword:

- **Reaching for the fancy structure when exact fits.** These earn their keep only when memory is the binding constraint. If your distinct set is a few million items, an exact hash set or an indexed `COUNT(DISTINCT)` is simpler, correct, and fine — modern databases handle large indexes well. Precision about *when the exact answer stops fitting* impresses more than naming HyperLogLog reflexively. (This is exactly the [web crawler](/synapse/system-design-from-first-principles/case-studies/web-crawler)'s verdict: the exact indexed lookup beats the Bloom filter at that scale.)
- **Forgetting you can't enumerate.** None of these can hand back *the items*. A Bloom filter can't list what's in it; Count-Min can't tell you *which* keys are heavy without a companion heap; HyperLogLog gives a count, never the set. If the design later needs the actual members, a sketch was the wrong choice.
- **Deletes and Bloom filters.** A standard Bloom filter can't delete (clearing a shared bit risks a false negative). If items expire — a sliding window, a TTL — you need a counting Bloom filter, a cuckoo filter, or a rebuild-on-rotation scheme, not a plain one.

The interviewer's favourite follow-up: *"what's the failure mode if the estimate is wrong?"* A strong answer names the direction (false positive / over-count / ±%), the concrete consequence (skipped page / inflated trend / slightly-off dashboard), and the mitigation (exact backstop, size for the target error, pick a structure whose one-sided error is harmless here).

---

## ✅ Check yourself

```quiz
{"prompt": "A Bloom filter answers test('/page-X') with 'probably present'. What can you correctly conclude?", "options": ["/page-X was definitely added before", "/page-X was probably added, but it may be a false positive — it might never have been added", "/page-X was definitely never added", "The filter is full and must be resized"], "answer": "/page-X was probably added, but it may be a false positive — it might never have been added"}
```

```quiz
{"prompt": "You need 'unique visitors today' for a site with hundreds of millions of users, sliced by country, and you want to merge per-shard results into a global total cheaply. Which structure fits best?", "options": ["A Bloom filter of user IDs", "A Count-Min sketch keyed by user ID", "HyperLogLog — fixed ~12 KB, ~0.8% error, and mergeable across shards by per-register max", "An exact COUNT(DISTINCT) per shard, summed"], "answer": "HyperLogLog — fixed ~12 KB, ~0.8% error, and mergeable across shards by per-register max"}
```

```quiz
{"prompt": "A Count-Min sketch reports that key '/hot' has been seen 5,000 times. What is the relationship between this estimate and the true count?", "options": ["It may be higher or lower than the true count by a bounded amount", "It is exactly the true count", "It is never less than the true count, and overshoots by a bounded amount due to collisions", "It is never more than the true count, and undershoots due to collisions"], "answer": "It is never less than the true count, and overshoots by a bounded amount due to collisions"}
```

```quiz
{"prompt": "Why does a t-digest keep small centroids near p99/p999 but larger ones near the median?", "options": ["The median is stored exactly and the tails are approximated", "Tail percentiles need high precision (they describe worst-case user experience), while a few positions of slack around the median don't matter", "Centroids near the median are cheaper to compute", "It reduces the total number of centroids to exactly 100"], "answer": "Tail percentiles need high precision (they describe worst-case user experience), while a few positions of slack around the median don't matter"}
```

<details>
<summary>You're deduping URLs in a web crawler with a Bloom filter to save memory. Your product manager asks, "could this cause us to miss pages?" What's the honest answer, and how would you make the design safe?</summary>

Yes — and it's the filter's *only* error direction, which makes it exactly the one that matters here. A Bloom filter never produces a false negative but *can* produce a **false positive**: it can say "probably seen" about a URL you've never crawled. In a crawler, "seen" means "skip," so a false positive causes a **genuinely new page to be silently dropped from the corpus** — data loss with no error raised. To make it safe you have two moves: (1) treat the Bloom filter as a *fast pre-filter* and, on a "probably seen" hit, confirm against an exact store (the indexed URL table) before actually skipping — the filter then only saves you the exact lookup on the common "definitely new" path; or (2) if you can afford it at your scale, skip the filter and use the exact indexed lookup outright, which is often the more practical engineering choice for a corpus builder where quiet loss is unacceptable. The judgement is entirely about whether the one-sided error is tolerable.

</details>

<details>
<summary>An interviewer says: "Count the number of distinct search queries per hour, and also show me the top 10 most frequent queries." Can one structure do both? What do you actually reach for?</summary>

No single sketch does both, because they answer different questions. **Distinct count ⇒ HyperLogLog** (cardinality: "how many different queries," fixed ~12 KB, mergeable across shards). **Top 10 most frequent ⇒ Count-Min sketch + a top-K min-heap** (frequency: estimate each query's count as you stream, and keep the K highest in a small heap — the sketch alone can't enumerate the heavy hitters, so it needs the heap companion). They run side by side over the same stream: every query updates both. A common wrong answer is trying to get frequencies out of a HyperLogLog (it only counts distinct values, it has no per-item frequency) or trying to get the *list* of heavy hitters from a bare Count-Min (it answers "how often is *this* key," not "which keys are hot" — hence the heap).

</details>

---

## 🔬 PoC — Proof of concepts

**Run it yourself.** [Probabilistic data structures](https://github.com/ani2fun/system-design-guide/tree/main/_proof-of-concepts/04-building-blocks/11-probabilistic-data-structures)
— Bloom filter, HyperLogLog and Count-Min sketch built from scratch, measuring the real
accuracy-vs-memory trade-off and merging sketches across shards (the property that makes them
distributable). From `_proof-of-concepts/04-building-blocks/11-probabilistic-data-structures/`, run
`./run`.

**Study real implementations.**

- [RedisBloom](https://github.com/RedisBloom/RedisBloom) — production Bloom, Cuckoo, Count-Min, Top-K
  and t-digest as Redis commands; the same structures this POC builds, hardened.
- [Apache DataSketches](https://github.com/apache/datasketches-java) — the rigorous, mergeable
  streaming-sketch library (quantiles, distinct counts, frequent items) with error bounds you can cite.
- [Redis](https://github.com/redis/redis) — has HyperLogLog built in (`PFADD`/`PFCOUNT`); read that
  implementation to see the register/bias-correction machinery in a widely-deployed system.

---

## 📚 Sources

DDIA2 ch. 4 pp. 122–123 (Bloom filters: mechanism, one-sided error, ~10 bits/item ≈ 1% FP), p. 129 (Bloom filters cut LSM point-read I/O) · [web: Flajolet, Fusy, Gandouet, Meunier, *"HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm"*, 2007] · [web: redis.io — HyperLogLog (~12 KB, 0.81% error)] · [web: Cormode & Muthukrishnan, *"An Improved Data Stream Summary: The Count-Min Sketch and its Applications"*, 2005] · [web: Dunning & Ertl, *"Computing Extremely Accurate Quantiles Using t-Digests"*, 2019] · [web: Fan, Andersen, Kaminsky, Mitzenmacher, *"Cuckoo Filter: Practically Better Than Bloom"*, CoNEXT 2014]

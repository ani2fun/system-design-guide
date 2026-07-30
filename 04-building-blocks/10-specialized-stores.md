---
title: "Specialized Stores: Geo, Time-series & Vectors"
summary: "Three purpose-built stores whose access pattern breaks a general-purpose index: proximity search (geohash, quadtrees, R-trees), time-series (append-mostly, columnar, rollups), and vector search (embeddings and approximate nearest neighbour)."
essential: true
---

# 🧬 Specialized Stores: Geo, Time-series & Vectors

> **Prerequisites:** [Indexing](/synapse/system-design-from-first-principles/data-foundations/indexing), [Storage Engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines) | **You'll be able to:** recognise the three access patterns — proximity, time-ordered, and similarity — that a B-tree cannot serve efficiently; name the right structure for each (geohash/quadtree/R-tree, columnar+rollups, HNSW/IVF); and decide when a query justifies reaching for a store shaped for it rather than bolting the query onto your primary database.

---

## 🧨 The problem (why this exists)

Your primary database — Postgres, MySQL, DynamoDB — is a magnificent general-purpose machine, and its index is a [B-tree or an LSM-tree](/synapse/system-design-from-first-principles/data-foundations/storage-engines). Both keep keys **sorted in one dimension**, and almost every query you have ever written exploits exactly that: find the row whose key equals X, or whose key falls in the range [X, Y]. Point lookups and one-dimensional ranges are the whole game.

Then three questions arrive that the sorted key cannot answer, no matter how you index.

The first is **"which drivers are within 2 km of this rider?"** — a query over *two* dimensions, latitude and longitude, at once. The second is **"what was this server's CPU, averaged per minute, over the last 30 days, across 100,000 machines?"** — a firehose of append-only measurements where the query is almost always *recent* and almost always *aggregated*. The third is **"which of these ten million documents means roughly the same thing as this sentence?"** — a search not for a matching key but for the *nearest point* in a 1,536-dimensional space of meaning.

Each of these breaks the one-dimensional sorted index in a different way, and each has spawned a category of purpose-built store to fix it. This lesson is a tour of all three — not three full lessons, but enough of each that you can recognise the access pattern, name the structure that serves it, and know when the query is worth a specialised store. The through-line is a single idea: **some queries need a store shaped for them.**

---

## 💡 Intuition first

Picture the B-tree as a phone book: names sorted alphabetically. It is brilliant for *"find Smith"* and *"find everyone from Raa to Rzz,"* because those answers are contiguous — they sit together on adjacent pages. It is useless the moment your question doesn't map to a contiguous stretch of that one sorted order.

- **Proximity.** Sort restaurants by latitude and the ones near you in longitude are scattered across the whole book; sort by longitude and latitude scatters instead. *"Near me"* is inherently 2-D, and any single sort flattens one dimension into noise. The fix is a structure that keeps things that are *close on the map* close *in the index* — either by cutting the map into a grid whose cells you can name (**geohash**), or by recursively cutting space into regions and hanging them off a tree (**quadtrees, R-trees**).

- **Time.** Metrics don't behave like customer rows. They only ever *append* (you never update yesterday's temperature), they arrive roughly in time order, and reads care overwhelmingly about the recent past and almost always want an *aggregate*, not a raw point. That lopsided pattern — write-once, time-ordered, recent-hot, read-aggregated — is what a **time-series database** is shaped around: columnar layout, heavy compression, pre-computed **rollups**, and automatic **retention** that throws old raw data away.

- **Similarity.** *"Documents like this one"* isn't a keyword match — a review that says *"terrific audio, dreadful battery life"* should match a query for *"great sound, poor battery"* though they share almost no words. An embedding model turns each piece of text into a **vector**, a point in high-dimensional space, positioned so that *similar meaning ⇒ nearby point*. Now *"similar to"* becomes *"nearest point,"* and the store's job is **nearest-neighbour search** in that space.

Three questions, three structures. The rest of the lesson takes each in turn: the access pattern that breaks a normal index, the structure that fixes it, and when to reach for it.

---

## ⚙️ How it works

### 🗺️ Geospatial: making "near me" contiguous

**The trap is worth stating precisely, because it is the single most common geo mistake in interviews.**

Suppose you store `(lat, lng)` and build a **concatenated index** on the pair — exactly the phone-book-on-(lastname, firstname) idea. DDIA is blunt about why this fails: a concatenated `(lat, lng)` index *"can't answer 2-D range queries efficiently"* — it can narrow on latitude *or* on longitude, one at a time, but not both simultaneously [DDIA2 p. 145–146]. Ask for everything in a map rectangle and the index finds the latitude band fast, then hands you a long strip spanning the entire planet's worth of longitudes, which you must scan and filter. The second dimension buys you nothing.

DDIA names two families of fix: encode the two dimensions into one key with a **space-filling curve** so it drops into an ordinary B-tree, or use a **specialised spatial index** — an R-tree or Bkd-tree — that *"groups nearby points in the same subtree"* [DDIA2 p. 146]. These two families are commonly called **encoded keys** and **custom spatial trees**.

**Encoded keys — geohash.** A geohash interleaves the bits of latitude and longitude into a single string. The trick that makes it work: because the bits alternate, a **shared prefix means spatial proximity** — two points whose geohashes start with the same characters sit in the same grid cell. So a proximity query becomes a *prefix* query, which a plain B-tree (or a Redis sorted set) does beautifully. Precision scales with length: roughly a 5-character geohash is a ~5 km cell and a 9-character one is a ~5 m cell [web: geohash precision ladder, en.wikipedia.org/wiki/Geohash]. Redis's `GEOADD`/`GEOSEARCH` are exactly this — a 52-bit geohash stored as the score in a sorted set.

Geohash cells subdivide predictably — each extra character narrows the box:

```d2
direction: right
classes: {
  data:  {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
  edge:  {style: {fill: "#dbeafe"; stroke: "#2563eb"}}
  svc:   {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
}
world: "geohash prefix 'gc' (~1200 km cell)" {class: edge}
region: "'gcpv' (~150 km cell)" {class: svc}
cell: "'gcpvj' (~5 km cell)" {class: data}
neighbour: "'gcpvn' (~5 km, adjacent)" {class: data}
world -> region: "add chars -> smaller box"
region -> cell: "add chars -> smaller box"
cell -> neighbour: "shared prefix 'gcpv' = nearby"
```

The one wart, worth knowing for the follow-up question: a query point near a cell **boundary** may have its true neighbours sitting in an *adjacent* cell with a different prefix. Production geohash search fixes this by also querying the **eight surrounding cells** (the *"3×3 trick"*) and merging results.

**Custom spatial trees.** Where a geohash imposes a fixed global grid, tree structures adapt to the data.

- A **quadtree** recursively splits a square region into four quadrants, subdividing only where points are dense — so a dense city gets fine cells and empty ocean stays one coarse cell. A *"find everything in this box"* query walks down only the quadrants that intersect the box.
- An **R-tree** generalises the B-tree to 2-D: instead of key ranges, each node holds a **minimum bounding rectangle** enclosing its children, and a range query descends only into rectangles that overlap the query window. This is what **PostGIS** uses (an R-tree via PostgreSQL's GiST), and it's DDIA's headline example [DDIA2 p. 146]. **Elasticsearch** uses a Bkd-tree for its geo fields.

The mental model for all of them is identical: **carve space into regions, index the regions, and a proximity query only visits the regions that could contain an answer** — instead of scanning every point on Earth.

<div style="border-left:4px solid #15448e;background:rgba(21,68,142,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

**When to reach for it.** Below a few thousand rows, brute-force distance to every point is genuinely fine — don't build a spatial index for a farmers-market app. Spatial indexes start paying off at "hundreds of thousands or millions of items." This is the [Uber](/synapse/system-design-from-first-principles/case-studies/uber) driver-matching problem, where Uber's own answer is the H3 hexagonal grid — an encoded-key scheme with ~200 m dispatch cells [web: H3, h3geo.org].

</div>

### 📈 Time-series: shaped for the firehose

Start with the scale that motivates a separate store. Monitor 100,000 servers, five metrics each, one sample every 10 seconds, and you are writing 50,000 points per second — about 4.3 billion points per day. Push that into a general-purpose OLTP database and its B-tree fights you the whole way: every insert scatters a small random write across pages, and yesterday's data is interleaved with today's, so a *"last 24 hours"* scan touches the entire table.

The access pattern, though, is unusually forgiving, and every design choice exploits it:

- **Append-mostly.** You never update a past measurement. That means the storage engine can be a pure append — no in-place updates, no read-modify-write. This is exactly the [LSM-tree](/synapse/system-design-from-first-principles/data-foundations/storage-engines) intuition: buffer writes in memory, flush sorted immutable segments, and let sequential writes run at full disk bandwidth instead of dribbling out random-page updates [DDIA2 p. 120].
- **Time-ordered and partitioned by time.** Data is written and queried by time, so partition the data into time chunks (e.g. one block per hour). A *"last 30 days"* query then loads only the ~30 relevant blocks and ignores the rest of history.
- **Columnar.** Metrics queries read *one column over a huge time range* (*"CPU for the last week"*), never `SELECT *`. Storing each column together — the columnar layout DDIA develops for analytics — means the query reads only the bytes it needs, and columns of near-identical numbers compress ferociously [DDIA2 pp. 137–138]. TimescaleDB and InfluxDB's IOx engine are explicitly columnar [DDIA2 p. 138].
- **Recent-hot, old-cold, with rollups and retention.** Nobody wants per-10-second resolution for data from a year ago. Time-series databases **downsample**: keep raw points for a short window, then a **rollup** job pre-aggregates older data into coarser buckets (1-minute averages, then 5-minute, then hourly), and a **retention** policy deletes raw data past its window entirely. A typical policy — raw for a day, 1-minute for a week, 5-minute for a month, hourly for a year — can store dramatically less data while keeping every dashboard fast.

Here is the layout that falls out of those choices — a hot recent tier feeding rollups and retention:

```d2
direction: right
classes: {
  edge:  {style: {fill: "#dbeafe"; stroke: "#2563eb"}}
  svc:   {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:  {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
  async: {style: {fill: "#f3e8ff"; stroke: "#9333ea"}}
}
ingest: "metrics firehose\n50k points/sec" {class: edge}
hot: "hot tier: raw points\n(last 24h, in-memory + recent segments)" {class: data}
roll: "rollup job\ndownsample to coarser buckets" {class: async}
warm: "warm tier: 1-min averages\n(last 7 days, columnar)" {class: data}
cold: "cold tier: hourly averages\n(last 1 year, compressed)" {class: data}
retention: "retention: drop raw\npast its window" {class: svc}
ingest -> hot: "append-only"
hot -> roll
roll -> warm: "1-min rollup"
warm -> cold: "hourly rollup"
hot -> retention: "expire raw"
```

The archetypes to name: **Prometheus** (the de-facto standard for infrastructure metrics, pull-based scraping), **InfluxDB** (purpose-built TSDB), and **TimescaleDB** (a time-series layer on top of Postgres, so you keep SQL and joins). This is the store behind the [Ad Click Aggregator](/synapse/system-design-from-first-principles/case-studies/ad-click-aggregator) and any metrics/observability design.

### 🧲 Vectors: turning "similar to" into "nearest to"

Semantic search is the motivation DDIA gives, and it's the one that matters most in 2026: search that *"understands document concepts and user intent,"* now central to AI applications like retrieval-augmented generation (RAG) that feed retrieved documents into an LLM [DDIA2 p. 147]. The mechanism is a two-step transform:

1. An **embedding model** — usually a neural network like BERT or an OpenAI embedding model — turns each document into a **vector embedding**: an array of floating-point numbers (often 1,000+ of them) locating the document as a point in high-dimensional space, positioned so that semantically similar documents land near each other [DDIA2 pp. 147–148].
2. **Closeness** is measured by a distance function — **cosine similarity** (the angle between vectors) or **Euclidean distance** (straight-line distance) [DDIA2 p. 148].

So *"find similar documents"* becomes *"find the nearest vectors to the query's vector."* The obvious way to answer it is a **flat index**: compare the query to *every* stored vector and keep the closest — DDIA's flat index, *"accurate but slow"* [DDIA2 p. 148]. Exact is the operative word: it's a correct k-nearest-neighbour answer. But the cost is brutal. One million 1,536-dimension vectors is roughly 6 billion floating-point operations *per query*; at ten million documents and real query rates, exact search collapses.

The escape is to accept **approximate** nearest neighbour (ANN): give up the guarantee of the *exact* closest results in exchange for finding *almost* the closest, orders of magnitude faster. The quality knob is **recall** — the fraction of the true nearest neighbours your approximate search actually returned; production systems target 95%+ and tune latency against it. The two dominant ANN index families, at the intuition level:

- **IVF (inverted file).** Cluster the vector space into partitions around **centroids** ahead of time. At query time, only search the few partitions nearest the query rather than the whole space — tuned by how many partitions you *probe*, trading accuracy for speed [DDIA2 pp. 148–149].
- **HNSW (Hierarchical Navigable Small World).** Build a multi-layer graph: a sparse top layer for big jumps across the space, progressively denser layers below. A query enters at the top, greedily hops toward closer vectors, and descends layer by layer — like a skip-list for geometry [DDIA2 p. 149]. HNSW is the most widely deployed ANN index; the specifics of its layer construction and `ef`/`M` tuning parameters are beyond both primary sources [web: HNSW, Malkov & Yashunin 2016, arxiv.org/abs/1603.09320].

Both trade a little accuracy for a lot of speed by **not looking at most of the vectors**:

```d2
direction: right
classes: {
  edge:  {style: {fill: "#dbeafe"; stroke: "#2563eb"}}
  svc:   {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:  {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
}
query: "query vector\n(embed the question)" {class: edge}
flat: "flat / exact KNN:\ncompare to ALL vectors\n~6B ops for 1M vectors" {class: data}
ivf: "IVF: probe only the\nfew nearest partitions" {class: svc}
hnsw: "HNSW: hop the graph\ntoward closer vectors" {class: svc}
result: "approx nearest neighbours\n(recall ~95%+)" {class: edge}
query -> flat: "accurate, slow"
query -> ivf: "approximate, fast"
query -> hnsw: "approximate, fast"
ivf -> result
hnsw -> result
```

The archetypes span a spectrum. At one end, **vector extensions to databases you already run** — **pgvector** (Postgres), Elasticsearch kNN, Redis vector search — which DDIA notes support both IVF and HNSW [DDIA2 p. 149]. At the other, **purpose-built vector databases** — **Pinecone** (managed), **FAISS** (Facebook's library, the workhorse behind many of them), Weaviate, Milvus, Qdrant. The rule of thumb for graduating from an extension to a dedicated store sits around **100 million vectors**.

---

## ⚖️ Trade-offs

| Store | Access pattern it serves | Structure | Reach for it when | Costs you |
| --- | --- | --- | --- | --- |
| Geospatial | "within X of here" (2-D proximity) | Geohash / quadtree / R-tree | 100k+ points, live proximity queries | Boundary edge cases; a second index to keep in sync |
| Time-series | Append-only, time-ordered, recent-hot, aggregated reads | Columnar + LSM + rollups + retention | High-rate metrics/events, dashboards over time | Not for updates or ad-hoc non-time queries; cardinality traps |
| Vector | "similar to this" (nearest neighbour in high-dim space) | HNSW / IVF (ANN) | Semantic search / RAG / recommendations at scale | Approximate (recall < 100%); memory-hungry; re-embed on model change |

The deeper trade-off cutting across all three: a specialised store is **a second system to run, replicate, and keep consistent** with your source of truth. You rarely make it the primary; you feed it from your primary (often via [change data capture or a stream](/synapse/system-design-from-first-principles/building-blocks/stream-processing)) and treat it as a derived, query-optimised view. That is the same *"secondary index in a different engine"* pattern you saw with [search](/synapse/system-design-from-first-principles/building-blocks/search) and Elasticsearch.

---

## 🔢 Numbers that matter

Ground figures to keep for the interview (full estimation method in [Estimation & Numbers](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers)):

- **Geohash precision:** ~5 characters ≈ 5 km cell; ~9 characters ≈ 5 m cell [web: en.wikipedia.org/wiki/Geohash]. Query the **3×3** neighbourhood for boundary correctness.
- **Spatial-index threshold:** brute force is fine below a few thousand points; spatial indexes pay off from *"hundreds of thousands or millions."*
- **Time-series firehose:** 100k servers × 5 metrics ÷ 10 s ≈ **50k points/sec ≈ 4.3 B points/day** — the number that justifies a TSDB.
- **Vector memory:** 4 bytes/dimension (float32), so a 1,536-dim vector ≈ **6 KB**; 1 M vectors ≈ **~6 GB raw**, and HNSW roughly doubles it.
- **Exact-NN cost:** ~6 B floating-point ops per query for 1 M × 1,536-dim vectors — the wall that forces ANN.
- **Vector-DB graduation:** ~**100 M vectors** is the rule-of-thumb line from *"extension on your existing DB"* to *"purpose-built vector store."* *(Rule of thumb, not a hard limit.)*

---

## 🏭 In production

**Geospatial.** Uber and Lyft run driver–rider matching on grid schemes, not raw distance math: Uber built and open-sourced **H3**, a hexagonal hierarchical grid, precisely because hexagons have uniform adjacency (every neighbour is equidistant, unlike a square grid's diagonal neighbours) [web: h3geo.org]. Redis GEO commands power countless *"nearby"* features because they're a thin, fast layer over a sorted set. PostGIS is the default when the geo data lives alongside relational data and you want SQL — its R-tree/GiST index is production-hardened over decades.

**Time-series.** Prometheus is the observability backbone of the Kubernetes world, scraping metrics and storing them in its own local TSDB; at scale, teams pair it with long-term stores (Thanos, Cortex, Mimir) that push old blocks to object storage — the hot/cold tiering made literal. InfluxDB and TimescaleDB anchor IoT and application-metrics workloads. The recurring operational win is **retention plus rollups**: dashboards stay instant because they read pre-aggregated buckets, and storage stays bounded because raw data is expired on a schedule.

**Vectors.** The 2023–2026 RAG boom made vector stores mainstream: an LLM app embeds your documents once, stores the vectors, and at query time embeds the user's question and retrieves the nearest chunks to stuff into the prompt — DDIA's exact RAG description [DDIA2 p. 147]. Teams overwhelmingly start with **pgvector** because it rides their existing Postgres (one system, transactional, familiar) and graduate to Pinecone/Milvus/Qdrant only when scale or QPS demands it. FAISS remains the library doing the heavy lifting inside many of these.

---

## 🪤 Pitfalls & interview traps

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **The three classic traps.** (1) *Bolting geo onto a B-tree.* Proposing a `(lat, lng)` index for "drivers near me" is the single most common geospatial mistake — it narrows one dimension and scans a planet-wide strip on the other. Name a spatial index (geohash, quadtree, R-tree) instead [DDIA2 p. 146]. (2) *Unbounded time-series cardinality.* A time-series DB indexes by **tag combinations** (series). Put something high-cardinality in a tag — a user ID, a request ID, an unbounded URL — and the number of distinct series explodes, blowing up memory and grinding ingestion to a halt. Keep tags low-cardinality; this is *the* production failure mode of TSDBs. (3) *Exact NN at scale.* Insisting on exact nearest-neighbour over millions of vectors is a non-starter — it's billions of ops per query. Reach for ANN (HNSW/IVF) and discuss the recall/latency trade-off explicitly [DDIA2 p. 148].

</div>

Three more worth a sentence each. **Geohash boundaries:** forgetting the 3×3 neighbour query silently drops results near cell edges — a subtle correctness bug, not a performance one. **Stale embeddings:** if you change your embedding model, *every stored vector is now in a different space* and must be re-embedded — the whole index is invalidated, so treat model choice as a migration-level decision. **Recall is not accuracy:** a vector search returning results fast doesn't mean they're the *right* results; if recall is low, users get subtly worse matches with no error to alert you.

The interviewer's favourite follow-up across all three: *"why not just use your main database?"* The answer is always the same shape — the access pattern (2-D proximity / time-ordered aggregation / high-dim similarity) doesn't map to a one-dimensional sorted index, so you either pay O(n) per query or you adopt a store shaped for it.

---

## ✅ Check yourself

```quiz
{"prompt": "You store restaurants with a concatenated B-tree index on (latitude, longitude). A user asks for everything within a small map rectangle. Why is this slow?", "options": ["The B-tree can't do range queries at all", "It narrows on latitude efficiently but must then scan a full longitude strip and filter", "Latitude and longitude can't be stored as numbers", "B-trees only support exact-match lookups, never ranges"], "answer": "It narrows on latitude efficiently but must then scan a full longitude strip and filter"}
```

```quiz
{"prompt": "A team pushes 50,000 metric points per second into Postgres and finds writes and 'last 24h' scans both degrade badly over time. Which property of a purpose-built time-series database most directly fixes the write problem?", "options": ["It stores data as JSON documents", "Append-only, time-partitioned, LSM-style sequential writes instead of scattered random-page updates", "It uses a B-tree with a larger branching factor", "It keeps every row in a single sorted file forever"], "answer": "Append-only, time-partitioned, LSM-style sequential writes instead of scattered random-page updates"}
```

```quiz
{"prompt": "Exact nearest-neighbour search over 10 million 1,536-dimension vectors is too slow for live queries. What does switching to an approximate (ANN) index like HNSW or IVF give up, and what does it gain?", "options": ["Gives up nothing; it is exact but faster", "Gives up some recall (may miss a few true neighbours) in exchange for far lower query cost", "Gives up the ability to store vectors, gaining compression", "Gives up cosine similarity, forcing Euclidean distance only"], "answer": "Gives up some recall (may miss a few true neighbours) in exchange for far lower query cost"}
```

<details>
<summary>Your metrics dashboard was fast for months, then ingestion suddenly collapsed after a deploy. The deploy added a <code>request_id</code> tag to every metric. What happened?</summary>

You created a **cardinality explosion**. A time-series DB creates one series per distinct combination of tag values, and indexes them in memory. A `request_id` is unique per request, so instead of a bounded set of series (one per host × metric) you now mint a *new series on essentially every write*. Memory for the series index balloons and ingestion grinds to a halt. The fix: tags must be **low-cardinality** dimensions you group or filter by (host, region, status_code) — never unbounded identifiers. High-cardinality values belong in logs or a wide event store, not TSDB tags.

</details>

<details>
<summary>You're designing "find drivers within 2 km." A colleague suggests just computing the distance from the rider to every driver and keeping the closest. When is that actually the right call — and when does it break?</summary>

Brute force is genuinely correct and often *simpler* when the candidate set is small — a few hundred or few thousand drivers in a single city zone, recomputed on demand, is fine and avoids a whole spatial index to maintain. It breaks when the set grows to hundreds of thousands or millions of points, or when query rate is high: distance-to-everyone is O(n) per query and you're doing it constantly. At that point you switch to a spatial index (geohash prefix lookup, quadtree, or R-tree) so each query only examines the handful of grid cells or bounding rectangles that could contain an answer. The judgement is about scale and query frequency, not correctness.

</details>

---

## 🔬 PoC — Proof of concepts

Each specialised store this lesson surveys, available as a Postgres extension you can add and query:

- [PostGIS](https://github.com/postgis/postgis) — geospatial types and indexes (R-tree/GiST) on
  PostgreSQL; the standard for *"find things near a point"* without a bespoke geo database.
- [TimescaleDB](https://github.com/timescale/timescaledb) — time-series on PostgreSQL: hypertables,
  automatic partitioning by time and continuous aggregates.
- [pgvector](https://github.com/pgvector/pgvector) — vector similarity search (HNSW/IVFFlat) in
  Postgres; the embeddings store this lesson describes, without leaving SQL.

---

## 📚 Sources

DDIA2 ch. 4 pp. 137–138, 145–149 (columnar storage, multidimensional & vector indexes) · DDIA2 p. 120 (LSM append-only write path) · [web: en.wikipedia.org/wiki/Geohash] (geohash precision ladder) · [web: h3geo.org] (Uber H3 hexagonal grid) · [web: arxiv.org/abs/1603.09320] (HNSW, Malkov & Yashunin 2016)

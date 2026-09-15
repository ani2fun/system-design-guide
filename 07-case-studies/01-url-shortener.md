---
title: "Design a URL Shortener"
summary: "The canonical opener, taken seriously: base62 and the birthday problem, why the counter is the real distributed-systems problem, and what a 301 does to your analytics."
essential: true
---

# 🔗 Design a URL Shortener

> **Prerequisites:** [Estimation & the Numbers](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers), [Indexing](/synapse/system-design-from-first-principles/data-foundations/indexing) | **You'll be able to:** run the full delivery framework end to end on the canonical opener; choose a short-code generation strategy with real collision math and defend it; scale a ~1000:1 read-heavy system with a cache and replicas — and predict what a 301 does to your analytics before the interviewer asks.

---

## 🤷 Why Bother?

*"Let's design a URL shortener — something like Bitly."* That's the whole brief. You paste in `https://example.com/collections/summer-2026?ref=newsletter&utm_campaign=...`, you get back `short.ly/15ftgG`, and anyone who clicks the short link lands on the long one.

This is the canonical opener of system design interviews, pitched explicitly at the junior end. Don't mistake that for *"easy to do well"*: the product fits in one sentence, so the interview is decided by *how* you execute — whether your requirements are quantified, whether your uniqueness argument survives arithmetic, whether you notice that this system's whole personality is its read-to-write ratio. It is also the cleanest stage anywhere for two ideas this book keeps returning to: scaling reads and unique-ID generation.

We'll run it the way [the delivery framework](/synapse/system-design-from-first-principles/foundations/the-interview-at-10000-feet) says to: requirements → core entities → API → high-level design → deep dives. A book can afford what 45 minutes can't, so in places we go past any interviewable answer — into birthday-problem arithmetic and DDIA's ID-generator theory — and each descent is marked **Going deeper**.

**Functional requirements.** State the top features and explicitly park the rest — [scoping is a graded skill](/synapse/system-design-from-first-principles/foundations/nonfunctional-requirements):

1. Users can submit a long URL and get back a short one — optionally with a custom alias and an expiration date.
2. Anyone who opens a short URL is redirected to the original URL.

*Below the line:* accounts and authentication; click analytics. Park them out loud — shelving analytics now is what makes the 301-vs-302 decision later land.

**Non-functional requirements — quantified.** All four:

1. **Uniqueness:** no two long URLs may ever share a short code — a throwaway-sounding line that turns out to be the hardest requirement on the board.
2. **Latency:** redirects well under 100 ms — the redirect *is* the product, sitting in front of every page load it serves.
3. **Availability:** 99.99%, and availability beats consistency on the redirect path. Say the arithmetic aloud: that's ~52 minutes of downtime per *year*, which alone rules out any single box on the critical path.
4. **Scale:** 1 billion stored URLs, 100 million DAU.

Then name the structural fact hiding inside those numbers: reads dwarf writes. A short URL is created once and clicked forever — roughly 1,000 reads per write. That skew is why this question opens the module: it is the purest rep of [the scaling-reads pattern](/synapse/system-design-from-first-principles/patterns/scaling-reads).

---

## 💡 Intuition first

Start with the dumbest thing that works, because knowing precisely *where* it breaks is the design.

**One server, one database table.**

`POST /urls` inserts a row mapping `short_code → long_url`; `GET /{code}` looks up the row and returns a redirect. The short code column is the primary key, so [the index comes for free](/synapse/system-design-from-first-principles/data-foundations/indexing) and every lookup is a single point read. This one box genuinely satisfies both functional requirements — for a hobby deployment you'd be done.

Now hold it against the non-functional requirements and watch three cracks open:

**Crack 1 — uniqueness under concurrency.** Where do short codes come from? Truncating the long URL is dead on arrival — every URL sharing a prefix collides. Hashing looks plausible until you run the collision math at a billion rows (we will). A counter fixes uniqueness by construction — and quietly becomes the design's only true *distributed-systems* problem the moment more than one server issues codes.

**Crack 2 — read volume.** 100M DAU at ~5 redirects each is ~500M redirects/day — about 5,800/second averaged. But traffic isn't averaged: size the peak at 100× — ~600k reads/second — deliberately harsh, because a shortener's job includes surviving someone else's viral moment. A single database node manages tens of thousands of reads per second. That gap is deep dive #2.

**Crack 3 — one box, four nines.** 52 minutes of allowed downtime a year doesn't survive one unlucky kernel upgrade. Redundancy everywhere on the read path is non-negotiable.

Just as important is the crack that *doesn't* open — the one your instincts will falsely report. Writes are a rounding error: ~100k new URLs/day is about **1 write per second**, and 1B rows at ~500 bytes is **~500 GB** — a dataset one modern database node holds without noticing. No write bottleneck, no sharding for size. Reaching for sharding here is [the classic estimation mistake](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers). This system is a read-scaling problem wearing a CRUD costume.

---

## ⚙️ How it works

### 🧱 Core entities

Keep this stage to a spoken list — detail belongs in the high-level design; interviewers reward the restraint:

- **Short URL mapping** — short code, original long URL, creation time, optional expiration, optional custom alias, creator.
- **User** — whoever created the link.

One [data-modeling](/synapse/system-design-from-first-principles/data-foundations/data-models) observation worth saying aloud: the hot path touches exactly one entity — no joins, no cross-entity transactions, a key-value lookup shape. That's why nearly any storage engine serves it, and why caching will work so well.

### 🔌 The API

One endpoint per functional requirement, [REST with the obvious verbs](/synapse/system-design-from-first-principles/foundations/api-design):

```
POST /urls
{ "longUrl": "https://example.com/very/long/path?with=params",
  "customAlias": "optional", "expirationTime": "optional" }
→ 200 { "shortUrl": "https://short.ly/15ftgG" }

GET /{shortCode}
→ 302 Found, Location: https://example.com/very/long/path?with=params
```

**Two details mark a practiced answer.**

The redirect endpoint lives at the domain root, not under `/api/v1/...` — path characters are product surface. And a `GET` returns no page, just a redirect status plus a `Location` header the browser follows automatically; *which* status is a real design decision with analytics consequences — flag it now, resolve it in deep dive #2.

### 🗺️ High-level design

Draw the single-service version and walk both flows before optimizing anything — a complete working system by minute 25 beats a perfect fragment.

```d2
direction: right
classes: {
  client: {style: {fill: "#f3f4f6"; stroke: "#6b7280"}}
  edge:   {style: {fill: "#dbeafe"; stroke: "#2563eb"}}
  svc:    {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:   {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
}
client: "Client\nbrowser or app" {class: client}
server: "Primary server\nvalidate · generate code · look up" {class: svc}
db: "Database\nshort_code (PK) → long_url" {class: data}
client -> server: "POST /urls"
client -> server: "GET /{code}"
server -> db: "insert mapping"
server -> db: "point lookup by PK"
server -> client: "302 · Location: long URL" {style.stroke-dash: 3}
```

**Write path.** The server validates the long URL (cheap sanity checks), generates a short code — treat generation as a magic function and *say that's deliberate*; it's your first deep dive — handles a custom alias if supplied (after checking it's free), inserts the row, returns the short URL.

**Read path.** The server looks up the code (primary-key point read), checks expiration, and answers with a redirect — or a 404. At small scale this is already fast: one indexed lookup, low single-digit milliseconds.

**That's a working system.**

Everything from here is the interview's second half.

---

## 🤿 Deep dives

Three dives, one per NFR under threat: uniqueness, read-scale latency, load skew. This is where the interview is decided.

### 🎰 Short-code generation: uniqueness without a bottleneck

Constraints: codes must be **unique** (hard requirement), **short** (it's the product's name), and **cheap to generate**. Evaluate the strategies in escalating order; here they are with the arithmetic filled in.

**How short is short?** Base62 — `a–z A–Z 0–9`, chosen over base64 because `+` and `/` collide with URL syntax. Six characters give 62⁶ ≈ 56.8 billion codes against a 1-billion requirement; concretely, 1,000,000,000 encodes as `15ftgG`. A seventh character buys 62⁷ ≈ 3.5 trillion. Six is comfortable; seven is forever.

**Strategy A — hash and truncate.** Hash the long URL, base62-encode, keep the first 6 characters. Deterministic (the same URL yields the same code — free dedupe, though that fights per-user links and expirations), stateless, no coordination. The failure mode is collisions, and the right lens is the birthday problem. **Going deeper** — the interview needs the phrase; the book can afford the arithmetic. For n keys hashed into N slots, expected colliding pairs ≈ n²∕2N. With N = 62⁶ ≈ 5.7 × 10¹⁰:

| codes stored (n) | 6-char space | 7-char space | 8-char space |
| --- | --- | --- | --- |
| 1 million | ~9 collisions | ~0.1 | ~0 |
| 100 million | ~88,000 | ~1,400 | ~23 |
| **1 billion (target)** | **~8.8 million** | ~142,000 | ~2,300 |

(The collision *counts* are this lesson's arithmetic via the standard birthday approximation, not a figure from either source.) The table's shape is the argument: at target scale, 6-character hashes collide millions of times, so every insert needs a check-and-retry — and the check must be **atomic** (a unique constraint or conditional write), because two concurrent inserts can both *"check"* clean and both insert. Enforcing uniqueness at write time is exactly the shape DDIA identifies as requiring [linearizability](/synapse/system-design-from-first-principles/distributed-data/linearizability-and-ordering) — an atomic compare-and-set on the code <abbr title="[ch. 10 p. 409]">[i]</abbr>. An 8th character buys headroom, but now the *"short"* URL is longer than a counter's and the atomic check remains. Purely random codes inherit the same math without the dedupe.

**Strategy B — a counter.** Issue codes from an incrementing integer, base62-encoded. Uniqueness becomes true *by construction* — no collision checks — and codes stay as short as the space allows, gaining a character only at each power of 62. The natural home for it is Redis: single-threaded, atomic `INCR`, so concurrent requests can't race. This is the right interview answer.

It also just moved the hard problem: every write, from every write server, now depends on one counter agreeing on *"next."* **Going deeper:** DDIA treats this exact object. A single-node auto-incrementing counter is a *linearizable fetch-and-add* — the textbook's simplest linearizable system <abbr title="[ch. 10 p. 417]">[i]</abbr> — and it inherits the textbook problems: single point of failure, throughput ceiling, a round trip from everywhere the writers are <abbr title="[ch. 10 pp. 417–418]">[i]</abbr>. Your `INCR` is a tiny timestamp oracle — the object TiDB builds transaction IDs on <abbr title="[ch. 10 p. 424]">[i]</abbr>. (At our ~1 write/second, be honest: a Postgres sequence would also do — the *strategy* is the decision; Redis is headroom.)

**Batched ranges** are the standard pressure release. Each write server leases a block of 1,000 values (`INCRBY 1000`), issues codes locally, and returns when exhausted — one counter round trip per thousand writes. DDIA generalizes: hand out IDs in batches, persisting the batch's high-water mark before serving from it <abbr title="[ch. 10 p. 424]">[i]</abbr>; statically preallocated blocks per node sit in the same family <abbr title="[ch. 10 p. 418]">[i]</abbr>. Two properties matter, and interviewers probe both:

- **Crashes waste, never repeat.** A server that dies mid-block abandons the rest of its range and leases a fresh one on restart. Gaps are harmless — the requirement is uniqueness, not density. Re-issuing a value is *never* acceptable, which is why the counter persists the high-water mark **before** handing out a range, not after <abbr title="[ch. 10 p. 424]">[i]</abbr>.
- **Ordering is quietly gone.** With blocks outstanding on several servers, codes stop appearing in global creation order — DDIA flags exactly this loss for preallocated blocks <abbr title="[ch. 10 p. 418]">[i]</abbr>. Here that costs *nothing*: no requirement says codes reflect creation order.

**Going deeper — the ordering ladder.** DDIA's ID-generator taxonomy runs **uniqueness only** (random UUIDs — no coordination, no order) → **approximate time order** (wall-clock schemes like Snowflake and UUIDv7; clock skew can invert nearby IDs) <abbr title="[ch. 10 pp. 418–419]">[i]</abbr> → **causal order** (Lamport and hybrid logical clocks: if A influenced B, A's ID is smaller; unrelated events order arbitrarily) <abbr title="[ch. 10 pp. 420–422]">[i]</abbr> → **linearizable order** (if A completed before B began, *anywhere*, A's ID is smaller — a single sequencer, or Spanner waiting out its clock's uncertainty interval) <abbr title="[ch. 10 pp. 423–425]">[i]</abbr>. A URL shortener lives on the bottom rung: codes are opaque names nobody compares, so uniqueness is the entire requirement. Batched ranges surrender ordering — a guarantee we never needed — and buy back throughput. Locate the requirement on that ladder unprompted and the deep dive is over.

One genuinely senior failure mode remains: the counter itself. If its state replicates asynchronously and it fails over, the replica may have missed the latest `INCRBY` — a stale counter re-issues ranges, meaning duplicate codes: exactly the async-failover hazard DDIA flags — committed writes simply lost <abbr title="[ch. 10 p. 411]">[i]</abbr>. The fixes are ordinary once named: persist the high-water mark durably *before* releasing a range — checkpoint ahead of what's issued, so recovery over-skips rather than repeats — or hold the counter in a store whose failover can't lose acknowledged writes. That is the only place consensus enters this design: as failover machinery for one integer, not an architecture — fault-tolerant agreement is consensus territory <abbr title="[ch. 10 p. 425]">[i]</abbr>. *"Raft"* without a *what for* is name-dropping, and interviewers can tell.

Rule of thumb, not from source: sequential codes are enumerable — `15ftgG` implies `15ftgF` exists — letting strangers crawl every link ever shortened. Deployments that care apply a cheap bijective scramble to the counter value; either way, treat short links as public.

### ⚡ The read path: redirects in single-digit milliseconds

The requirements: under 100 ms per redirect at ~5,800/second average, spiking toward the 600k/second peak. Build the path in layers, cheapest first.

**Layer 0 — the index you already have.** With `short_code` as primary key, the lookup is a PK point read — O(log n) B-tree or O(1) hash index ([Indexing](/synapse/system-design-from-first-principles/data-foundations/indexing)) — the cheapest question a database answers. The problem is never the *cost* of one read; it's the *count*.

**Layer 1 — [a cache](/synapse/system-design-from-first-principles/building-blocks/caching) in front.** The numbers make the argument: memory ~100 ns, SSD ~0.1 ms, disk ~10 ms — memory is ~1,000× faster than SSD, and a cache node serves 100k+ operations/second where a database node manages tens of thousands. So: Redis or Memcached in front, cache-aside — try the cache; on a hit, redirect from memory; on a miss, read the database, populate with a TTL, redirect.

And this is a *dream* caching workload: the mapping is effectively immutable — a code's target never changes, so the only invalidation events are expiration and deletion, and caching's classic hard problem (coherence with a changing source of truth) barely exists. Hit ratio reduces to cache size plus traffic skew, and skew is your friend: clicks concentrate on recent and popular links, so a cache holding a small fraction of 1B mappings absorbs most reads. (Skew here is a traffic-shape rule of thumb, not a sourced figure — the design needs only its existence.)

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant R as Read service
    participant C as Cache (Redis)
    participant D as Database / replica
    participant O as Origin site
    B->>R: GET /15ftgG
    R->>C: GET 15ftgG
    alt cache hit
        C-->>R: long URL
    else cache miss
        C-->>R: nil
        R->>D: SELECT long_url WHERE short_code = '15ftgG'
        D-->>R: long URL
        R->>C: SET 15ftgG → long URL (TTL)
    end
    R-->>B: 302 Found · Location: long URL
    B->>O: GET long URL (browser follows automatically)
```

**Layer 2 — replicas, not shards.** Misses and cache failures still reach the database, and four nines forbid a single copy anyway. The scaling tool is [leader–follower replication](/synapse/system-design-from-first-principles/distributed-data/replication) with reads on followers: DDIA is explicit that when *read* throughput is the bottleneck, read scaling via replicas is the answer — sharding is for datasets or write rates that exceed a node, and 500 GB at 1 write/second is neither <abbr title="[ch. 7 p. 253]">[i]</abbr>. Replication brings lag, with one user-visible sting: create a link, share it instantly, and the first click may hit a follower that hasn't seen the row — a 404 on a brand-new link, the staleness hazard DDIA opens its consistency chapter with <abbr title="[ch. 10 p. 401]">[i]</abbr>. The fix costs one line in the write path: populate the cache at creation time. Fresh links are the likeliest clicks, and a write-time fill serves them without touching a replica.

**301 or 302 — the status code is a caching decision.** Both redirect, but they instruct the browser differently: **301 Moved Permanently** invites the browser to cache the redirect itself — that browser's later clicks go straight to the destination, never touching you; **302 Found** is temporary — every click comes back. With 301s, repeat clicks vanish from analytics: browsers answer them from cache, counts skew silently low, and there's no retroactive fix — the cached redirects live in a million browser caches you don't control. A cached 301 also outlives your ability to expire or retarget that link for that browser. In 301's favor: browser-cached redirects are free capacity. We land on 302 — keeping click tracking possible (*"below the line"* today doesn't mean amputated forever) and links revocable. Rule of thumb, not from source: production systems pin behavior with explicit `Cache-Control` headers rather than trusting status-code defaults.

**Layer 3, mentioned not built — the edge.** The final escalation answers popular codes from CDN points of presence (edge functions à la Cloudflare Workers) without touching the origin — real latency wins, real costs (invalidation across PoPs, cold caches, debugging, money). At our scale, cache + replicas already clears the bar; name the option, decline it with reasons — a senior move.

### 🔥 Hot keys: what a viral link does to your design

A celebrity posts one short link; for an hour it takes hundreds of thousands of clicks per second. This is the *hot key* problem — one key whose load rivals your whole system's <abbr title="[ch. 7 p. 256]">[i]</abbr> — raised to see whether you understand your own architecture's failure surface.

The honest first answer: the design above *mostly* handles it already — say so rather than reflexively adding machinery. One viral code is one cache entry; reads hit the cache and the database sees a single miss. Recognizing a problem your design already solved is itself signal. Two places it genuinely bites:

**The cold start.** The instant a link goes viral it isn't cached yet, and thousands of concurrent requests miss simultaneously — a stampede on the database for one row. (Stampedes and their fix — request coalescing: one request fetches, the rest wait — are a general caching hazard; rule of thumb, not from the graded sources. Write-time cache population, already in our design, blunts the common case: links go viral young, and young links are pre-warmed.)

**The single-node ceiling.** Hash-based distribution — across cache nodes or database shards — gives each *key* one home, and DDIA's warning is precise: consistent hashing spreads keys evenly, **not load** <abbr title="[ch. 7 p. 263]">[i]</abbr>. A 10-node cache cluster does not serve a viral key at 10× one node's throughput; the owning node serves all of it, to its ops ceiling or its network card, while nine neighbors idle. When one entry outgrows one node:

- **Replicate the hot entry** — several cache nodes each hold the viral mapping; readers fan out among them. Trivially safe because the value is immutable. This is the read-hot answer; the general version is [hot-key mitigation](/synapse/system-design-from-first-principles/patterns/scaling-writes).
- **Isolate it** — range-based schemes can give a hot key a shard, even a machine, of its own <abbr title="[ch. 7 p. 264]">[i]</abbr>; managed stores automate this — Amazon's *heat management* / *adaptive capacity* <abbr title="[ch. 7 p. 264]">[i]</abbr>.
- **Not key salting.** DDIA's salting trick — append two random digits, splitting one key across 100 — spreads *write* load, at the price of reading and recombining all 100 keys per lookup <abbr title="[ch. 7 p. 264]">[i]</abbr>. Our viral key is read-hot with one immutable value: salting adds fan-out and helps nothing. Write-hot and read-hot keys demand different strategies <abbr title="[ch. 7 p. 264]">[i]</abbr>; matching tool to hotness separates understanding from pattern-matching.

A tempting cross-connection: wouldn't 301s absorb viral load? Barely — viral traffic is overwhelmingly *first* clicks from *distinct* browsers, each of which must reach you once; browser caching only dedupes repeats.

The final whiteboard:

```d2
direction: right
classes: {
  client: {style: {fill: "#f3f4f6"; stroke: "#6b7280"}}
  edge:   {style: {fill: "#dbeafe"; stroke: "#2563eb"}}
  svc:    {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:   {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
  async:  {style: {fill: "#f3e8ff"; stroke: "#9333ea"}}
}
client: "Client" {class: client}
lb: "Load balancer" {class: edge}
read: "Read service\nstateless · scale horizontally" {class: svc}
write: "Write service\nvalidate · encode · insert" {class: svc}
cache: "Cache\ncode → long URL" {class: data}
counter: "Counter\nleases ranges of 1,000" {class: data}
db: "Primary DB\n~500 GB · one node" {class: data}
replica: "Read replicas" {class: data}
clicks: "Click event stream\noff the hot path" {class: async}
client -> lb: "GET /{code} · POST /urls"
lb -> read: "reads"
lb -> write: "writes"
read -> cache: "1 · get"
read -> replica: "2 · on miss"
read -> clicks: "fire and forget" {style.stroke-dash: 3}
write -> counter: "lease range"
write -> db: "insert"
write -> cache: "populate on create" {style.stroke-dash: 3}
db -> replica: "async replication" {style.stroke-dash: 3}
```

The whole design as a **walkthrough** — three boards rather than one picture: the system in
context, its containers, and the code level inside the API service. Any box carrying a link
badge drills down a level; the ◀ ▶ ⌂ controls and the board menu walk back out.

```d2 boards name="c4-url-shortener" root="System Context"
direction: right

classes: {
  async:  { style: { fill: "#f3e8ff"; stroke: "#9333ea"; font-color: "#581c87" } }
  client: { style: { fill: "#f3f4f6"; stroke: "#6b7280"; font-color: "#111827" } }
  data:   { style: { fill: "#ffedd5"; stroke: "#ea580c"; font-color: "#7c2d12" } }
  svc:    { style: { fill: "#dcfce7"; stroke: "#16a34a"; font-color: "#14532d" } }
}

user: "User\n[Person]" {
  class: client
  shape: person
}

sys: "URL Shortener\n[Software System]" {
  class: svc
  link: layers.container
}

user -> sys: "HTTPS: create links, follow short codes"

layers: {
  container: {
    direction: right

    user: "User\n[Person]" {
      class: client
      shape: person
    }

    api: "API service\n[Python · FastAPI]" {
      class: svc
      link: _.layers.code
    }

    cache: "Redirect cache\n[Redis]" {
      class: data
      shape: cylinder
    }

    db: "Link store\n[PostgreSQL]" {
      class: data
      shape: cylinder
    }

    range: "ID range allocator\n[PostgreSQL (sequence table)]" {
      class: data
      shape: cylinder
    }

    clicks: "Click stream\n[Redis Stream]" {
      class: async
      shape: queue
    }

    api -> cache: "GET code (hit path, ~µs–ms)"
    api -> db: "miss path reads · new-link writes"
    api -> range: "lease code range (rare, amortized)"
    api -> clicks: "click event (fire-and-forget)"
  }

  code: {
    direction: down

    api: "API service\n[Python · FastAPI]" {
      class: svc

      link_creator: "LinkCreator" {
        class: svc
        link: "https://github.com/ani2fun/system-design-guide/blob/main/_proof-of-concepts/06-case-studies/01-url-shortener/domain/link_creator.py"
      }
      base62_codec: "Base62Codec" {
        class: svc
        link: "https://github.com/ani2fun/system-design-guide/blob/main/_proof-of-concepts/06-case-studies/01-url-shortener/domain/base62_codec.py"
      }
      range_lease: "RangeLease" {
        class: svc
        link: "https://github.com/ani2fun/system-design-guide/blob/main/_proof-of-concepts/06-case-studies/01-url-shortener/domain/range_lease.py"
      }
      redirect_handler: "RedirectHandler" {
        class: svc
        link: "https://github.com/ani2fun/system-design-guide/blob/main/_proof-of-concepts/06-case-studies/01-url-shortener/domain/redirect_handler.py"
      }
    }

    cache: "Redirect cache\n[Redis]" {
      class: data
      shape: cylinder
    }

    db: "Link store\n[PostgreSQL]" {
      class: data
      shape: cylinder
    }

    range: "ID range allocator\n[PostgreSQL (sequence table)]" {
      class: data
      shape: cylinder
    }

    clicks: "Click stream\n[Redis Stream]" {
      class: async
      shape: queue
    }

    api.link_creator -> api.range_lease: "next id"
    api.link_creator -> api.base62_codec: "encode(id)"
    api.redirect_handler -> cache: "lookup"
    api.redirect_handler -> clicks: "click event"
    api.range_lease -> range: "lease [from, to)"
    api.link_creator -> db: "INSERT link"
  }
}
```

### 🛠️ Hands-on: run this design

A **runnable implementation** of this exact design lives at `_proof-of-concepts/07-case-studies/01-url-shortener/` in the repo root — FastAPI + Postgres + Redis via docker-compose, with the four classes above (`LinkCreator`, `Base62Codec`, `RangeLease`, `RedirectHandler`) mirroring the code view 1:1. Start it and watch the design's claims become concrete:

```bash
cd _proof-of-concepts/07-case-studies/01-url-shortener
./run            # frees ports 8310–8312, builds, starts, waits healthy
./run test       # pure unit tests + end-to-end smoke
```

Then observe the two moves this case study turns on: create five links and hit `/stats` to see `ranges_leased` stay at **1** while `ids_issued` climbs — the allocator row is touched once per *thousand* writes, not once per write; and hammer one code to watch `redirect.hit_ratio` climb toward 1.0 as Redis absorbs the read skew. Restart the API and the next code jumps forward by a whole batch — the crash-safety property made visible: **leased-but-unused ids are lost, never reissued**. `./run stop` tears it down.

---

## 🧱 Component reference

<details>
<summary>11 components — what each one owns, the invariant it protects, and where it breaks</summary>

### 👤 User
`Actor` · `Browser or mobile app`

The **User** is anyone on either side of a short link: the person who creates one, and the (far more numerous) people who click one. That asymmetry is the whole system in miniature — a link is created once and clicked forever, which is why the architecture behind this box is built almost entirely for reads.

**Responsibilities**

- Create short links: `POST /links` with a long URL, optionally a custom alias and an expiration date.
- Follow short links: `GET /{code}`, receiving a `302 Found` whose `Location` header the browser follows automatically — the user never sees a page from this system at all.

The user's browser is quietly part of the design. Because the redirect is a `302` (temporary), every click — first or repeat — comes back to the system, which keeps click analytics possible and links revocable. A `301` would invite the browser to cache the redirect itself: free capacity, but repeat clicks would vanish from view permanently.

**Where it grows.** One of these users is eventually a celebrity, and one click becomes hundreds of thousands per second on a single code — viral traffic is overwhelmingly *first* clicks from *distinct* browsers, so browser-side caching can't absorb it. Everything downstream of this actor is shaped by that moment.

### 🏢 URL Shortener
`System` · `HTTPS · read-optimized web service`

The **URL Shortener** turns a long URL into a code like `15ftgG` and redirects anyone who opens it. The product fits in one sentence; the design is decided by two facts hiding inside it.

**Responsibilities**

- Accept a long URL (optionally a custom alias and expiration) and return a short one.
- Redirect every `GET /{code}` to the original URL in well under 100 ms, at 99.99% availability.
- Never let two long URLs share a short code — uniqueness is the hardest requirement on the board.

The first structural fact: **reads dwarf writes**. At 100M DAU the read side averages ~5,800 redirects/second (spiking far higher), while new links arrive at roughly *one per second*. So this is a read-scaling problem wearing a CRUD costume: a cache and read replicas, not shards — 1B rows is only ~500 GB, a dataset one database node holds without noticing.

The second: **uniqueness under concurrency is the only true distributed-systems problem here**. Hashing collides at scale (birthday math: ~8.8M expected collisions at 1B codes in 6 base62 characters); a counter is unique by construction but becomes a shared object every writer depends on. The design's answer is batched counter ranges — see the ID range allocator.

**Where it breaks.** The failure surface is concentrated in two places: the counter's failover (a stale counter re-issues ranges — duplicate codes, the one unforgivable event) and hot keys (one viral link lands on one cache node, because hashing spreads keys, not load).

### ⚙️ API service
`Service` · `Python · FastAPI`

The **API service** is the only compute in the system: it owns both endpoints and stays deliberately **stateless** — any node can serve any request, so scaling is simply adding nodes behind the load balancer. The one piece of per-node state it holds, a leased counter range, is designed to be safely *lost* (a crash abandons the range; gaps, never duplicates).

**Responsibilities**

- `POST /links`: validate the long URL, mint a unique short code, insert the mapping into the link store.
- `GET /{code}`: resolve the code — cache first, store on a miss — and answer `302 Found`.
- Emit a click event per redirect, fire-and-forget, so analytics never adds latency to the hot path.

Internally it is four classes with one-way dependencies — the write path (`LinkCreator → RangeLease → Base62Codec`) and the read path (`RedirectHandler`) share nothing, which is what makes *"no coordination on the read path"* literally true:

```mermaid
classDiagram
    class LinkCreator {
        +create(long_url, alias) Link
    }
    class RangeLease {
        -lo: int
        -hi: int
        +next_id() int
    }
    class Base62Codec {
        +encode(id) str
        +decode(code) int
    }
    class RedirectHandler {
        +resolve(code) str
    }
    LinkCreator --> RangeLease : next id
    LinkCreator --> Base62Codec : encode(id)
```

Each class mirrors a file in the runnable POC at `06-case-studies/examples/url-shortener/app/` — click the code-level boxes for their docs.

**Where it grows.** Statelessness means the service itself never becomes the bottleneck — pressure always lands downstream, on the cache (hot keys), the store (miss traffic), or the allocator (failover). If read and write traffic ever need independent scaling or isolation, the four classes split cleanly into separate read and write services along the dependency seam above.

### 🧩 LinkCreator
`Code` · `Python`

**LinkCreator** is the write path in one class: everything `POST /links` does between receiving a long URL and returning a short one.

**Responsibilities**

- Validate the long URL (and the optional custom alias, when offered).
- Take the **next id** from the node's **RangeLease** — a local, in-memory operation on the amortized-lease design, no allocator round trip.
- Turn the id into a code via **Base62Codec** and `INSERT` the `code → long URL` row into the link store, unique index on `code` as belt-and-braces.

The class embodies the lesson's chosen strategy — *uniqueness by construction*. It never hashes, never generates-and-checks, never retries on collision: the id it encodes came from a range no other node holds, so the code is unique before the database ever sees it. The dependency arrows are one-way and the read path (`RedirectHandler`) shares none of them, which is what makes *"no coordination on the read path"* literally true.

**The invariant it protects:** every code it mints comes from the leased range and is used exactly once — so two concurrent creates, on this node or any other, can never produce the same code.

**Where it grows.** At ~1 write/second the class is nowhere near a bottleneck; its natural evolution is a write-time cache fill (populate the redirect cache on create), which closes the replication-lag 404 on brand-new links. Implemented in the forthcoming POC at `06-case-studies/examples/url-shortener/app/link_creator.py`.

### 🧩 Base62Codec
`Code` · `Python`

**Base62Codec** is the smallest class in the system and the one carrying the product's name: it turns counter ids into *short* URLs.

**Responsibilities**

- `encode(id)`: integer → base62 string over `a–z A–Z 0–9` — the lesson's alphabet choice, picked over base64 because `+` and `/` collide with URL syntax.
- `decode(code)`: the exact inverse, used wherever a code must map back to its id.

The arithmetic is why 62 symbols suffice: six characters give 62⁶ ≈ 56.8 billion codes against a 1-billion-link requirement — `1,000,000,000` encodes as `15ftgG` — and codes only gain a character at each power of 62, so they stay as short as the space allows.

Deliberately, this is a **pure function pair**: no I/O, no state, no clock. That makes it trivially testable (round-trip every boundary value) and means correctness here is a unit test, not an integration concern.

**The invariant it protects:** `encode` and `decode` are a strict bijection — `decode(encode(n)) == n` for every id, and distinct ids never encode to the same code. Uniqueness of codes is exactly uniqueness of ids passed in; the codec can neither create nor destroy it.

**Where it grows.** Sequential inputs make codes enumerable (`15ftgG` implies `15ftgF` exists); deployments that care insert a cheap bijective scramble between counter and codec — the bijection property is what makes that a drop-in. Implemented in the forthcoming POC at `06-case-studies/examples/url-shortener/app/base62_codec.py`.

### 🧩 RangeLease
`Code` · `Python`

**RangeLease** is the class that removes the global counter from the write path. Instead of one allocator round trip per link, it leases a *block* of ids — `[from, to)`, via a single batched fetch-and-add on the **ID range allocator** — and serves `next_id()` from local memory until the block runs dry.

**Responsibilities**

- Lease a fresh disjoint range from the allocator when none is held, and refresh **before exhaustion** so a lease round trip never lands in a request's latency.
- Serve `next_id()` locally — an increment, not a network call — making writes collision-free with zero coordination between API nodes.
- On restart, hold nothing: a new node simply leases a new range.

The design's two deliberate consequences live here. A node that crashes mid-range abandons the unissued remainder — the sequence has gaps, which are harmless because the requirement is uniqueness, not density. And global creation order is gone once several nodes hold ranges — which costs nothing, since codes are opaque names nobody compares.

**The invariant it protects:** a crash produces **gaps, never duplicates**. RangeLease never persists its cursor and never resumes an old range; because the allocator advanced its high-water mark *before* releasing the lease, recovery over-skips rather than repeats, and no id is ever served twice.

**Where it breaks.** Only through its supplier: an allocator that fails over onto stale state can re-issue a range, and duplicate ids become duplicate codes. The class itself cannot detect that — the defense lives in the allocator's durability. Implemented in the forthcoming POC at `06-case-studies/examples/url-shortener/app/range_lease.py`.

### 🧩 RedirectHandler
`Code` · `Python`

**RedirectHandler** is the hot path: `GET /{code}` at ~100:1 read skew, inside a 100 ms budget, spiking toward the design's peak. Everything about the class is shaped by that budget.

**Responsibilities**

- Look the code up in the **redirect cache** first — the hit path answers from memory.
- On a miss, fall through to the **link store** (a primary-key point read), populate the cache with a TTL, and continue.
- Answer `302 Found` with the long URL — `302`, not `301`, so clicks stay observable and links stay revocable.
- Emit a click event onto the **click stream**, fire-and-forget, *after* the redirect is already decided.

Note what the class does **not** touch: the range allocator, the codec, the write path. Its only collaborators are the cache, the store, and the stream — reads need no coordination with anything, which is why redirect capacity is just *"add nodes."* The workload it serves is caching's best case: a code's target never changes, so the cache's classic coherence problem barely exists and hit ratio reduces to size plus skew.

**The invariant it protects:** the redirect never waits on anything but the lookup itself — no click write, no analytics call, no cross-node chatter sits between request and `302`.

**Where it breaks.** Cold viral links: the instant a code goes hot it isn't cached, and thousands of concurrent misses stampede the store for one row. Write-time cache population blunts the common case (links go viral young); request coalescing is the general fix. Implemented in the forthcoming POC at `06-case-studies/examples/url-shortener/app/redirect_handler.py`.

### ⚡ Redirect cache
`Cache` · `Redis`

The **Redirect cache** holds hot `code → long URL` entries in memory so most redirects never touch the database. It exists because of arithmetic: memory answers in ~100 ns versus ~0.1 ms for SSD, and a single cache node serves 100k+ operations/second where a database node manages tens of thousands — and this system's reads outnumber its writes by orders of magnitude.

**Responsibilities**

- Answer the hit path of `GET /{code}` from memory.
- On a miss, let the request fall through to the link store; the handler populates the entry with a TTL on the way back (cache-aside).
- Hold entries populated at *creation* time — fresh links are the likeliest clicks, and a write-time fill serves them without touching a replica (it also sidesteps the replication-lag 404 on a brand-new link).

This is a dream caching workload: a code's target never changes, so the mapping is effectively immutable and cache coherence — normally caching's hard problem — barely exists. The only invalidation events are expiration and deletion. Hit ratio reduces to cache size plus traffic skew, and skew helps: clicks concentrate on recent and popular links, so a cache holding a small fraction of 1B mappings absorbs most reads. Operationally, hit ratio is *the* dashboard metric — it moves before p99 does.

**Where it breaks.** Hot keys. Hashing across a cache cluster spreads *keys* evenly, not *load*: one viral code lives on one node, which takes all of its traffic while its neighbors idle. The value being immutable makes the fix trivially safe — replicate the hot entry across several nodes and fan reads out among them.

### 🗄️ Link store
`Relational database` · `PostgreSQL`

The **Link store** is the system of record: one table of `code → long URL` rows (plus creation time, optional expiration and alias, creator), with a unique index on the code. The hot path touches exactly one entity — no joins, no cross-entity transactions — so every lookup is a primary-key point read, the cheapest question a database answers.

**Responsibilities**

- Persist every mapping durably; serve as the source of truth the cache is filled from.
- Serve the read path's *miss* traffic — the small fraction of redirects the cache doesn't absorb.
- Accept new-link inserts, where the unique index on `code` is the last line of defense for the uniqueness requirement.

The numbers here are the design's most counterintuitive lesson. One billion rows at ~500 bytes is **~500 GB** — a dataset one modern node holds without noticing — and writes arrive at roughly **one per second**. So there is no sharding and no write-scaling machinery; proposing them is the classic estimation mistake on this problem. What the store *does* need is redundancy and read headroom: leader–follower replication with reads on followers, because 99.99% availability forbids a single copy and misses still have to land somewhere.

**Where it breaks.** Replication lag, in one user-visible way: create a link, share it instantly, and the first click may hit a follower that hasn't seen the row — a 404 on a brand-new link. The one-line fix lives upstream: populate the redirect cache at creation time. The other pressure point is a cold viral key stampeding the miss path — also blunted by that same write-time fill, since links go viral young.

### 🗄️ ID range allocator
`Relational database` · `PostgreSQL (sequence table)`

The **ID range allocator** is one integer with strong opinions: a single fetch-and-add row that hands out disjoint counter ranges — `[from, to)` — to API nodes. It exists because uniqueness by construction beats collision checking (hashing to 6 base62 characters yields ~8.8M expected collisions at 1B codes), but a *per-write* global counter would put a single round trip, throughput ceiling, and point of failure on every insert. Batching is the pressure release: lease ~1,000 ids at a time and the allocator is contacted once per thousand writes.

**Responsibilities**

- Atomically advance the counter by the batch size and return the leased range — disjoint ranges are what make concurrent API nodes collision-free with zero coordination between them.
- Persist the new high-water mark durably **before** the range is released to the caller — so recovery over-skips rather than repeats.

Two consequences are deliberate. Crashed API nodes abandon the unissued remainder of their range, so the code sequence has gaps — harmless, because the requirement is uniqueness, not density (gaps are even useful: they tell on your crash rate). And global creation order is quietly gone once several nodes hold outstanding ranges — which costs nothing, since codes are opaque names nobody compares.

**Where it breaks.** Failover. If the allocator's state replicates asynchronously and it fails over, the replica may have missed the latest advance — and a stale counter re-issues a range, meaning **duplicate codes**, the one unforgivable event in this system. The fix is not *"add Raft"* as a slogan; it is one sentence: this tiny state must survive failover without losing acknowledged increments. Alarm on issued-range history — a re-issue is a catastrophe in progress.

### 🌊 Click stream
`Event stream` · `Redis Stream`

The **Click stream** is the design's async boundary: a queue that carries one small event per redirect into the analytics pipeline, so that counting clicks never adds a microsecond to serving them. It exists because the lesson chose `302` over `301` precisely to *keep* click data — and then must make that data free on the hot path.

**Responsibilities**

- Accept a click event from the **RedirectHandler**, **fire-and-forget** — the `302` is already on its way before the event lands; a redirect never waits on a click write.
- Buffer bursts (a viral link means hundreds of thousands of clicks per second on one code) as *lag* in the stream, not as latency on redirects.
- Feed downstream analytics consumers at their own pace.

The asymmetry is the design decision: redirects have a 100 ms budget and a four-nines target; click counts have neither. Splitting them means the analytics pipeline can fall behind, restart, or be rebuilt without the redirect path noticing.

**Where it breaks.** Fire-and-forget means exactly what it says: an API node that crashes between sending the `302` and emitting the event loses that click, and nobody reconciles it. That is a deliberate trade — approximate analytics for an untouched hot path — but say it out loud, because *"clicks"* quietly becoming *"billing"* would invalidate it. The metric to watch is consumer lag age, not stream depth: a stalled consumer with a shallow-looking stream is still an outage for analytics.

</details>

## ⚖️ Trade-offs

The two decisions that define this design:

**Short-code generation** (deep dive #1):

| Option | Gives you | Costs you | Use when |
| --- | --- | --- | --- |
| Hash long URL, truncate | Stateless, no coordination; same URL → same code (dedupe) | Birthday collisions (~8.8M expected at 1B in 6 chars) → atomic check-and-retry per insert; longer codes for headroom | Writers must stay coordination-free; dedupe desired |
| Random 6-char code | Stateless, no coordination | Same collision math, no dedupe | Rarely, at this scale |
| Single global counter + base62 | Uniqueness by construction; shortest codes; no collision checks | Every write round-trips one counter: SPOF, throughput ceiling, cross-region latency <abbr title="[ch. 10 pp. 417–418]">[i]</abbr> | Single region, modest write rate — or as the base the next row fixes |
| Counter + **batched ranges** | Counter contact per ~1,000 writes; crash-safe if high-water mark persists before issue <abbr title="[ch. 10 p. 424]">[i]</abbr> | Global creation order lost <abbr title="[ch. 10 p. 418]">[i]</abbr> — irrelevant here; counter failover needs care | The recommended design at our scale |

**Redirect status** (deep dive #2):

| Option | Gives you | Costs you | Use when |
| --- | --- | --- | --- |
| 301 Moved Permanently | Browsers cache the redirect → repeat clicks cost you nothing | Analytics silently undercount; cached redirects are irrevocable — no expiry or retargeting for that browser | Mappings truly permanent and click data worthless |
| 302 Found (our choice) | Every click observed → analytics possible; links stay expirable and retargetable | Every repeat click is a request you serve | Analytics or link lifecycle matter at all |

---

## 🔢 Numbers that matter

The estimates that changed decisions — the [estimation lesson's](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers) test: each ends in a verb.

| Estimate | Value | Decision it bought | Source |
| --- | --- | --- | --- |
| Storage: 1B rows × ~500 B | ~500 GB | One database node; **don't shard** | Estimation |
| Write rate: ~100k URLs/day | ~1/sec | Any database works; no write-scaling design | Estimation |
| Read rate: 100M DAU × 5 | ~5,800/sec avg | Beyond one node's comfort once spiky → **cache + replicas** | Estimation |
| Peak sizing: avg × 100 | ~600k/sec | Cache is load-bearing, not garnish | Estimation — deliberately harsh; typical diurnal peaks are far smaller (rule of thumb); viral tails are the point |
| Code space: 62⁶ | ~56.8 billion | 6-char codes cover 1B ~57× over; 62⁷ ≈ 3.5T is forever | Arithmetic; `15ftgG` and the 3.5T figure |
| Hash collisions at 1B into 62⁶ | ~8.8 million expected | Hash-truncation needs atomic check-and-retry → **counter wins** | Derived here (birthday approximation) |
| Access speed: RAM / SSD / HDD | ~100 ns / ~0.1 ms / ~10 ms | Cache hits make the <100 ms budget trivial | Estimation |
| Availability: 99.99% | ~52 min downtime/year | No single box on the read path | Arithmetic |

---

## 🏭 In production

The parts no interview asks about.

**The dashboard metric is cache hit ratio.** A hit is a memory read behind one network hop; a miss adds a database round trip. At ~5,800 requests/second average, 99% vs 90% hit ratio is ~58 vs ~580 database reads per second — replicas coasting vs replicas mattering. Watch the ratio, not just p99; the ratio moves *first*. (Reasoning from the access-speed numbers above, not a sourced operational figure.)

**The counter's gaps tell on your crashes.** Two operational habits from deep dive #1: alarm on issued-range history — a re-issued range is a uniqueness catastrophe in progress, the one alert here that can't wait — and expect code-sequence gaps in proportion to write-server restarts. Gaps are normal; duplicates never are.

**Link rot runs in both directions.** Destinations die — the table fills with codes pointing at 404s — and every code *you* expire creates dead links in other people's documents. Expiration is a *product* decision with an infrastructure bill: *"links live forever"* means the table only grows (fine — ~1 row/second), while aggressive expiry breaks the web that embedded you. Neither source adjudicates this; raise it, don't invent an answer.

**Abuse is the unglamorous half of the job.** A shortener is a machine for hiding destinations — a phishing and malware tool by default. Malicious-URL filtering was scoped below the line earlier; production cannot leave it there. The standard shape — industry practice, not from the graded sources — is screening destinations at creation and periodically afterward (destinations change *after* shortening precisely to evade creation-time checks) against threat feeds such as Google Safe Browsing, plus interstitial warnings and creation rate limits.

**Analytics rides the 302, asynchronously.** With 302s every click passes through you. When analytics gets funded, the read service emits a click event (code, timestamp, coarse client info) onto a queue or stream and *never waits on it* — the redirect returns immediately; aggregation happens downstream ([the event-driven pipeline pattern](/synapse/system-design-from-first-principles/patterns/event-driven-cqrs-outbox-cdc)). The production sin is making redirect latency depend on the analytics pipeline's health.

Closing honesty note: this section describes *this* design's operational surface, not how Bitly the company runs its systems — this is an interview-shaped walkthrough, not an engineering blog.

---

## 🪤 Pitfalls & interview traps

**Sharding 500 gigabytes.** The most common failure on this question: proposing sharding for a dataset one node holds easily — 2015 constraints in a 2026 interview. The counter-signal is doing the storage math aloud and *declining* to shard, citing read replicas as the read-scaling tool <abbr title="[ch. 7 p. 253]">[i]</abbr>.

**"Hashes are unique."** Truncating a hash to 6 characters and calling it collision-free misses the birthday arithmetic by roughly seven orders of magnitude at 1B keys (~8.8 million expected collisions, not *"a couple"*). The senior version knows the expected-collision count and the atomic check-and-retry it forces, then chooses the counter *because* of that arithmetic.

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **The 301 "optimization."** "Use 301 — it saves a request" sounds like a performance win, and interviewers let you walk into it. A cached 301 lives in browsers you will never control again: click analytics silently undercount from day one, and expiration and retargeting stop working for that browser, permanently. The follow-up is always "so how do you count clicks?" — asked after you've made counting impossible. Default to 302; adopt 301 only while *stating* you're trading analytics and control away forever.

</div>

**A counter with no failover story.** *"Redis INCR"* and stopping invites the obvious probe: what happens when Redis fails over? The answer must include the persisted high-water mark <abbr title="[ch. 10 p. 424]">[i]</abbr> and the stale-counter re-issue hazard on async failover <abbr title="[ch. 10 p. 411]">[i]</abbr>. Equally bad in reverse: *"we'll use Raft/ZooKeeper"* with no *what for* — the substantive claim is one sentence: the counter's tiny state must survive failover without losing acknowledged increments.
**The leveling bar.** This question is pitched at juniors, which recalibrates what each answer is worth: a junior pass executes the framework with prompting and lands counter + cache; a senior *leads* — quantifies the NFRs unasked, kills sharding with arithmetic, runs the collision math, pre-empts the counter's failover problem, and chooses 302 with the analytics rationale attached. On the easiest question in the canon, the differentiator is depth delivered unprompted.

---

## ✅ Check yourself

```quiz
{"prompt": "You ship 301 redirects to reduce server load. Weeks later, reported click counts look impossibly low. What happened?", "options": ["Browsers cached the redirects, so repeat clicks never reach your servers to be counted", "301 responses are slower, so users abandon before the redirect completes", "301 redirects strip query parameters from the destination URL", "Nothing — 301 and 302 produce identical analytics"], "answer": "Browsers cached the redirects, so repeat clicks never reach your servers to be counted"}
```

```quiz
{"prompt": "A write server leases counter range 41,000–41,999, issues 412 codes, then crashes. What should happen next?", "options": ["Its replacement leases a fresh range; the rest of the old range is abandoned — gaps are harmless, duplicates are not", "Its replacement resumes at 41,412 by scanning the database for the highest issued code", "The counter service rolls back to 41,000 and the range is re-issued", "All codes from the dead range are recalled and re-generated"], "answer": "Its replacement leases a fresh range; the rest of the old range is abandoned — gaps are harmless, duplicates are not"}
```

```quiz
{"prompt": "A short link goes viral: 500k reads/sec for one code. Your cache layer hashes keys across 10 nodes. What actually happens?", "options": ["The single node that owns the key takes all 500k reads/sec — hashing spreads keys evenly, not load", "Load spreads evenly at ~50k reads/sec per node", "The cache evicts the hot key because its access frequency exceeds the LRU threshold", "The load balancer detects the hot key and shards it automatically"], "answer": "The single node that owns the key takes all 500k reads/sec — hashing spreads keys evenly, not load"}
```

<details>
<summary><strong>Q:</strong> When would batched ranges NOT be good enough — when would you need a true linearizable ID generator?</summary>

**A:** When IDs must encode *real-time order across the whole system*, not just uniqueness. DDIA's example: an account is set private from a laptop, then a photo is uploaded from a phone; if the photo's ID can sort *before* the privacy change's, a snapshot read shows the photo under the old public setting <abbr title="[ch. 10 pp. 423–424]">[i]</abbr>. Guaranteeing "A completed before B began ⇒ A's ID < B's ID" takes a linearizable generator — a single sequencer (a timestamp oracle, batch-optimized <abbr title="[ch. 10 p. 424]">[i]</abbr>) or Spanner waiting out its clock's uncertainty interval <abbr title="[ch. 10 pp. 424–425]">[i]</abbr>. A URL shortener needs none of this: codes are opaque names nobody compares for order, so uniqueness — the weakest rung — is the whole requirement. Matching the guarantee to the requirement, not maximizing it, is the point.

</details>

---

## 🔬 PoC — Proof of concepts

**Run it yourself.** [URL shortener](https://github.com/ani2fun/system-design-guide/tree/main/_proof-of-concepts/07-case-studies/01-url-shortener)
— the full design running: FastAPI + Postgres + Redis, with range-leased IDs, Base62 encoding and a
fire-and-forget click stream. From `_proof-of-concepts/07-case-studies/01-url-shortener/`, run `./run`.

**Study real implementations.**

- [Redis](https://github.com/redis/redis) — the redirect cache and the atomic counter this design
  leans on (`INCR`, `INCRBY`); the hot path of every shortener.
- [System Design Primer — Pastebin / URL shortener](https://github.com/donnemartin/system-design-primer)
  — the canonical exercise, with the key-generation and read-heavy trade-offs written out.

---

## 📚 Sources

- `DDIA2 ch. 10 pp. 409–425 (ID generators)` — uniqueness as linearizability (p. 409); async-failover write loss (p. 411); the single-node counter as linearizable fetch-and-add and its limits (pp. 417–418); the ordering ladder — preallocated blocks, wall-clock IDs, Lamport/hybrid clocks (pp. 418–422); linearizable generators, the timestamp oracle, batching, persist-before-issue, Spanner's alternative (pp. 423–425); fault-tolerant agreement as consensus (p. 425).
- `DDIA2 ch. 7 pp. 253–264 (hash sharding, hot keys)` — read scaling via replicas vs sharding (p. 253); hot shard / hot key definitions (p. 256); consistent hashing spreads keys, not load (p. 263); dedicated shards, key salting and its read cost, read-hot vs write-hot strategies, heat management / adaptive capacity (p. 264).
- Derived here, flagged inline: birthday collision counts (n²∕2N); 99.99% ≈ 52 min/year; 62⁶ ≈ 56.8B. Rules of thumb, flagged inline: enumerability, peak factors, fresh-link skew, stampede coalescing, `Cache-Control` pinning, abuse screening.

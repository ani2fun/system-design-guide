---
title: "PostgreSQL"
summary: "Why it should be your default: the write path that makes it fast and durable at once, the specialized indexes that replace whole other databases, and the exact point where one node runs out."
essential: true
---

# 🐘 PostgreSQL

> **Prerequisites:** [Indexing](/synapse/system-design-from-first-principles/data-foundations/indexing), [Transactions & Isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation) | **You'll be able to:** trace a write from client to disk and name what makes it durable; use one database for relational, document, full-text and geospatial work; and say at what write rate a single node stops being enough.

---

## 🧨 The problem (why this exists)

**PostgreSQL should be your default, and "it's <abbr title="Atomicity, Consistency, Isolation, Durability — the four guarantees a transaction provides">ACID</abbr> compliant" is not why.**

Saying a database has transactions is not a design argument. The argument is that Postgres covers four jobs — relational, document, search, geospatial — that a weaker default would spread across four systems, and that it holds strong guarantees while doing it.

The failure mode in a design discussion is the opposite of exotic. It is naming a specialized store for a problem one node would have absorbed, or naming Postgres and then being unable to say what happens at 20,000 writes a second.

---

## 💡 Intuition first

**Think of a library that photocopies instead of lending.**

In an ordinary library the only copy of a book is either on the shelf or in someone's hands, so a reader and a re-shelver contend for the same object. Now imagine the librarian hands every reader a photocopy frozen at the moment they asked. The reader sees a consistent book from start to finish, and the librarian keeps editing the original meanwhile. Neither waits for the other.

That is <abbr title="Multi-Version Concurrency Control — the database keeps several versions of a row so each transaction reads a consistent snapshot">MVCC</abbr>, and DDIA states the payoff in one line: **readers never block writers, and writers never block readers** <abbr title="(p. 295)">[i]</abbr>. A long analytics query cannot stall your checkout path, which is exactly the property people assume databases *lack*.

**The second idea is writing down what you intend before you do it.**

Postgres does not update data files when you commit. It appends the change to a **<abbr title="Write-Ahead Log — an append-only record of every change, written and flushed before the change is applied to the data files">WAL</abbr>** first, and the commit is durable the instant that log entry is on disk. The data files catch up later, in the background.

<div style="border-left:4px solid #195045;background:rgba(25,80,69,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

💡 **This is the trick that makes durability cheap.** Appending to a log is a *sequential* disk write; updating rows scattered across data files is *random*. Postgres pays the fast cost synchronously and defers the slow one, which is why it can be both durable and quick — and why a crash loses nothing: recovery replays the log.

</div>

---

## ⚙️ How it works

### ✍️ The write path, in four steps

```d2
direction: right
classes: {
  client: {style: {fill: "#f3f4f6"; stroke: "#6b7280"}}
  svc:    {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:   {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
}
app: "Client\nCOMMIT" {class: client}
wal: "1 · WAL on disk\nsequential append\ncommit is durable HERE" {class: data}
buf: "2 · Shared buffer cache\npages modified in memory,\nmarked dirty" {class: svc}
idx: "3 · Index updates\nevery index also writes WAL" {class: svc}
files: "4 · Data files on disk\nbackground writer,\nbatched, asynchronous" {class: data}
app -> wal: "flush, then acknowledge"
app -> buf: "apply change"
buf -> idx: "one update per index"
buf -> files: "written later, in batches" {style.stroke-dash: 3}
```

Read the diagram as a claim about *where the time goes*. Durability is bought at step 1, on a sequential write. Steps 2 and 4 are memory work and deferred batching. Step 3 is the one that scales with your schema, not your traffic.

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **Every index you add is a tax on every write.** Each one needs its own update *and* its own log entry. Indexes are usually discussed as a read optimisation, so the write cost goes unmentioned — and then a table with nine indexes writes at a fraction of the rate the same hardware managed with two.

</div>

### 🔍 Indexes that replace other databases

The default index is a B-tree, and it handles equality and ranges. The specialized index types matter more in a design discussion, because each one removes a reason to add another system.

| Index | What it makes fast | Replaces |
| --- | --- | --- |
| B-tree | equality, ranges, sorting | — (the default) |
| <abbr title="Generalized Inverted Index — stores the mapping the other way round, from each term to every row containing it">GIN</abbr> | full-text search; keys inside <abbr title="JSON Binary — JSON stored in a parsed binary form, so individual fields can be indexed and queried">JSONB</abbr> documents | a search cluster, a document store |
| <abbr title="Generalized Search Tree — an index framework for data with no natural linear order, such as shapes and coordinates">GiST</abbr> + PostGIS | geospatial containment and distance | a dedicated geospatial database |

**Full-text search** via <abbr title="Generalized Inverted Index">GIN</abbr> works by inverting the table. A normal index answers *"what is in this row?"*; an inverted one answers *"which rows contain this word?"* — the direction search actually needs. It handles stemming, relevance ranking and boolean queries — enough that most applications never need a separate search cluster. Reach for [Elasticsearch](/synapse/system-design-from-first-principles/building-blocks/search) when you need sophisticated relevance tuning, faceting, fuzzy "search-as-you-type", or search distributed across a dataset one node cannot hold.

**Documents** via <abbr title="JSON Binary — JSON stored parsed, so fields can be indexed">JSONB</abbr> give you schema flexibility inside a relational database. Attributes that vary per row — tags, mentions, arbitrary metadata — live in one column, indexed by <abbr title="Generalized Inverted Index">GIN</abbr>, without a second store and without a migration per new field.

**Geospatial** via the PostGIS extension indexes coordinates with <abbr title="Generalized Search Tree — R-tree-style indexing for geometric data">GiST</abbr>, which is R-tree indexing underneath. *"Everything within 5 km"* becomes an index lookup instead of a full scan. It is capable enough that companies have run real location products on it before outgrowing it.

The compounding effect is the actual argument: one query can filter relationally, match text, and constrain by distance at once — across one system, in one transaction, with one operational burden.

### 🔗 Replication: read scaling and staying up

Replication does two jobs, and conflating them causes trouble.

- **Asynchronous** — the primary acknowledges the write immediately and ships changes afterwards. Fast, and replicas trail.
- **Synchronous** — the primary waits for replica acknowledgement before confirming. Stronger, and every write pays the round trip.

Many deployments run a hybrid: one or two synchronous replicas for safety, more asynchronous ones for read capacity. Reads scale close to linearly with replica count, which is why a read-heavy product gets a long way on one primary.

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **Replication lag breaks the most basic user expectation: seeing your own edit.** A user saves their profile, the read goes to a replica that has not caught up, and their change appears to have vanished. This is the **read-your-writes** problem, and the fix is routing — send a user's reads to the primary for a short window after they write, or pin them to a replica known to be current.

</div>

For availability, a replica is promoted when the primary fails: detect, promote, repoint connections. Managed services handle this; what matters in a design discussion is knowing failover exists, that it takes seconds not milliseconds, and that an asynchronous replica may be missing the last few writes when promoted.

### 🔐 Consistency you have to actually use

Postgres gives genuine <abbr title="Atomicity, Consistency, Isolation, Durability">ACID</abbr> transactions, and the default isolation level is **Read Committed** — each statement sees only data committed before it began.

Not every database that says `SERIALIZABLE` means it. DDIA notes Oracle as the example: it has an isolation level *called* serializable that actually implements snapshot isolation, a weaker guarantee <abbr title="(p. 282)">[i]</abbr>. Postgres is the honest case here — its `SERIALIZABLE` really does prevent the anomalies serializability forbids, at a cost in aborted transactions under contention.

The practical point: choosing Postgres does not give you consistency. Using its transactions deliberately does — `SELECT … FOR UPDATE` for a row you are about to modify, a unique constraint to make a race impossible, an explicit isolation level when Read Committed is not enough. See [Transactions & Isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation) for which anomaly each level actually stops.

---

## ⚖️ Trade-offs

| Option | Gives you | Costs you | Use when |
| --- | --- | --- | --- |
| **Single primary** | Strong guarantees, no coordination, simplest thing that works | One node's write ceiling; one failure domain | The default, up to a few thousand writes/second |
| **+ read replicas** | Read throughput multiplied by replica count | Replication lag and read-your-writes problems | Read-heavy, which is most products |
| **+ synchronous replica** | No data loss on failover | Every write pays a network round trip | Losing seconds of writes is unacceptable |
| **<abbr title="JSON Binary — JSON stored parsed and indexable">JSONB</abbr> instead of a document store** | Flexible fields inside <abbr title="Atomicity, Consistency, Isolation, Durability">ACID</abbr> transactions | Weaker schema discipline; awkward for deeply nested access | Attributes vary per row and still need transactions |
| **<abbr title="Generalized Inverted Index">GIN</abbr> search instead of a search cluster** | One less system to run and keep in sync | No faceting or advanced relevance tuning | Search is a feature, not the product |
| **Sharding** | Writes beyond one node | Cross-shard queries and transactions get hard | You have measured past the single-node ceiling |

---

## 🔢 Numbers that matter

A well-tuned instance on ordinary hardware, at the default Read Committed isolation:

| Operation | Throughput |
| --- | --- |
| Simple inserts | ~5,000/second per core |
| Updates that touch indexes | ~1,000–2,000/second per core |
| Complex multi-table transactions | hundreds/second |
| Bulk load | tens of thousands of rows/second |
| Storage per node | ~64 TiB; managed engines reach 128–256 TiB |
| Concurrent connections | ~5k–20k, and far fewer without pooling |

These are `industry practice` figures, not DDIA claims — see [Numbers Quick Reference](/synapse/system-design-from-first-principles/reference/numbers-quick-reference). Four things move them: disk speed for the <abbr title="Write-Ahead Log">WAL</abbr>, index count, synchronous replication, and how many tables a transaction touches.

<div style="border-left:4px solid #15448e;background:rgba(21,68,142,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

📘 **Exceeding 5,000 writes/second does not rule Postgres out.** It rules out *one node*. The ladder is batch writes, scale the machine up, move non-critical writes off the hot path, and only then shard. Reaching for a distributed store at the first sign of load is [the classic estimation mistake](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers).

</div>

---

## 🏭 In production

**Connections are a scarcer resource than people expect.** Each one is a server process with its own memory, so a few thousand idle connections cost real capacity. A pooler in front is standard, and the failure it prevents — an application fleet that scales out and exhausts the database's connection limit — looks like a database outage while being an architecture problem.

**Vacuum is the maintenance that <abbr title="Multi-Version Concurrency Control — old row versions are kept until nothing can still see them">MVCC</abbr> forces on you.** Old row versions stay until no transaction can still see them, then autovacuum reclaims the space. On a write-heavy table it can fall behind, leaving **bloat**: a table far bigger on disk than its live rows justify, with queries slowing in proportion. Long-running transactions make it worse, because nothing older than the oldest open transaction can be reclaimed.

**Where it sits in this book.** Postgres is the system of record in [the URL shortener](/synapse/system-design-from-first-principles/case-studies/url-shortener), the orders database in [Ticketmaster](/synapse/system-design-from-first-principles/case-studies/ticketmaster), and the whole subject of [Inventory Reservations in PostgreSQL](/synapse/system-design-from-first-principles/reference/inventory-reservations-postgres), where every SQL block was executed against a live instance.

---

## 🪤 Pitfalls & interview traps

- **"We'll use Postgres because it's ACID."** Say which anomaly you are preventing and with what — a row lock, a unique constraint, a stricter isolation level. The property is not the design.
- **Adding indexes without naming the write cost.** Every index is another log entry per write.
- **Forgetting read-your-writes.** The moment you add a replica, a user can fail to see their own change. Say how you route around it.
- **Assuming failover is free.** Promotion takes seconds, and an asynchronous replica may be missing the newest writes.
- **Reaching for a specialized store too early.** Full-text and geospatial are built in. Justify the extra system against what Postgres already does.
- **Sharding before measuring.** Batching, a bigger machine and write offloading all come first.

---

## ✅ Check yourself

```quiz
{"prompt": "A COMMIT returns successfully and the server loses power one millisecond later, before the data files were updated. What happens to that transaction?", "options": ["It is lost — the change never reached the data files", "It survives; the change was already flushed to the write-ahead log and is replayed during recovery", "It survives only if a synchronous replica had acknowledged it", "It is partially applied, leaving the table inconsistent"], "answer": "It survives; the change was already flushed to the write-ahead log and is replayed during recovery"}
```

```quiz
{"prompt": "An analytics query scans a large table for 40 seconds. What does it do to concurrent checkout writes on that table?", "options": ["It blocks them until the scan completes", "Nothing — under MVCC readers never block writers, and writers never block readers", "It forces them to a lower isolation level", "It blocks writes only to rows the scan has already read"], "answer": "Nothing — under MVCC readers never block writers, and writers never block readers"}
```

```quiz
{"prompt": "A user updates their profile, is redirected, and their old name appears. Reads are load-balanced across replicas. What is happening?", "options": ["The write was lost because replication is asynchronous", "Replication lag — the read hit a replica that had not yet applied the change", "The transaction was never committed", "The primary rejected the write and returned success anyway"], "answer": "Replication lag — the read hit a replica that had not yet applied the change"}
```

```quiz
{"prompt": "A product needs relational data, per-row flexible attributes, keyword search, and 'within 5 km' queries. Traffic is ~2,000 writes/second. What is the strongest first design?", "options": ["Postgres for relations, MongoDB for attributes, Elasticsearch for search, and a geo database for distance", "One Postgres instance using JSONB with GIN, full-text GIN, and PostGIS with GiST, plus read replicas", "A distributed NoSQL store, since four access patterns imply four systems", "Postgres sharded from day one, since four features on one node will not scale"], "answer": "One Postgres instance using JSONB with GIN, full-text GIN, and PostGIS with GiST, plus read replicas"}
```

<details>
<summary>Why is writing to the log first <em>faster</em> than writing the data pages, when it is strictly more work?</summary>

Because the two writes have completely different costs. The log is append-only, so its write is **sequential** — the disk writes a contiguous run with no seeking, and that is the pattern storage hardware is best at. Updating the actual rows means touching pages scattered across the data files: **random** writes, orders of magnitude slower per byte.

So Postgres pays the cheap write synchronously — the commit waits only for the log flush — and defers the expensive one to the background writer, which batches many changes into fewer, larger, better-ordered writes. Total work goes up; the work *on the critical path* goes down. The same reasoning explains why [Kafka](/synapse/system-design-from-first-principles/key-technologies/kafka) writes everything to disk and is still fast, and why LSM-tree engines buffer in memory before flushing.

</details>

<details>
<summary>Your table is 400 GB on disk but holds only 40 GB of live rows, and queries have slowed. What happened?</summary>

Table bloat from MVCC. Every update writes a new row version and leaves the old one behind; the old versions can only be reclaimed once no transaction could still need them. Autovacuum normally does this continuously, but on a heavily updated table it can fall behind — and a single long-running transaction pins the horizon, so *nothing* newer can be reclaimed while it is open.

Queries slow because they read pages, and the pages are now mostly dead rows. The immediate fix is to make vacuum keep up: tune autovacuum to run more aggressively on that table, and hunt for long transactions holding the horizon open. The lasting fix is not leaving transactions open across slow work such as network calls.

</details>

<details>
<summary>When should you genuinely reach past PostgreSQL?</summary>

Three honest cases. **Write volume beyond what one node plus the optimisation ladder handles** — sustained tens of thousands of writes per second pushes you toward a store built for horizontal write scaling, such as [Cassandra](/synapse/system-design-from-first-principles/key-technologies/cassandra). **Access patterns that are purely key-value at enormous scale**, where a relational engine's features are overhead. And **search as the product rather than a feature** — faceting, tuned relevance and fuzzy matching are a search engine's job.

Notice what is not on the list: "we have JSON", "we need geospatial", or "we might scale one day." Those are Postgres features or premature optimisation. The strong move is to start here and justify each deviation, rather than start somewhere niche and justify it against Postgres.

</details>

---

## 🔬 PoC — Proof of concepts

- **Run it yourself.** [Inventory Reservations in PostgreSQL](/synapse/system-design-from-first-principles/reference/inventory-reservations-postgres) is this book's deepest Postgres piece — row locks, `SKIP LOCKED`, bloat and connection attribution, with every SQL block executed against PostgreSQL 17.10 and three real defects found that way.
- [postgres/postgres](https://github.com/postgres/postgres) — the source; `src/backend/access/transam/README` is a readable account of the write-ahead log.
- [PostgreSQL documentation: Write-Ahead Logging](https://www.postgresql.org/docs/current/wal-intro.html) — the authoritative statement of what a commit guarantees.
- [PostGIS](https://postgis.net/) — the geospatial extension, with worked examples of GiST-indexed distance and containment queries.

---

## 📚 Sources

- DDIA2 ch. 8 p. 282 — many databases use isolation weaker than serializability; Oracle's "serializable" is actually snapshot isolation.
- DDIA2 ch. 8 p. 295 — the MVCC principle: readers never block writers, and writers never block readers.
- DDIA2 ch. 4 pp. 115–132 — the write-ahead log and why sequential writes outperform random ones.
- DDIA2 ch. 6 pp. 197–213 — synchronous versus asynchronous replication, replication lag, and read-your-writes consistency.
- `[web: PostgreSQL documentation — Write-Ahead Logging, Routine Vacuuming, Textsearch, PostGIS]` — the write path, autovacuum, GIN full-text search and GiST spatial indexing.
- Write-throughput and connection figures are `industry practice` rungs from [Numbers Quick Reference](/synapse/system-design-from-first-principles/reference/numbers-quick-reference), measured at the default Read Committed isolation level.

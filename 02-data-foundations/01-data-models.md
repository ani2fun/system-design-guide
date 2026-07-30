---
title: "Data Models"
summary: "How the shape you give your data — relational, document, graph — decides which operations are cheap and which are painful, and how to drive the 'core entities' step of an interview fast."
essential: true
---

# 🧩 Data Models

> **Prerequisites:** [Thinking in Trade-offs](/synapse/system-design-from-first-principles/foundations/thinking-in-tradeoffs), [API Design](/synapse/system-design-from-first-principles/foundations/api-design) | **You'll be able to:** choose relational vs document from the *shape* of the data rather than by reflex; explain what a join actually buys you and what denormalization costs; drive the *"core entities"* step of an interview in two minutes without freezing.

---

## 🧨 The problem (why this exists)

**You are handed a feature:** *"show each user their home timeline — the recent posts from everyone they follow."*

You have `users`, `posts`, and a `follows` relationship. It sounds like one query: find everyone this user follows, find their recent posts, sort by time, return the top fifty.

**At a thousand users this is instant. At a hundred million, with celebrities followed by tens of millions, the same query melts.**

- The problem was never the code — it was a decision you made before writing a line of it: **how the data is shaped**.
- Store a timeline as a live join across two giant tables and every load pays for that join.
- Store each user's timeline as a pre-built list and reads get cheap, but now every post has to be *fanned out* into all its followers' timelines, and a celebrity's single post triggers thirty million writes.

**Neither answer is "correct."**

They are the *same data* under two shapes, and the shape decides which operation is cheap and which is brutal. This is the quiet truth of system design: **the data model is the most consequential layer you touch.** It shapes not just performance but how you write every piece of code above it and even how you *think* about the problem — an application is a stack of models, each expressed in terms of the one below [p. 65]. Pick the wrong shape at the bottom and every layer above inherits the awkwardness.

This lesson is about picking the shape deliberately. We'll build the two dominant general-purpose models — relational and document — from first principles, using that timeline as the running example, then place graph, event sourcing, and CQRS around them. By the end you'll choose a model from the *shape of the relationships in your data*, and drive the *"core entities"* step of an interview quickly and with reasons.

---

## 🏙️ Intuition first

Forget databases for a moment. You have a fact — *"Alice lives in Washington, DC"* — and it shows up in a thousand places across your app. Two honest options for storing it:

**Option one: write it out every time.**

Every record that mentions Alice's city contains the literal string *"Washington, DC."* Reading is trivial — the answer is right there. But the day Alice moves, you must find and rewrite all thousand copies, and if you miss one, your data disagrees with itself.

**Option two: write it once, point to it everywhere.**

Store *"Washington, DC"* in one place, give it an ID, and everywhere else store just the ID. Now moving Alice is a single edit. But reading her city means following the pointer — a *lookup* — to turn the ID back into something readable.

**That is the entire tension of data modeling in one example.**

- **Normalization:** Storing information in exactly one place and referring to it by ID is called **normalization** [p. 72]; duplicating it so it's readable on the spot is **denormalization** [p. 72].
- Normalized data is cheaper to write and can never disagree with itself; denormalized data is cheaper to read because the answer is already assembled.
- **The join:** The lookup that option two forces — resolving an ID back into the real data — is, in a relational database, a **join** [p. 72].

**Now zoom out. Real data is not one fact; it's facts *related* to other facts.**

- A user *has* several jobs. A post *belongs to* a user. A user *follows* many users and *is followed by* many.
- The relational and document models are two bets about which relationships you'll have most, and which you'll make expensive:
  - The **document model** bets your data is mostly **tree-shaped** — one thing owning a nested pile of sub-things, loaded together. It stores each tree as one self-contained document (one JSON object), so reading the whole tree is one cheap fetch — the *"write it out together"* choice by default.
  - The **relational model** bets your data is a web of **cross-references** — many things pointing at many others — and gives you the join as a first-class, cheap-ish tool for following those pointers at read time — the *"write it once, point to it"* choice made comfortable.

> Everything that follows elaborates that one distinction: *what kind of relationships dominate your data, and which lookups will you pay for?*

---

## ⚙️ How it works

### 🔀 The object-relational mismatch

**Start with why this is annoying at all.**

- Most application code is object-oriented — data lives as objects with nested objects and lists.
- Relational databases store data as **relations**: tables, unordered collections of rows [p. 67], a model Codd proposed in 1970 that became the default for structured data by the mid-1980s [p. 67].
- **Impedance mismatch:** Objects don't slot cleanly into rows; bridging the two takes an awkward translation layer, a friction so recognized it has a name from electronics — the **impedance mismatch** [p. 68].

**ORMs help but leak.**

- Tools called ORMs (object-relational mappers, like Hibernate or ActiveRecord) automate that translation's boilerplate [p. 68].
- They help but leak: they can't fully hide the two models, and they make it easy to write inefficient queries — inviting the classic **N+1 query problem**.
- Ask an ORM for N posts, then in a loop touch each post's author, and you may silently issue one query for the posts plus one per post for its author: N+1 round-trips where a single join would do [p. 68].
- Hold onto that phrase; it's a favorite interview probe, and the *deliberate* version of the same pattern turns out to be sometimes correct.

### 🌳 One-to-many is a tree, and trees like documents

**Take a résumé — the LinkedIn kind.**

- One person has several jobs, schools, contact methods. Each is a **one-to-many** relationship: one user, many positions.
- In a relational schema you split these into separate tables — `positions`, `education`, `contact_info` — each carrying a foreign key back to the `users` row [p. 69], so assembling a full profile means several queries or a multi-way join.

**Express the same résumé as a single JSON document and something clicks:**

the positions are a nested array *inside* the user object, education another array, the whole profile one document fetched in one shot [p. 69–70]. This maps far more closely to the object in your application code, and it has better **locality** — every piece you need sits in one place, so the read is faster and the code simpler [p. 71]. The fit is clean for a structural reason: a one-to-many relationship *is* a tree, and JSON makes the tree explicit [p. 71].

This is the document model's home turf. When your data is a tree you load all at once, it's a genuinely good fit, and shredding that tree across many relational tables produces cumbersome schemas and fiddly code [p. 80].

<div style="border-left:4px solid #15448e;background:rgba(21,68,142,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

**"One-to-many" is really "one-to-few."** Embedding works because a résumé has a *handful* of jobs. The moment the "many" is genuinely large — the thousands of comments under a celebrity's post — cramming them all into one document becomes unwieldy, and the relational approach wins [p. 71]. The number of related items, not the relationship's name, decides whether embedding is wise.

</div>

### 🔗 Normalization, denormalization, and what a join buys you

**Return to the Alice's-city problem, now with vocabulary.**

- Storing `region_id` instead of the literal `"Washington, DC"` is a normalization choice, and it buys real things: consistent spelling, no ambiguity between two places with the same name, one-place updates, easier localization, and better search — the ID can encode facts like *"Washington is on the East Coast"* that a raw string can't [p. 72].
- An ID never has to change, precisely because it carries no human meaning; duplicated readable data, by contrast, must be rewritten everywhere it appears, costing more writes, more disk, and — worst — risking inconsistency if an update is missed [p. 72].
- The price of normalization is the lookup: to *show* a record you resolve its IDs back to readable values, which in a relational database is a join [p. 72].

**So a join is not overhead to be feared** — it is what makes normalization affordable, letting you keep one clean copy of every fact and still assemble a readable view on demand.

- Document databases historically had weak join support (some have none, forcing application-side joins; MongoDB offers a `$lookup` operator) [p. 73] — a large part of *why* document data tends to be denormalized: without a cheap join, staying normalized is inconvenient, so people duplicate instead.

The general principle, worth memorizing:

> Normalized data is usually **faster to write** (one copy) but **slower to query** (needs joins); denormalized data is usually **faster to read** (fewer joins) but **more expensive to write** (more copies to keep in sync) [p. 74].

**And the sting in the tail: denormalized data is *derived* data.**

- The copies don't maintain themselves — you need a process to keep them consistent, and if it crashes mid-update you can be left with copies that disagree [p. 74].
- Atomic transactions make this safer, but not every database offers atomicity across multiple documents, so the burden sometimes lands on you [p. 74].

### 📰 The X/Twitter timeline: denormalization done right

**Now the running example pays off.**

- X's home timeline is the canonical case of *deliberate* denormalization: a materialized timeline is nothing more than a **cache of the posts-follows join** from the top of this lesson, precomputed and stored so reads don't recompute it [p. 74].
- When you post, a fan-out process pushes an entry into your followers' materialized timelines, keeping the denormalized representation up to date [p. 74].

**Here's the senior-level detail interviewers love. What does that stored entry contain?**

- Not the post text — only the **post ID, the poster's user ID, and a little extra** [p. 74–75].
- Reading a timeline therefore still performs *two joins*: one hydrating each post ID into its content and stats, another hydrating each sender ID into profile details like name and avatar [p. 74–75].
- *"Hydrating the IDs"* is just a join done in application code — the exact N+1-shaped pattern from earlier, except here it's the *right* call [p. 75].

**Why store only IDs when the whole point was to precompute?**

Because the referenced data is **fast-changing** — like counts and profile photos change constantly — so baking it into thirty million timelines would be instantly stale *and* explode storage [p. 75]. IDs are stable; the mutable data stays in one place, joined at read time. That hydration parallelizes well, its cost independent of follower count — which is why read-time joins are *not* inherently an obstacle to a scalable service [p. 75].

> The lesson: normalization and denormalization are neither good nor bad. The most scalable design often **denormalizes some things and normalizes others** — here, denormalize *which posts* are in your timeline, but keep post content and profile data normalized and join on read [p. 75].

Here is the same profile-and-timeline data under both shapes:

```d2
direction: right

classes: {
  client: {style: {fill: "#f3f4f6"; stroke: "#6b7280"}}
  edge:   {style: {fill: "#dbeafe"; stroke: "#2563eb"}}
  svc:    {style: {fill: "#dcfce7"; stroke: "#16a34a"}}
  data:   {style: {fill: "#ffedd5"; stroke: "#ea580c"}}
  async:  {style: {fill: "#f3e8ff"; stroke: "#9333ea"}}
}

norm: "Normalized (relational)" {
  users: "users\n(id, name, avatar_url)" {class: data}
  posts: "posts\n(id, author_id, text, likes)" {class: data}
  follows: "follows\n(follower_id, followee_id)" {class: data}
  timeline: "home_timeline\n(user_id, post_id, author_id)" {class: data}

  posts -> users: "author_id → id" {style.stroke: "#ea580c"}
  follows -> users: "follower_id → id" {style.stroke: "#ea580c"}
  timeline -> posts: "hydrate post_id" {style.stroke: "#ea580c"}
  timeline -> users: "hydrate author_id" {style.stroke: "#ea580c"}
}

denorm: "Denormalized (document)" {
  doc: |md
    # one timeline entry, self-contained
    {
      user_id: 251,
      post_id: 8842,
      author_name: "Alice",
      author_avatar: "a.png",
      text: "Hello, world!",
      likes: 40
    }
  | {class: async}
}
```

The normalized side keeps every fact once and pays joins to reassemble a view. The denormalized document is readable in one shot — but `author_name`, `author_avatar`, and `likes` are now *copies*, each a future consistency problem the moment Alice renames herself or the like count ticks.

### 🕸️ Many-to-one and many-to-many: the pressure back toward relations

**The document model shines on trees, but not everything is a tree.**

`region_id` was a **many-to-one** relationship — many people live in one region [p. 75]. Introduce organizations and schools that many people reference and you get **many-to-many**: a person works at several organizations, an organization has many employees [p. 75]. These do *not* fit neatly inside one self-contained document, and they push you back toward a normalized, relational shape [p. 76].

**In the relational model, a many-to-many relationship is an associative table (join table):**

each row pairs one user ID with one organization ID [p. 75]. In the document model you're forced to store *references* to other documents instead of nesting — re-inventing the relational approach inside JSON [p. 76]. And such relationships usually need querying **in both directions** (*"who works here?"* and *"where does this person work?"*). Storing the reference on both sides denormalizes it — now in two places, able to drift — whereas a normalized representation stores it once and leans on secondary indexes to answer both directions efficiently [p. 76].

This is the relational model's home turf, and why *"just use a document database"* collapses for richly interconnected data. The more your data is a web of many-to-many links rather than independent trees, the more the join — and the model that makes it cheap — earns its place.

### 📐 Schema-on-read vs schema-on-write, honestly

A frequently overstated advantage of document databases is being *"schemaless"* — a misleading word, since the code reading a document *always* assumes some structure. There's an implicit schema; it's just not enforced by the database [p. 80]. The honest framing is a contrast of *when* the schema is applied [p. 80]:

- **Schema-on-write** — explicit, enforced by the database at write time (the relational default); analogous to static (compile-time) type checking [p. 80–81].
- **Schema-on-read** — implicit, interpreted only when the data is read (the document default); analogous to dynamic (runtime) type checking [p. 80–81].

**Neither wins outright; it's genuinely contested [p. 81].**

- The difference bites hardest when you *change* the data's shape.
- In a document database you just start writing the new field and teach your reading code to cope with old documents that lack it [p. 81].
- In a schema-on-write database you run a migration — `ALTER TABLE` to add the column (usually fast) plus, to backfill, an `UPDATE` that rewrites every row (slow on a large table, and operationally delicate to run without downtime) [p. 81].

**The honest guidance:**

schema-on-read genuinely helps when data is **heterogeneous** — many object types where giving each its own table is impractical, or where structure is dictated by external systems you don't control [p. 81]. When all records share one structure, an enforced schema is a *feature*: it documents and guarantees that structure for everyone [p. 81]. This matters in interviews — functional requirements are usually scoped tight enough that *"the schema keeps changing"* rarely applies, removing the main reason to reach for a document store.

### 📍 Data locality — the real, narrow benefit

**The performance argument for documents is locality:**

a document is typically stored as one continuous string (JSON, or a binary form like MongoDB's BSON), so if you need the *whole* document at once, one contiguous read beats scattering the same data across many tables and index lookups [p. 82]. But the benefit is narrow and cuts both ways. It only helps when you need large parts together; loading a big document to read one field is wasteful, and updates usually rewrite the *entire* document — so large documents with frequent small updates are a bad fit, and the standing advice is to keep documents fairly small [p. 82]. Locality isn't unique to documents either: Spanner can interleave related rows inside a parent table, and Bigtable-style wide-column stores (HBase, Cassandra) use column families for the same effect [p. 82].

### 🤝 The convergence: the two models are growing together

**Here's the plot twist that keeps you from tribalism.**

- The relational and document models started far apart and have steadily converged [p. 83].
- Most relational databases added JSON column types, operators, and the ability to index values *inside* a JSON document — so you can store a document-shaped tree in a relational database and query into it — while document databases (MongoDB, Couchbase, RethinkDB) added joins, secondary indexes, and declarative query languages [p. 83].
- A relational-document *hybrid* — normalized tables for interconnected data, JSON columns for the genuinely tree-shaped, load-together parts — is a powerful combination [p. 83].
- Codd's original 1970 model even allowed something JSON-like via *"nonsimple domains,"* so this is arguably the model returning to an old idea [p. 83].
- Practically: *"SQL vs NoSQL"* is a false binary; a modern PostgreSQL gives you both shapes in one database.

### 🗺️ One honest paragraph on graphs

**When many-to-many connections don't just exist but *dominate*** — your data is mostly relationships, traversed many hops deep — even the join starts to strain, and it becomes natural to model the data as a **graph** [p. 84].

- A graph has two kinds of object: **vertices** (people, places, pages) and **edges** (relationships between them) [p. 84].
- Social graphs, the web's link graph, and road networks are the classic examples, home to algorithms like shortest-path and PageRank [p. 84].
- **Property graph:** The dominant flavor is the **property graph** (Neo4j, Amazon Neptune): each vertex and edge carries a label and key-value properties, any vertex can connect to any other, and you traverse forward *and* backward efficiently [p. 86–87].
- The tell that you want one is a query traversing a **variable** number of hops — *"everyone within N degrees of this person"* — which SQL expresses clumsily (recursive CTEs) and a graph language (Cypher, SPARQL, Datalog — out of scope here) expresses in a line [p. 90–91].
- Reality check: even relationship-heavy companies often run their core social data on relational stores, so name the graph option but don't reach for it by reflex.

### 📜 A different answer entirely: event sourcing & CQRS

**Every model so far shares an assumption: you query data in roughly the same shape you wrote it. Event sourcing rejects that [p. 101].**

Instead of storing current state, you store the *log of everything that happened* — an append-only sequence of immutable, past-tense events (*"seats were booked,"* *"booking was cancelled"*), where a later cancellation is a *new* event, not an edit [p. 101, 103]. From that write-optimized log you derive whatever read-optimized views you need, each a **materialized view** (projection / read model) [p. 102]. Keeping the events as the source of truth is *event sourcing*; maintaining the derived read representations is **CQRS** (command query responsibility segregation) [p. 102].

**The payoff is real:**

events capture *intent* (*"booking cancelled"* vs a raw row mutation), the log doubles as an audit trail, and views can be deleted and recomputed to fix a bug or spun up freshly in any data model over the same events [p. 103–104]. So are the costs: processing must be deterministic (fold external facts like an exchange rate *into* the event, don't re-query a live one), and immutability collides with a right-to-be-forgotten deletion when one log mixes many users' data [p. 104]. This is only an introduction — a later patterns lesson develops it properly. For now, register it as a genuinely *different* answer to *"what is the data?"*: not a snapshot of the present, but the full history that produced it.

---

## ⚖️ Trade-offs

| Model / choice | Gives you | Costs you | Use when |
| --- | --- | --- | --- |
| **Relational** | Cheap joins; strong many-to-one and many-to-many support; enforced schema | Impedance mismatch with objects; join cost can bite at extreme scale | Data is a web of cross-references queried in multiple directions (the default choice) |
| **Document** | Tree-shaped data as one self-contained read; locality; closeness to app objects; flexible schema | Weak joins; many-to-many is awkward; whole-document rewrites; easy stale duplication | Data is a load-together tree of one-to-few relationships with few inter-document links |
| **Graph (property graph)** | Any-to-any connections; efficient forward/backward, variable-hop traversal | Operational complexity; specialized query languages; overkill for most cases | Data is *dominated* by many-to-many links traversed many hops deep |
| **Normalize ↔ denormalize** | Normalize: one copy, cheap writes, no self-contradiction. Denormalize: pre-assembled, fast reads | Normalize: reads pay joins. Denormalize: copies must stay in sync; more storage; write amplification | Normalize for OLTP / write-heavy / changing facts; denormalize for read-heavy hot paths and analytics |
| **Schema-on-write ↔ on-read** | On-write: enforced, self-documenting structure. On-read: change shape by just writing new fields | On-write: migrations to change shape. On-read: no read-time guarantees; reading code carries the burden | On-write for uniform records; on-read for heterogeneous or externally-dictated data |
| **Event sourcing + CQRS** | Full history; intent captured; audit log; recomputable, multiple read views | Deterministic-processing discipline; deletion/GDPR friction; more moving parts | Auditability, temporal queries, or many divergent read shapes over one write stream |

---

## 🔢 Numbers that matter

Data modeling is more about shapes than arithmetic, but a few figures anchor the trade-offs:

- **N+1 queries.** Fetching N items then issuing one follow-up per item is N+1 round-trips versus a single join [p. 68] — the cost is N extra network round-trips, the gap between one request and fifty. (See [Latency, Throughput, and Percentiles](/synapse/system-design-from-first-principles/foundations/latency-throughput-percentiles) for why serial round-trips hurt.)
- **Fan-out cost.** One post by a user with F followers is one write as a live join, but F writes if you materialize the timeline. For a celebrity, F is in the *tens of millions* — which is why the largest accounts get a hybrid: fanned-out timelines for normal users, a read-time join for the mega-accounts. *Rule of thumb, not from source:* the fan-out-on-write vs fan-out-on-read line sits around follower counts in the high thousands to millions, tuned per system.
- **Timeline entry size.** X stores a post ID + user ID + a little extra per entry, *not* the post text [p. 74–75]. An ID is a handful of bytes; a post with media metadata is orders of magnitude larger — multiplied across every follower's timeline, that's the difference between gigabytes and petabytes.
- **Celebrity comments.** Embedding is fine for a résumé's handful of jobs but breaks at *"thousands of comments on a celebrity's post"* — a concrete marker for when one-to-few stops being few [p. 71].

For how to turn these into capacity estimates, see [Estimation and Numbers](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers).

---

## 🏭 In production

**The default is relational, and that's not a cop-out.**

- In real systems and interviews, the right first answer is almost always a relational database, PostgreSQL specifically — you reach for something exotic only when a requirement clearly signals it.
- The tired knock that relational databases *"don't scale"* is largely exaggerated: read replicas, sharding, connection pooling, and caching take them very far, and some of the largest companies in the world run on relational foundations.
- Scaling is about how you architect *around* the database, not just which one you pick.

**Denormalization is how production systems go fast — carefully.**

- The pattern that keeps it sane: *keep your source of truth clean and normalized, and push denormalization into a cache or derived view.*
- A Redis layer holding pre-computed joins in front of a normalized PostgreSQL gives fast reads without corrupting your system of record; when the derived copy drifts, you rebuild it from the clean source rather than untangling a corrupted primary.
- (X's materialized timeline is exactly this at scale: a precomputed join kept consistent by fan-out, storing only IDs [p. 74–75].)

**Foreign keys are a trade-off at scale, not a law.**

They enforce referential integrity — no post pointing at a deleted user — but the database validates them on every insert and update, so at very large scale some companies drop database-level foreign keys and enforce integrity in application code to buy write performance. Mentioning that trade-off, rather than treating foreign keys as sacred, is a senior signal. And because the two models have converged, production systems routinely mix them in one database — normalized tables for the interconnected core, JSON columns for the tree-shaped parts [p. 83]; you choose per piece of data, not per camp.

---

## 🪤 Pitfalls & interview traps

**Reaching for a graph or document database to sound sophisticated.** The most common self-inflicted wound. Graph and document stores *sound* advanced but add operational complexity, and the primary access patterns of most systems — even social ones — are handled fine by relational stores. Name the specialized option to show you know it exists, then justify why you're *not* using it.

<div style="border-left:4px solid #da5233;background:rgba(218,82,51,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

⚠️ **"NoSQL scales, SQL doesn't" is a false dichotomy — and a yellow flag when stated as fact.** The choice is driven by the *shape and access patterns* of your data, not by a scaling myth. Say "document, because this profile is a load-together tree with few cross-references," or "relational, because I'll query these relationships in both directions" — reasons an interviewer accepts. Reaching for a document store *purely* to scale, when your data is richly interconnected, trades a manageable performance problem for a much nastier consistency problem.

</div>

**Denormalizing by reflex, then eating the consistency bug.** Duplicating a value into a hot read path feels free until the value changes and copies disagree. Denormalized data is *derived* data and needs a process to keep it in sync [p. 74]. Start normalized; denormalize only where a real access pattern demands it, and only for *stable* values — copy an ID, never a fast-changing like counter, which is why X denormalizes IDs but not counts [p. 75]. Be explicit about how copies stay consistent (a transaction, a stream processor, or a rebuildable cache) [p. 74].

**Calling document databases "schemaless."** They aren't — the schema is implicit and enforced by your reading code instead of the database [p. 80]. Say **schema-on-read vs schema-on-write** and you signal you understand the trade-off rather than parroting a marketing word [p. 80].

**Freezing on the *"core entities"* step.** This should take about two minutes. Name the nouns from the problem domain — for a Twitter-like system, `users`, `tweets`, `follows`, not abstract *"entities"* — give each a system-generated ID (not an email or other business data, which can change), sketch the foreign keys, and move on. Then tie any indexing or denormalization choice to a specific access pattern from your API — *"since we load feeds by follower and likes can be eventually consistent, I'll denormalize the like count into a derived view"* — which shows reasoning rather than pattern-matching.

---

## ✅ Check yourself

```quiz
{"prompt": "You're modeling user profiles for a résumé site. Each profile has a handful of jobs and schools, and you almost always load the whole profile at once. Profiles rarely reference each other. Which model fits most naturally?", "options": ["Document — the profile is a load-together tree of one-to-few relationships", "Relational with heavy normalization — split jobs and schools into separate tables joined on every read", "Graph — jobs and schools are relationships, so a graph database is the natural home", "Key-value — store each profile blob under the user ID and never query into it"], "answer": "Document — the profile is a load-together tree of one-to-few relationships"}
```

```quiz
{"prompt": "X stores only the post ID and poster's user ID in each materialized home-timeline entry, not the post text or the author's current avatar. Why store just the IDs?", "options": ["Because the referenced data (like counts, avatars) changes fast, so denormalizing it into millions of timelines would be instantly stale and explode storage", "Because relational databases cannot store text inside a timeline table", "Because IDs are the only thing a join is allowed to use", "Because storing text would violate the schema-on-read model"], "answer": "Because the referenced data (like counts, avatars) changes fast, so denormalizing it into millions of timelines would be instantly stale and explode storage"}
```

```quiz
{"prompt": "Your data is a set of independent profile trees today, but a new feature needs to query 'which users work at organization X' AND 'which organizations does user Y work at' — the same relationship, both directions. What does this pressure push you toward?", "options": ["A normalized relational representation storing the relationship once, with secondary indexes to query it efficiently in both directions", "Embedding the full organization document inside every user document that references it", "Denormalizing the relationship onto both sides so each is readable without a lookup", "A key-value store keyed by user ID only"], "answer": "A normalized relational representation storing the relationship once, with secondary indexes to query it efficiently in both directions"}
```

```quiz
{"prompt": "An interviewer asks why you'd choose schema-on-write (an enforced relational schema) over calling MongoDB 'schemaless.' What is the most accurate reasoning?", "options": ["When all records share one structure, an enforced schema documents and guarantees it — and 'schemaless' is misleading anyway, since the reading code always assumes a structure", "Schema-on-write is always faster than schema-on-read for every workload", "Document databases genuinely have no schema, so there is nothing to reason about", "Schema-on-write removes the need for any application-side validation ever"], "answer": "When all records share one structure, an enforced schema documents and guarantees it — and 'schemaless' is misleading anyway, since the reading code always assumes a structure"}
```

<details>
<summary>Answer: A junior engineer duplicates each user's display name into every one of their posts "to avoid the join." What breaks, and what's the disciplined alternative?</summary>

Denormalized data is **derived** data: the moment the user renames themselves, every copied name must be rewritten, and any missed update leaves the data contradicting itself [p. 72, 74]. The join they avoided was cheap; the consistency bug isn't. Keep the source of truth **normalized** (the name lives once in `users`) and, if reads genuinely need to be faster, push a denormalized copy into a **cache or derived view** rebuildable from the clean source when it drifts [p. 75] — only where a real access pattern demands it, and only for values that don't change often.

</details>

<details>
<summary>Answer: What single question should you ask about your data before choosing between the relational and document models?</summary>

*What kind of relationships dominate my data?* Mostly **one-to-many, tree-shaped, load-together** data with few inter-record links → document, for locality [p. 71, 80]. A web of **many-to-one and many-to-many** cross-references queried in multiple directions → relational, which makes those joins cheap and keeps one clean copy of each fact [p. 75–76]. The model follows the shape of the relationships — and thanks to convergence, a modern relational database can serve both shapes if needed [p. 83].

</details>

---

## 🔬 PoC — Proof of concepts

The three data models this lesson contrasts, in the systems that made each one's case:

- [PostgreSQL — JSON types](https://www.postgresql.org/docs/current/datatype-json.html) — the
  relational model *and* the document model in one engine (`jsonb`, containment, GIN indexes), which
  is exactly the *"why choose?"* this lesson raises.
- [Neo4j](https://github.com/neo4j/neo4j) — the reference property-graph database; read its Cypher
  examples to see relationship-first modelling that a join table only approximates.
- [System Design Primer — SQL vs NoSQL](https://github.com/donnemartin/system-design-primer) — the
  decision table, with the access patterns that push you toward one shape or the other.

---

## 📚 Sources

- DDIA2 ch. 3 pp. 65–67 (data models as the most consequential layer; the stack of models; relational model origins)
- DDIA2 ch. 3 pp. 68–71 (object-relational impedance mismatch; N+1 query problem; one-to-many résumé as a tree; document locality; one-to-few limit)
- DDIA2 ch. 3 pp. 72–75 (normalization vs denormalization; what a join buys; the read/write trade-off principle; X/Twitter timeline as a cached join; ID hydration; denormalize-some/normalize-some)
- DDIA2 ch. 3 pp. 75–76 (many-to-one and many-to-many; associative/join tables; document references; querying both directions)
- DDIA2 ch. 3 pp. 80–82 (when to use which model; *"schemaless"* is misleading; schema-on-read vs schema-on-write; data locality and its limits)
- DDIA2 ch. 3 p. 83 (convergence of relational and document; JSON columns; Codd's nonsimple domains)
- DDIA2 ch. 3 pp. 84–90 (graph-like data models; vertices and edges; property graphs; variable-hop traversal and why SQL is clumsy at it)
- DDIA2 ch. 3 pp. 101–104 (event sourcing and CQRS; append-only event log; materialized views/projections; past-tense events; benefits and deletion/determinism costs)

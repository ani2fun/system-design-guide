---
title: Search index
kind: Search index
technology: Postgres FTS (POC) / Elasticsearch
---

## 🔎 Search index

An **inverted index** over events, venues, and dates — because the naive alternative, `WHERE name LIKE '%taylor%'`, defeats a B-tree index with its leading wildcard and degenerates into a full scan, nowhere near the 500 ms search budget at catalog scale.

**Responsibilities**

- Map each term to the documents containing it, so keyword lookup is an index probe, not a scan.
- Serve the queries users actually type — keyword-in-the-middle matches, plus structured filters on date, location, and type.
- (Elasticsearch tier) absorb typos with fuzzy matching — *"Tayler Swift"* still finds the show.

The technology label is a ladder, and the honest move is naming which rung you're on. The POC uses **Postgres full-text search**: tokenized-word indexes with no new infrastructure, at the price of index storage and slower writes. At scale, a dedicated **Elasticsearch** cluster takes over, kept in sync via **change data capture** from Postgres — inserts, updates, and deletes streaming into the index near-real-time. Repeated queries get caching layered on top: normalized query → results in Redis, plus Elasticsearch's own node caches.

**Where it breaks.** The Elasticsearch rung buys speed with operational weight: a second stateful cluster, a sync pipeline that can lag or break, and **eventual consistency** between catalog and index — a just-created event may be briefly unsearchable. That's acceptable here precisely because search is on the availability side of the split posture; nothing in the booking invariant depends on it.

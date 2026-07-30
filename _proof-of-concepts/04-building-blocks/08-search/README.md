# POC: Inverted Index & Ranked Search

A runnable companion to **Search** (`04-building-blocks/08-search`). It builds an
inverted index, ranks with TF-IDF and BM25, then shards the corpus to show the
one detail interviews love: distributed ranking is only correct when the shards
score against **global** collection statistics.

| Piece | File | Role |
| --- | --- | --- |
| `analyze` | [`domain/tokenizer.py`](domain/tokenizer.py) | text → normalized terms (lowercase, stop-words) |
| `InvertedIndex` | [`domain/index.py`](domain/index.py) | term → postings; `search` walks only query-term postings |
| `TfIdf`, `BM25` | [`domain/scoring.py`](domain/scoring.py) | scorers behind one `Scorer` port; `CollectionStats` carries N / df / avg-len |
| `SearchCluster` | [`domain/cluster.py`](domain/cluster.py) | scatter-gather over shards; gathers global stats first |

## Run it

```bash
./run            # ranking + scatter-gather demonstration
./run test       # mypy --strict + unit tests + demo
./run check      # mypy only
```

Uses [`uv`](https://docs.astral.sh/uv/); no Docker, no ports, standard library only.

## What the demo proves

- **Ranking works:** a query for `raft leader log` puts the Raft document first;
  a rare term (`paxos`) outweighs a common one (`node`) via IDF; BM25 saturates
  term frequency and penalizes long documents where plain TF-IDF does not.
- **Scatter-gather is correct with global stats:** splitting the corpus across 4
  shards and merging each shard's top-k reproduces the single-index ranking
  **12/12** queries — *when* every shard scores against global `CollectionStats`.
- **Local stats drift:** if each shard uses only its own IDF, the merged ranking
  disagrees with the true ranking on some queries (**10/12** here) — because a
  term that's rare globally can look common on one shard, distorting its weight.

## What is simulated vs. real

A production search engine (Elasticsearch, Solr, a Lucene cluster) spreads its
index across **many machines**; a query fans out to every shard, each returns its
local top-k, and a coordinator merges them. This POC **mimics the shards in one
process**: `SHARDS = 4` `InvertedIndex` objects, each holding a slice of the
corpus, with `SearchCluster` doing the scatter and the gather in a loop.

What is **identical to production**: the inverted index, the TF-IDF/BM25 math, and
— most importantly — the *global-statistics problem*. Real distributed search
really does gather corpus-wide term statistics (Elasticsearch calls this the
`dfs_query_then_fetch` search type) precisely because per-shard IDF produces
inconsistent scores, exactly as the `local stats` run shows. Only the transport
(a method call instead of a network fan-out) and the corpus size (12 tiny docs)
are faked; the ranking and the reason global stats matter are real.

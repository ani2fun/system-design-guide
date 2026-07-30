"""SearchCluster — a scatter-gather query over sharded indexes, the way a real
distributed search engine works. Each shard indexes a slice of the corpus; a
query fans out to all shards and the coordinator merges their top-k.

The subtlety this demonstrates: BM25/TF-IDF need corpus-wide statistics (N,
document frequency, average length). If each shard scores with only its *local*
stats, scores are not comparable and the merged ranking is wrong. The fix —
what Elasticsearch does — is to gather global term statistics first and score
every shard against them.
"""

from __future__ import annotations

from domain.index import InvertedIndex
from domain.scoring import CollectionStats


class SearchCluster:
    def __init__(self, shards: list[InvertedIndex]) -> None:
        self._shards = shards

    def global_stats(self) -> CollectionStats:
        num_docs = 0
        doc_freq: dict[str, int] = {}
        total_len = 0.0
        for shard in self._shards:
            local = shard.local_stats()
            num_docs += local.num_docs
            total_len += local.avg_doc_len * local.num_docs
            for term, df in local.doc_freq.items():
                doc_freq[term] = doc_freq.get(term, 0) + df
        avg = total_len / num_docs if num_docs else 0.0
        return CollectionStats(num_docs, doc_freq, avg)

    def search(self, query: list[str], k: int, *, use_global_stats: bool = True) -> list[tuple[str, float]]:
        stats = self.global_stats() if use_global_stats else None
        gathered: list[tuple[str, float]] = []
        for shard in self._shards:
            gathered.extend(shard.search(query, k, stats))  # scatter: local top-k
        gathered.sort(key=lambda kv: (-kv[1], kv[0]))       # gather: merge + rank
        return gathered[:k]

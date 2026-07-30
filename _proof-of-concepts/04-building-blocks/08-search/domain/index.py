"""InvertedIndex — term → postings (doc → term-frequency), the core data
structure behind every search engine. `search` walks only the postings of the
query terms (never the whole corpus) and ranks candidates with the injected
`Scorer`, using externally supplied `CollectionStats` when given.
"""

from __future__ import annotations

from collections import Counter

from domain.scoring import CollectionStats, Scorer


class InvertedIndex:
    def __init__(self, scorer: Scorer) -> None:
        self._scorer = scorer
        self._postings: dict[str, dict[str, int]] = {}   # term -> {doc_id: tf}
        self._doc_len: dict[str, int] = {}

    def add(self, doc_id: str, tokens: list[str]) -> None:
        self._doc_len[doc_id] = len(tokens)
        for term, tf in Counter(tokens).items():
            self._postings.setdefault(term, {})[doc_id] = tf

    def local_stats(self) -> CollectionStats:
        n = len(self._doc_len)
        doc_freq = {term: len(postings) for term, postings in self._postings.items()}
        avg = sum(self._doc_len.values()) / n if n else 0.0
        return CollectionStats(n, doc_freq, avg)

    def search(
        self, query: list[str], k: int, stats: CollectionStats | None = None
    ) -> list[tuple[str, float]]:
        stats = stats or self.local_stats()
        scores: dict[str, float] = {}
        for term in set(query):
            postings = self._postings.get(term)
            if postings is None:
                continue
            for doc_id, tf in postings.items():
                scores[doc_id] = scores.get(doc_id, 0.0) + self._scorer.term_score(
                    term, tf, self._doc_len[doc_id], stats
                )
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:k]

"""Relevance scorers behind one explicit `Scorer` port (Dependency Inversion):
the index ranks with whatever scorer it is given. `CollectionStats` carries the
corpus-wide numbers a scorer needs (N, per-term document frequency, average
document length) — the values that must be *global* for shard scores to compare.
"""

from __future__ import annotations

import abc
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CollectionStats:
    num_docs: int
    doc_freq: dict[str, int]
    avg_doc_len: float


class Scorer(abc.ABC):
    name: str

    @abc.abstractmethod
    def term_score(self, term: str, tf: int, doc_len: int, stats: CollectionStats) -> float:
        """Contribution of one query term occurring `tf` times in a doc of length
        `doc_len`, given corpus statistics."""


class TfIdf(Scorer):
    name = "tf-idf"

    def term_score(self, term: str, tf: int, doc_len: int, stats: CollectionStats) -> float:
        df = stats.doc_freq.get(term, 0)
        if df == 0 or stats.num_docs == 0:
            return 0.0
        idf = math.log(1 + stats.num_docs / df)
        return tf * idf


class BM25(Scorer):
    """The Lucene/Elasticsearch default: TF saturates (k1) and long documents are
    penalized (b), which plain TF-IDF does not do."""

    name = "bm25"

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b

    def term_score(self, term: str, tf: int, doc_len: int, stats: CollectionStats) -> float:
        df = stats.doc_freq.get(term, 0)
        if df == 0 or stats.num_docs == 0 or stats.avg_doc_len == 0:
            return 0.0
        idf = math.log(1 + (stats.num_docs - df + 0.5) / (df + 0.5))
        norm = 1 - self._b + self._b * doc_len / stats.avg_doc_len
        return idf * (tf * (self._k1 + 1)) / (tf + self._k1 * norm)

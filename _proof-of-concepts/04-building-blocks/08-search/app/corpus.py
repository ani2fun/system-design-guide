"""A tiny in-memory corpus of short technical blurbs — enough to make ranking
and sharding observable without any external data.
"""

from __future__ import annotations

CORPUS: dict[str, str] = {
    "replication": "Replication keeps copies of data on multiple nodes for availability and read scaling.",
    "consensus": "Consensus protocols like Raft and Paxos let distributed nodes agree on one value despite failures.",
    "raft": "Raft is a consensus algorithm that elects a leader and replicates a log across nodes.",
    "sharding": "Sharding partitions data across nodes so each node stores only a subset of the keyspace.",
    "consistent-hashing": "Consistent hashing maps keys to nodes on a ring so adding a node moves few keys.",
    "caching": "Caching stores hot data in fast memory to reduce latency and database load.",
    "cache-invalidation": "Cache invalidation decides when cached data is stale and must be refreshed or evicted.",
    "bloom-filter": "A bloom filter is a probabilistic structure for fast set membership with no false negatives.",
    "load-balancing": "Load balancing spreads requests across backend nodes to avoid overloading any single node.",
    "message-queue": "A message queue buffers events between producers and consumers for asynchronous processing.",
    "kafka": "Kafka is a distributed log that partitions and replicates event streams across brokers.",
    "search": "An inverted index maps each term to the documents that contain it, enabling fast full-text search.",
}

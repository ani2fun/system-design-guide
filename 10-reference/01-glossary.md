---
title: "Glossary"
summary: "Fast lookup for the load-bearing terms this book uses, each linked to the lesson that teaches it."
essential: false
---

# 📖 Glossary

A curated, skimmable index of the terms this book leans on most — from storage internals to consensus to production operations. Each entry gives a one-sentence working definition and a `→` link to the lesson that teaches it in depth; follow the link when you want the mechanism, the trade-offs, and the numbers. Terms are grouped by theme and listed alphabetically within each group.

<div style="border-left:4px solid #15448e;background:rgba(21,68,142,0.08);padding:0.6rem 1rem;border-radius:0 0.5rem 0.5rem 0;margin:1.25rem 0">

📖 This is a reference, not a lesson. Definitions are deliberately terse — the linked lesson is the source of truth for meaning, caveats, and where the simplification bites.

</div>

## 🧭 Foundations & data models

- **API gateway** — a single front door that terminates client requests and handles cross-cutting concerns (auth, rate limiting, routing) before fanning out to services. → [Load balancing & gateways](/synapse/system-design-from-first-principles/building-blocks/load-balancing-and-gateways)
- **Back-of-the-envelope estimation** — sizing a design with rough order-of-magnitude arithmetic (QPS, storage, bandwidth) before committing to it. → [Estimation & the numbers](/synapse/system-design-from-first-principles/foundations/estimation-and-numbers)
- **Column-oriented (columnar) storage** — laying out all values of a column together rather than all values of a row, so analytical scans read only the columns they need. → [Analytics & column stores](/synapse/system-design-from-first-principles/data-foundations/analytics-and-column-stores)
- **Data lake** — a central repository of raw copies of any potentially useful data, stored as files with no schema imposed until read. → [Analytics & column stores](/synapse/system-design-from-first-principles/data-foundations/analytics-and-column-stores)
- **Data warehouse** — a separate read-only database holding copies of operational data, optimized for unrestricted analytical querying. → [Analytics & column stores](/synapse/system-design-from-first-principles/data-foundations/analytics-and-column-stores)
- **Denormalization** — deliberately duplicating human-meaningful data across records to avoid joins at read time, trading write cost and consistency for read speed. → [Data models](/synapse/system-design-from-first-principles/data-foundations/data-models)
- **Derived data** — data (a cache, index, materialized view, or ML model) produced from a system of record by a deterministic transformation and re-creatable from it. → [Data models](/synapse/system-design-from-first-principles/data-foundations/data-models)
- **Encoding (serialization)** — translating an in-memory structure into a self-contained byte sequence for storage or transmission; decoding is the reverse. → [Encoding & evolution](/synapse/system-design-from-first-principles/data-foundations/encoding-and-evolution)
- **Event log** — an append-only sequence of immutable, timestamped, self-contained event records. → [Data models](/synapse/system-design-from-first-principles/data-foundations/data-models)
- **Forward / backward compatibility** — backward = new code reads old data; forward = old code reads new data; both are required for zero-downtime rollouts. → [Encoding & evolution](/synapse/system-design-from-first-principles/data-foundations/encoding-and-evolution)
- **Functional vs. nonfunctional requirements** — what the system must *do* (features, operations) versus the cross-cutting properties it must *have* (fast, reliable, secure, scalable). → [Nonfunctional requirements](/synapse/system-design-from-first-principles/foundations/nonfunctional-requirements)
- **Latency vs. throughput** — latency is the time a single request takes; throughput is how many requests per second the system sustains. → [Latency, throughput & percentiles](/synapse/system-design-from-first-principles/foundations/latency-throughput-percentiles)
- **Materialized view** — a precomputed, stored query result kept up to date as its inputs change, making reads cheap at the cost of write work. → [Data models](/synapse/system-design-from-first-principles/data-foundations/data-models)
- **Normalization** — storing each human-meaningful fact in exactly one place and referring to it by ID elsewhere, so updates touch a single row. → [Data models](/synapse/system-design-from-first-principles/data-foundations/data-models)
- **OLTP vs. OLAP** — online transaction processing (fast point queries and record CRUD) versus online analytical processing (scanning many rows to compute aggregates). → [Data models](/synapse/system-design-from-first-principles/data-foundations/data-models)
- **Percentile / tail latency** — p50/p95/p99 are the values below which that fraction of requests fall; the high percentiles (*"the tail"*) are what users actually feel. → [Latency, throughput & percentiles](/synapse/system-design-from-first-principles/foundations/latency-throughput-percentiles)
- **REST vs. RPC** — REST models resources behind HTTP verbs and URLs; RPC makes a remote call look like a local function invocation. → [API design](/synapse/system-design-from-first-principles/foundations/api-design)
- **Schema-on-read vs. schema-on-write** — interpret structure only when data is read (flexible, implicit) versus enforce it at write time (validated, explicit). → [Data models](/synapse/system-design-from-first-principles/data-foundations/data-models)
- **Schema evolution** — changing a schema over time while keeping old and new code able to read each other's data. → [Encoding & evolution](/synapse/system-design-from-first-principles/data-foundations/encoding-and-evolution)
- **Shared-nothing architecture** — scaling out across independent nodes that share no memory or disk and coordinate only over the network. → [Nonfunctional requirements](/synapse/system-design-from-first-principles/foundations/nonfunctional-requirements)
- **Tail-latency amplification** — the rising share of slow end-user requests as each request fans out to more backend calls, since it waits on the slowest of them. → [Latency, throughput & percentiles](/synapse/system-design-from-first-principles/foundations/latency-throughput-percentiles)
- **Vertical vs. horizontal scaling** — scaling up to a bigger single machine versus scaling out by adding more machines. → [Nonfunctional requirements](/synapse/system-design-from-first-principles/foundations/nonfunctional-requirements)

---

## 🗄️ Storage & indexing

- **B-tree** — an update-in-place index of fixed-size pages forming a balanced tree of key ranges; the default index in most relational databases. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)
- **Bloom filter** — a probabilistic bitmap membership test with no false negatives but occasional false positives, used to skip disk lookups for absent keys. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)
- **Clustered / covering index** — a clustered index stores the row inside the index; a covering index stores enough extra columns to answer a query from the index alone. → [Indexing](/synapse/system-design-from-first-principles/data-foundations/indexing)
- **Compaction** — the background process that merges storage segments and discards overwritten or deleted values to reclaim space. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)
- **Geohash** — encoding a latitude/longitude into a short string whose shared prefixes mean spatial proximity, enabling range-based geospatial lookups. → [Specialized Stores: Geo, Time-series & Vectors](/synapse/system-design-from-first-principles/building-blocks/specialized-stores)
- **Inverted index** — a term → document-ID postings structure that powers full-text search. → [Search](/synapse/system-design-from-first-principles/building-blocks/search)
- **LSM-tree** — a storage engine built on buffering writes in memory and merging sorted, immutable on-disk files, optimizing for write throughput. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)
- **Memtable** — the in-memory ordered structure that buffers writes before they are flushed to an on-disk sorted file. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)
- **Page** — the fixed-size block (traditionally ~4 KiB) that a B-tree reads and overwrites as a unit. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)
- **Secondary index** — an additional index on a non-primary column, letting queries find rows by attributes other than the primary key. → [Indexing](/synapse/system-design-from-first-principles/data-foundations/indexing)
- **SSTable (Sorted String Table)** — an immutable file of key-value pairs sorted by key, with each key appearing once. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)
- **Tombstone** — a special deletion marker appended to a log so that later compaction discards the key's prior values. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)
- **Vector embedding / vector index** — a float vector locating an item in semantic space, searched with approximate-nearest-neighbor indexes (IVF, HNSW). → [Specialized stores](/synapse/system-design-from-first-principles/building-blocks/specialized-stores)
- **WAL (write-ahead log)** — an append-only file written before applying a change to the main structure, so a crash can be recovered by replaying it. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)
- **Write / read amplification** — the ratio of bytes actually written to (or read from) disk versus the logical bytes of the operation; a key storage-engine trade-off. → [Storage engines](/synapse/system-design-from-first-principles/data-foundations/storage-engines)

---

## 🔁 Replication & partitioning

- **Anti-entropy** — a background process that continuously copies differences between replicas to bring them back into agreement. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Consistent hashing** — a hashing scheme that keeps keys roughly evenly distributed across nodes while moving as few keys as possible when the node set changes. → [Sharding & consistent hashing](/synapse/system-design-from-first-principles/distributed-data/sharding-and-consistent-hashing)
- **CRDT (conflict-free replicated data type)** — a data type whose concurrent writes always auto-merge to the same result, giving strong eventual consistency without coordination. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Eventual consistency** — a guarantee that replicas may lag but will converge to the same state once writes stop. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Failover** — promoting a follower to leader after the leader fails and reconfiguring the system to use it. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Hinted handoff** — a reachable replica temporarily storing writes on behalf of an unavailable one, then replaying them when it recovers. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Hot key / hot shard** — a single key (e.g. a celebrity account) or a single shard receiving disproportionately high load. → [Sharding & consistent hashing](/synapse/system-design-from-first-principles/distributed-data/sharding-and-consistent-hashing)
- **Leader / follower** — the leader (primary) accepts writes and streams the change log; followers (read replicas) apply that log and serve reads. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Leaderless replication** — a scheme where any replica accepts writes with no enforced ordering, using quorums and read repair to converge (Dynamo-style). → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Monotonic reads** — a guarantee that a user's successive reads never move backward in time to an older state. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Multi-leader replication** — a topology where more than one node accepts writes, requiring conflict resolution when they diverge. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Partition key** — the value that decides which shard a record lands on; all records with the same partition key co-locate. → [Sharding & consistent hashing](/synapse/system-design-from-first-principles/distributed-data/sharding-and-consistent-hashing)
- **Quorum (w + r > n)** — requiring write and read sets to overlap across replicas so a read is guaranteed to see the latest committed write. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Read-your-writes (read-after-write)** — a guarantee that a user always sees the updates they themselves just submitted. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Read repair** — a client detecting a stale replica during a parallel read and writing the newer value back to it. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Replication lag** — the delay between a write committing on the leader and it appearing on a follower. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Resharding / rebalancing** — redistributing shards across nodes as the cluster or data volume changes, ideally moving minimal data. → [Sharding & consistent hashing](/synapse/system-design-from-first-principles/distributed-data/sharding-and-consistent-hashing)
- **Shard (partition)** — a subset of the dataset that behaves as a small database of its own, with each record belonging to exactly one shard. → [Sharding & consistent hashing](/synapse/system-design-from-first-principles/distributed-data/sharding-and-consistent-hashing)
- **Sharding** — splitting a dataset across nodes by partition key so each node holds and serves only a slice. → [Sharding & consistent hashing](/synapse/system-design-from-first-principles/distributed-data/sharding-and-consistent-hashing)
- **Skew** — an uneven distribution where some shards hold more data or serve more requests than others, undermining the point of sharding. → [Sharding & consistent hashing](/synapse/system-design-from-first-principles/distributed-data/sharding-and-consistent-hashing)
- **Sloppy quorum** — accepting writes on any reachable replicas when the designated ones are down, boosting availability at the cost of consistency. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Split brain** — the failure mode where two nodes each believe they are the leader and make conflicting decisions. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Synchronous vs. asynchronous replication** — the leader either waits for a follower to confirm before reporting success (durable, slower) or does not (fast, can lose recent writes on failover). → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)
- **Version vector** — a set of per-replica counters attached to a value, used to tell whether two writes were concurrent or causally ordered. → [Replication](/synapse/system-design-from-first-principles/distributed-data/replication)

---

## 🔒 Transactions & consistency

- **2PC (two-phase commit)** — a coordinator-driven prepare-then-commit protocol that makes a transaction spanning multiple nodes atomic. → [Distributed transactions](/synapse/system-design-from-first-principles/distributed-data/distributed-transactions)
- **ACID** — the transaction guarantees of Atomicity, Consistency, Isolation, and Durability. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Atomicity** — a transaction either applies all of its writes or, on any fault, aborts and applies none (all-or-nothing). → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **CAP theorem** — during a network partition a system must choose between consistency (linearizable but unavailable) and availability (up but non-linearizable). → [CAP & PACELC, honestly](/synapse/system-design-from-first-principles/distributed-data/cap-and-pacelc-honestly)
- **Compare-and-set (CAS) / optimistic locking** — writing a value only if it (or its version number) is unchanged since it was read, detecting concurrent modification. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Dirty read / dirty write** — reading (or overwriting) another transaction's uncommitted write. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Distributed transaction** — a transaction whose reads and writes span multiple nodes or shards, requiring an atomic commitment protocol. → [Distributed transactions](/synapse/system-design-from-first-principles/distributed-data/distributed-transactions)
- **Isolation level** — the degree to which concurrent transactions are shielded from each other's intermediate state (read committed, snapshot isolation, serializable). → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Linearizability** — a recency guarantee that the system behaves as if there is one copy of the data and every operation takes effect atomically at a single point in time. → [Linearizability & ordering](/synapse/system-design-from-first-principles/distributed-data/linearizability-and-ordering)
- **Lost update** — two concurrent read-modify-write cycles where one silently clobbers the other's change. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **MVCC (multi-version concurrency control)** — keeping multiple committed versions of a row so each transaction reads a consistent point-in-time snapshot without blocking writers. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **PACELC** — an extension of CAP: if Partitioned, trade Availability vs. Consistency; Else, trade Latency vs. Consistency. → [CAP & PACELC, honestly](/synapse/system-design-from-first-principles/distributed-data/cap-and-pacelc-honestly)
- **Phantom** — a write in one transaction changing the set of rows that match another transaction's search query. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Read committed** — an isolation level guaranteeing no dirty reads and no dirty writes. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Repeatable read** — an SQL-standard isolation level whose exact meaning varies widely across databases; often equated with snapshot isolation. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Serializability** — the strongest isolation: the concurrent result always equals *some* serial, one-at-a-time execution of the transactions. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Snapshot isolation** — each transaction reads from a consistent snapshot of everything committed as of its start, typically implemented with MVCC. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Strict serializability** — serializability plus linearizability: a serial order that also respects real-time ordering. → [Linearizability & ordering](/synapse/system-design-from-first-principles/distributed-data/linearizability-and-ordering)
- **Two-phase locking (2PL)** — enforcing serializability by acquiring shared/exclusive locks and holding them until the transaction commits. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **Write skew** — two transactions read overlapping data and update different rows, together breaking an invariant neither violated alone. → [Transactions & isolation](/synapse/system-design-from-first-principles/distributed-data/transactions-and-isolation)
- **XA** — a standard C API for coordinating two-phase commit across heterogeneous systems (databases and message brokers). → [Distributed transactions](/synapse/system-design-from-first-principles/distributed-data/distributed-transactions)

---

## 🗳️ Consensus & coordination

- **Byzantine fault** — a node that may lie, sending arbitrary or corrupted responses rather than simply crashing. → [Faults, clocks & time](/synapse/system-design-from-first-principles/distributed-data/faults-clocks-and-time)
- **Clock drift** — a physical clock running slightly fast or slow, so machine clocks diverge and cannot be trusted for ordering. → [Faults, clocks & time](/synapse/system-design-from-first-principles/distributed-data/faults-clocks-and-time)
- **Consensus** — getting multiple nodes to agree on a single value despite failures; the core problem behind fault-tolerant leader election and ordering. → [Consensus & coordination](/synapse/system-design-from-first-principles/distributed-data/consensus-and-coordination)
- **Coordination service** — a consensus-backed system (ZooKeeper, etcd, Consul) providing locks, leases, leader election, and failure detection for other services. → [Consensus & coordination](/synapse/system-design-from-first-principles/distributed-data/consensus-and-coordination)
- **Epoch (term / ballot / view)** — a monotonically increasing election number within which the consensus leader is guaranteed unique. → [Consensus & coordination](/synapse/system-design-from-first-principles/distributed-data/consensus-and-coordination)
- **Fencing token** — a monotonically increasing number issued with each lock grant; storage rejects any write carrying a token lower than one already seen. → [Faults, clocks & time](/synapse/system-design-from-first-principles/distributed-data/faults-clocks-and-time)
- **Fencing** — cutting off or shutting down a stale leader or lease holder so it cannot cause split-brain damage. → [Faults, clocks & time](/synapse/system-design-from-first-principles/distributed-data/faults-clocks-and-time)
- **FLP result** — the impossibility theorem that no deterministic asynchronous algorithm can guarantee consensus terminates if even one node may crash. → [Consensus & coordination](/synapse/system-design-from-first-principles/distributed-data/consensus-and-coordination)
- **Happens-before** — the causal relation where A happens before B if B could have been influenced by A; unrelated events are concurrent. → [Linearizability & ordering](/synapse/system-design-from-first-principles/distributed-data/linearizability-and-ordering)
- **Lamport clock** — a logical clock producing (counter, node-ID) timestamps that give a total order consistent with causality. → [Linearizability & ordering](/synapse/system-design-from-first-principles/distributed-data/linearizability-and-ordering)
- **Lease** — a lock with a timeout that can be reassigned to a new owner if the current holder stops renewing it. → [Consensus & coordination](/synapse/system-design-from-first-principles/distributed-data/consensus-and-coordination)
- **Logical clock** — a counter that orders events by causality rather than by wall-clock time, giving comparable but non-real timestamps. → [Linearizability & ordering](/synapse/system-design-from-first-principles/distributed-data/linearizability-and-ordering)
- **Monotonic vs. wall-clock time** — a monotonic clock only moves forward and is for measuring durations; a wall-clock (time-of-day) can jump backward and must not be used for elapsed time. → [Faults, clocks & time](/synapse/system-design-from-first-principles/distributed-data/faults-clocks-and-time)
- **Network partition** — a fault that cuts one part of the network off from another while both sides keep running. → [Faults, clocks & time](/synapse/system-design-from-first-principles/distributed-data/faults-clocks-and-time)
- **State machine replication** — replicating a service by applying the same ordered log of deterministic operations on every node so they converge. → [Consensus & coordination](/synapse/system-design-from-first-principles/distributed-data/consensus-and-coordination)
- **Total order broadcast** — delivering messages to all nodes in the same order; equivalent to consensus and the basis of a shared log. → [Consensus & coordination](/synapse/system-design-from-first-principles/distributed-data/consensus-and-coordination)
- **Vector clock** — a set of per-node counters stored with each write, able to detect whether two writes were concurrent. → [Linearizability & ordering](/synapse/system-design-from-first-principles/distributed-data/linearizability-and-ordering)
- **Zombie** — a former lease or lock holder that has not yet learned it lost the lease and still acts as if it holds it. → [Faults, clocks & time](/synapse/system-design-from-first-principles/distributed-data/faults-clocks-and-time)

---

## 🧱 Infrastructure building blocks

- **Acknowledgment** — a consumer's explicit signal that it finished processing a message, letting the broker remove or advance past it. → [Queues & brokers](/synapse/system-design-from-first-principles/building-blocks/queues-and-brokers)
- **Backpressure** — a downstream component signaling upstream to slow down when its buffer or capacity is exhausted, instead of dropping or piling up work. → [Stream processing](/synapse/system-design-from-first-principles/building-blocks/stream-processing)
- **Cache-aside (lazy loading)** — the application reads the cache, and on a miss loads from the database and populates the cache itself. → [Caching](/synapse/system-design-from-first-principles/building-blocks/caching)
- **CDN (content delivery network)** — a geographically distributed edge network that caches content close to users to cut latency and offload origin. → [CDN & edge](/synapse/system-design-from-first-principles/building-blocks/cdn-and-edge)
- **Consumer group** — a set of consumers sharing a topic's messages, load-balancing within the group while different groups each get the full stream. → [Queues & brokers](/synapse/system-design-from-first-principles/building-blocks/queues-and-brokers)
- **Dead-letter queue (DLQ)** — a side queue for messages that repeatedly fail processing, so they stop blocking the main queue. → [Queues & brokers](/synapse/system-design-from-first-principles/building-blocks/queues-and-brokers)
- **Edge / point of presence (PoP)** — a location near users where CDN or edge compute runs, terminating connections far from the origin. → [CDN & edge](/synapse/system-design-from-first-principles/building-blocks/cdn-and-edge)
- **Event time vs. processing time** — the time an event actually occurred (embedded in it) versus the time the system happened to process it; they diverge under delay. → [Stream processing](/synapse/system-design-from-first-principles/building-blocks/stream-processing)
- **Load balancer** — a component that spreads incoming requests across multiple backend instances for scale and fault tolerance. → [Load balancing & gateways](/synapse/system-design-from-first-principles/building-blocks/load-balancing-and-gateways)
- **Message broker** — a server that durably stores messages between producers and consumers, decoupling them in time and rate (Kafka, RabbitMQ, SQS). → [Queues & brokers](/synapse/system-design-from-first-principles/building-blocks/queues-and-brokers)
- **Object storage / blob store** — a service (S3, GCS, Azure Blob) storing large immutable objects by bucket and key behind a get/put API, not a filesystem. → [Object storage & blobs](/synapse/system-design-from-first-principles/building-blocks/object-storage-and-blobs)
- **Offset** — the monotonically increasing sequence number a broker assigns each message within a log partition; consumers track how far they have read. → [Queues & brokers](/synapse/system-design-from-first-principles/building-blocks/queues-and-brokers)
- **Presigned URL** — a time-limited signed link that lets a client upload or download an object directly to/from object storage without proxying through a service. → [Object storage & blobs](/synapse/system-design-from-first-principles/building-blocks/object-storage-and-blobs)
- **Thundering herd (cache stampede)** — many requests simultaneously missing on the same expired key and all hitting the database at once. → [Caching](/synapse/system-design-from-first-principles/building-blocks/caching)
- **TTL (time to live)** — an expiry duration after which a cached entry (or record) is considered stale and evicted. → [Caching](/synapse/system-design-from-first-principles/building-blocks/caching)
- **Tumbling / hopping / sliding / session window** — the ways stream processing groups events over time: fixed non-overlapping, fixed overlapping, continuously sliding, or bounded by inactivity. → [Stream processing](/synapse/system-design-from-first-principles/building-blocks/stream-processing)
- **Watermark** — a moving marker asserting that all events up to a given event-time have (probably) arrived, so a window can be closed. → [Stream processing](/synapse/system-design-from-first-principles/building-blocks/stream-processing)
- **WebSockets / SSE** — persistent connections for pushing real-time updates to clients: WebSockets are bidirectional, server-sent events are one-way server→client. → [Real-time delivery](/synapse/system-design-from-first-principles/building-blocks/realtime-delivery)
- **Write-through / write-behind** — write-through updates cache and database synchronously; write-behind writes the cache first and flushes to the database asynchronously. → [Caching](/synapse/system-design-from-first-principles/building-blocks/caching)

---

## 🧩 Patterns

- **At-least-once delivery** — a messaging guarantee that a message is never lost but may be delivered more than once, forcing consumers to be idempotent. → [Idempotency & exactly-once](/synapse/system-design-from-first-principles/patterns/idempotency-and-exactly-once)
- **Change data capture (CDC)** — observing a database's row-level changes and emitting them as a stream to keep other systems in sync. → [Event-driven: CQRS, outbox, CDC](/synapse/system-design-from-first-principles/patterns/event-driven-cqrs-outbox-cdc)
- **Compensation (compensating transaction)** — a later corrective action that semantically undoes an earlier step when a multi-step process fails partway. → [Multi-step processes & sagas](/synapse/system-design-from-first-principles/patterns/multi-step-processes-and-sagas)
- **Contention** — multiple operations competing for the same resource or row, forcing serialization and limiting throughput. → [Dealing with contention](/synapse/system-design-from-first-principles/patterns/dealing-with-contention)
- **CQRS (command query responsibility segregation)** — maintaining separate write-optimized and read-optimized models, with reads derived from writes. → [Event-driven: CQRS, outbox, CDC](/synapse/system-design-from-first-principles/patterns/event-driven-cqrs-outbox-cdc)
- **Event sourcing** — treating an append-only log of events as the source of truth and deriving all current state from it. → [Event-driven: CQRS, outbox, CDC](/synapse/system-design-from-first-principles/patterns/event-driven-cqrs-outbox-cdc)
- **Exactly-once (effectively-once)** — arranging processing so the observable effect equals a single successful run despite retries, via atomic commit or idempotent deduplication. → [Idempotency & exactly-once](/synapse/system-design-from-first-principles/patterns/idempotency-and-exactly-once)
- **Fan-in** — many upstream sources converging into a single consumer or aggregation point. → [Fan-out: push vs. pull](/synapse/system-design-from-first-principles/patterns/fan-out-push-vs-pull)
- **Fan-out (on write vs. on read)** — pushing a new item into each recipient's precomputed feed at write time, versus assembling the feed by pulling from sources at read time. → [Fan-out: push vs. pull](/synapse/system-design-from-first-principles/patterns/fan-out-push-vs-pull)
- **Idempotency** — the property that performing an operation multiple times has the same effect as performing it once. → [Idempotency & exactly-once](/synapse/system-design-from-first-principles/patterns/idempotency-and-exactly-once)
- **Idempotency key** — a client-supplied unique token attached to a request so the server can detect and dedupe retries of the same operation. → [Idempotency & exactly-once](/synapse/system-design-from-first-principles/patterns/idempotency-and-exactly-once)
- **Long-running task** — work too slow to handle inline, offloaded to a background worker via a queue and tracked asynchronously. → [Long-running tasks](/synapse/system-design-from-first-principles/patterns/long-running-tasks)
- **Outbox pattern** — writing an event to an *"outbox"* table in the same transaction as the domain change, so a relay can publish it reliably without dual-write races. → [Event-driven: CQRS, outbox, CDC](/synapse/system-design-from-first-principles/patterns/event-driven-cqrs-outbox-cdc)
- **Saga** — a multi-step business process spread across services, made atomic-ish by pairing each step with a compensating action for rollback. → [Multi-step processes & sagas](/synapse/system-design-from-first-principles/patterns/multi-step-processes-and-sagas)
- **Scaling reads** — absorbing read load with replicas, caching, and denormalized read models. → [Scaling reads](/synapse/system-design-from-first-principles/patterns/scaling-reads)
- **Scaling writes** — absorbing write load with sharding, batching, and write-optimized storage. → [Scaling writes](/synapse/system-design-from-first-principles/patterns/scaling-writes)

---

## 🏭 Production & operations

- **Autoscaling** — automatically adding or removing capacity in response to load signals to match demand without manual intervention. → [Capacity & autoscaling](/synapse/system-design-from-first-principles/production-engineering/capacity-and-autoscaling)
- **Blast radius** — the scope of damage a single failure can cause; good designs deliberately shrink it. → [Resilience & incidents](/synapse/system-design-from-first-principles/production-engineering/resilience-and-incidents)
- **Blue-green deployment** — running two identical environments and switching traffic from the old (blue) to the new (green) all at once, with instant rollback. → [Deployment strategies](/synapse/system-design-from-first-principles/production-engineering/deployment-strategies)
- **Bulkhead** — isolating resources into compartments so that overload or failure in one cannot sink the whole system. → [Resilience & incidents](/synapse/system-design-from-first-principles/production-engineering/resilience-and-incidents)
- **Canary** — rolling a change out to a small fraction of traffic first, watching metrics, and only then widening the rollout. → [Deployment strategies](/synapse/system-design-from-first-principles/production-engineering/deployment-strategies)
- **Chaos engineering** — deliberately injecting faults into production-like systems to build confidence in their fault tolerance. → [Resilience & incidents](/synapse/system-design-from-first-principles/production-engineering/resilience-and-incidents)
- **Circuit breaker** — a client-side guard that stops sending requests to a failing dependency after a threshold, giving it time to recover. → [Resilience & incidents](/synapse/system-design-from-first-principles/production-engineering/resilience-and-incidents)
- **Error budget** — the allowed amount of unreliability implied by an SLO (100% minus the target), spent on change and risk. → [Observability](/synapse/system-design-from-first-principles/production-engineering/observability)
- **Expand / contract (parallel-change) migration** — evolving a schema or interface in backward-compatible steps — add the new, migrate, then remove the old — so no deploy requires downtime. → [Deployment strategies](/synapse/system-design-from-first-principles/production-engineering/deployment-strategies)
- **JWT (JSON Web Token)** — a signed, self-contained token carrying claims, letting a service verify identity and authorization without a session lookup. → [Authentication & authorization](/synapse/system-design-from-first-principles/production-engineering/authn-authz)
- **Load shedding** — a server proactively rejecting or dropping requests when near overload to protect its ability to serve the rest. → [Resilience & incidents](/synapse/system-design-from-first-principles/production-engineering/resilience-and-incidents)
- **OAuth / OIDC** — OAuth 2.0 delegates authorization via access tokens; OpenID Connect layers authentication (identity) on top of it. → [Authentication & authorization](/synapse/system-design-from-first-principles/production-engineering/authn-authz)
- **Observability** — collecting metrics, logs, and traces so operators can ask arbitrary questions about a running system's behavior. → [Observability](/synapse/system-design-from-first-principles/production-engineering/observability)
- **Rate limiting** — capping how many requests a client may make in a window to protect a service from abuse and overload. → [Rate limiter](/synapse/system-design-from-first-principles/case-studies/rate-limiter)
- **RBAC (role-based access control)** — granting permissions to roles and assigning roles to users, rather than permissions to users directly. → [Authentication & authorization](/synapse/system-design-from-first-principles/production-engineering/authn-authz)
- **Retry storm** — a self-amplifying surge of traffic when many clients time out and retry at once, often tipping an already-struggling service over. → [Resilience & incidents](/synapse/system-design-from-first-principles/production-engineering/resilience-and-incidents)
- **Rolling upgrade** — deploying a new version a few nodes at a time while the rest keep serving, avoiding downtime. → [Deployment strategies](/synapse/system-design-from-first-principles/production-engineering/deployment-strategies)
- **Service discovery** — the mechanism by which a client finds the current network address of the service instance it needs. → [Service discovery & mesh](/synapse/system-design-from-first-principles/production-engineering/service-discovery-and-mesh)
- **Service mesh** — an infrastructure layer (typically sidecar proxies) handling service-to-service networking: discovery, load balancing, retries, mTLS, and telemetry. → [Service discovery & mesh](/synapse/system-design-from-first-principles/production-engineering/service-discovery-and-mesh)
- **Sidecar** — a helper process deployed alongside a service instance that handles cross-cutting concerns (proxying, telemetry) out of the application. → [Service discovery & mesh](/synapse/system-design-from-first-principles/production-engineering/service-discovery-and-mesh)
- **SLI / SLO / SLA** — a service level indicator is a measured metric; an objective is the target for it; an agreement is a contract with consequences if the objective is missed. → [Observability](/synapse/system-design-from-first-principles/production-engineering/observability)

## PoC — Proof of concepts

If a term here is still fuzzy, these define it in more depth (and often with a diagram or a runnable
demo):

- [System Design Primer](https://github.com/donnemartin/system-design-primer) — a broad glossary of
  the same vocabulary, each term tied to where it is used.
- [Jepsen — consistency models](https://jepsen.io/consistency) — the precise, formal definitions for
  the consistency and isolation terms, which are the ones most often used loosely.
- [awesome-system-design-resources](https://github.com/ashishps1/awesome-system-design-resources) —
  a term-by-term index into deeper material when a one-line definition is not enough.

## Sources

Definitions distilled and paraphrased from the DDIA (2nd ed.) chapter digests in this book's author notes and from the book's own lessons; each entry links to the lesson that teaches the concept in full, where the page-cited sources live.

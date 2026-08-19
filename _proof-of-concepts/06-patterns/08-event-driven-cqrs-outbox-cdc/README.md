# POC: Transactional Outbox

A runnable companion to **Event-driven, CQRS, outbox & CDC**
(`05-patterns/08-event-driven-cqrs-outbox-cdc`). It implements the transactional
outbox against a **real Postgres** and proves the three properties that make the
pattern worth its plumbing: atomic write, at-least-once delivery, and
effectively-once processing.

| Piece | File | Role |
| --- | --- | --- |
| `OrderService` | [`domain/services.py`](domain/services.py) | writes order + event in one transaction |
| `OutboxRelay` | [`domain/services.py`](domain/services.py) | polls unsent events, publishes, marks sent |
| `IdempotentConsumer` | [`domain/services.py`](domain/services.py) | dedups on `event_id` |
| `UnitOfWork` port | [`domain/ports.py`](domain/ports.py) | the shared transaction (`orders` + `outbox`) |
| `PostgresUnitOfWork` | [`infra/postgres.py`](infra/postgres.py) | asyncpg adapter; `FOR UPDATE SKIP LOCKED` poll |
| `InMemoryBroker` | [`infra/broker.py`](infra/broker.py) | simulated message bus (append-only log) |

## Run it

```bash
./run            # start Postgres (8451) + run the walkthrough
./run test       # mypy --strict + smoke (all three guarantees)
./run stop       # tear down
```

Uses [`uv`](https://docs.astral.sh/uv/) and Docker. Port block **8451**.

## What the walkthrough proves

1. **Atomic write** — the order row and its `OrderPlaced` event commit in one
   transaction, so there is no window where one exists without the other (the
   dual-write problem the outbox eliminates).
2. **Atomicity on failure** — a rejected order (amount 0) writes *neither* row
   nor event; the relay finds nothing to publish.
3. **At-least-once + effectively-once** — the relay is crashed *after* publishing
   two events but *before* marking them sent. The events are already on the bus,
   so the retry re-publishes them: the broker sees **9** messages (2 duplicates),
   but the idempotent consumer applies **7** unique effects for 7 orders. Duplicate
   delivery, exactly-once effect.

## What is simulated vs. real

The **hard part is real**: the atomic write and the outbox poll run against a
genuine Postgres, using a true Unit of Work (one transaction spanning both
tables) and `SELECT … FOR UPDATE SKIP LOCKED` — exactly how production relays
(and Debezium-style CDC) drain an outbox without two workers grabbing the same
row. The relay crash is *injected* (a raised exception) rather than a real
process kill, but it exercises the real failure path: the transaction rolls back,
the events stay unsent, and the retry re-delivers.

**Simulated:** the message broker and the consumer. A real system publishes to
Kafka/RabbitMQ/SQS on separate machines and consumers run as separate services;
here the broker is an in-process append-only list and the consumer is an
in-process object with a set of seen `event_id`s. That is deliberate — it makes
the duplicate *visible* (you can count the log) and shows the consumer absorbing
it. The delivery semantics (at-least-once from the bus, dedup at the consumer)
are exactly what you implement for real; only the transport and process
boundaries are collapsed into one process.

# POC: Ticketmaster (no double-booking)

A runnable implementation of the **Design Ticketmaster** case study
(`system-design-from-first-principles/06-case-studies/ticketmaster`), focused on
the invariant the whole design exists to protect: **never sell one seat twice**,
even when thousands of buyers stampede the same seat at on-sale.

The three classes here mirror, 1:1, the C4 **code**-level elements inside the
booking service in `06-case-studies/ticketmaster.c4`:

| C4 code element | File | Role |
| --- | --- | --- |
| `SeatHoldService` | [`app/seat_hold_service.py`](app/seat_hold_service.py) | Redis TTL holds — `SET hold:{seat} holder NX PX` |
| `BookingConfirmer` | [`app/booking_confirmer.py`](app/booking_confirmer.py) | the critical section — `SELECT … FOR UPDATE`, re-check, sell, order |
| `PaymentClient` | [`app/payment_client.py`](app/payment_client.py) | stubbed capture, idempotent per checkout key |

Containers: a **FastAPI** booking service, a **Redis** seat-hold store (TTL), and
a **Postgres** orders/seat store (the system of record).

## Run it

```bash
./run            # frees ports 8320–8322, builds, starts, waits healthy
./run test       # end-to-end smoke + the concurrency stampede
./run stop       # tear down
```

Requires Docker (Compose v2). Port block **8320–8322**.

This is a [`uv`](https://docs.astral.sh/uv/) project (`pyproject.toml` +
`uv.lock`). For editor resolution or running outside Docker: `uv sync
--python 3.12` creates a local `.venv`, then e.g. `uv run uvicorn app.main:app`.

- API → http://localhost:8320 (`/docs`)
- Postgres → `localhost:8321` (`ticket`/`ticket`) · Redis → `localhost:8322`

## What to observe

**1. A hold is an admission ticket.** `POST /holds` does `SET … NX PX`: the first
caller wins, a second caller for the same seat gets `409`, and if the winner
crashes the `PX` TTL auto-releases the seat. Holds throttle checkout without
being the correctness guarantee.

**2. The row lock is the real guarantee.** `POST /confirm` runs the critical
section: `SELECT status … FOR UPDATE` row-locks the seat, re-checks it is still
`available`, captures payment, marks it `sold`, writes the order. Concurrent
confirms serialise on the lock — the first commits, the rest block then see
`sold` and get `409`.

**3. Prove it.** `./run test` fires **25 concurrent confirms at one seat** and
asserts exactly **one** wins and exactly **one** order exists
(`double_sold_seats == 0`). It then repeats on an intentionally **unsafe** path
(`"unsafe": true` drops `FOR UPDATE`) to *demonstrate the anomaly the lock
prevents* — without the lock, multiple confirms pass the `available` check and
the seat is sold more than once.

```bash
# watch a double-sell happen without the lock, then never with it:
curl -s -XPOST localhost:8320/reset
python3 tests/concurrency.py            # SAFE: 1 order · UNSAFE: >1 order
curl -s localhost:8320/stats | python3 -m json.tool
```

## Notes & simplifications

- The virtual waiting room, browse/search path, and cache from the container
  view are out of scope here — this POC isolates the booking critical section,
  which is where the design's correctness lives.
- `PaymentClient` is a stub (always authorises) but keeps the idempotency-key
  behaviour so a retried capture never double-charges.
- `RACE_DELAY` widens the read→write window so the unsafe anomaly reproduces
  reliably on a laptop; the safe path holds the lock across that window.

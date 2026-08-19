# POC: Uber (geospatial matching under contention)

A runnable implementation of the **Design Uber** case study
(`06-case-studies/07-uber`), focused on the matching core: find nearby drivers
fast, offer to **exactly one** at a time, and create the trip **exactly once**.

The three classes under [`domain/`](domain/) mirror the C4 code elements 1:1:

| C4 code element | File | Role |
| --- | --- | --- |
| `NearbyDriverQuery` | [`domain/nearby_driver_query.py`](domain/nearby_driver_query.py) | radius query over the geo index, nearest first |
| `DriverLock` | [`domain/driver_lock.py`](domain/driver_lock.py) | `SET NX PX` — one offer per driver at a time |
| `OfferFlow` | [`domain/offer_flow.py`](domain/offer_flow.py) | walk candidates → lock → create trip (exactly once) |

Containers: a **FastAPI** service, **Redis GEO** (driver positions) + Redis locks
(offer window), and **Postgres** (trips; `UNIQUE(request_id)` = exactly-once).

## Run it

```bash
./run            # build + start api (8380) + Redis (8381) + Postgres (8382)
./run test       # mypy --strict + smoke
./run stop
```

## What the smoke proves

- **Exactly-once trip** — matching the same `request_id` twice returns the *same*
  trip and driver (`OfferFlow` checks first; the `UNIQUE(request_id)` constraint
  is the final arbiter).
- **No double-booking under contention** — 8 riders scramble for 5 drivers, all
  fired concurrently: exactly **5 match, each a distinct driver**, and the other
  3 get a clean "no driver available" (409). The per-driver `SET NX` lock
  serialises the offer, so no driver is offered to two riders at once.

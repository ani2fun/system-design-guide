---
title: OfferFlow
kind: Code
technology: Python
---

## 🧩 OfferFlow

**OfferFlow** is the allocation loop written as readable code: get candidates, then walk them one at a time — lock, offer, await accept within the window; on decline or expiry, advance to the next. It composes the other two classes and owns the sequencing they deliberately don't.

**Responsibilities**

- `run(request) → Trip`: pull ranked candidates from `NearbyDriverQuery`, and for each: `DriverLock.acquire` first (an offer without a lock could double-offer a driver), push the offer, wait out the window, and either hand off to trip creation or move on. Lock-acquisition failure just means someone else holds that driver — skip, don't wait.
- Keep **accept idempotent**: a retried accept (flaky driver network, duplicate tap) converges on the same result instead of erroring or duplicating.
- Create the trip **exactly once per request** — the write goes through the Trip service against the Trip DB's per-request unique constraint, so even a zombie flow replaying an assignment matches zero rows.

**The invariant it protects:** every ride request produces at most one trip, and every accepted offer produces exactly one — no matter how many retries, duplicate accepts, or crashed-and-resumed flows occur along the way. The loop's *liveness* (who advances to driver B if this executor dies mid-window?) is the workflow problem the lesson resolves with durable timeouts or durable execution; its *safety* never depends on the executor surviving, because it rests on the DB constraint.

**Where it breaks.** On deadline math: the sub-minute match SLA affords only ~5 sequential silent-driver hops at 10 seconds each — ranking quality, not loop mechanics, decides whether the walk finishes in time. Lands in the forthcoming POC at `06-case-studies/examples/uber/app/offer_flow.py`.

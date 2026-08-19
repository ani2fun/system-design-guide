---
title: Rider
kind: Actor
technology: Human · rider app
---

## 👤 Rider

The **Rider** asks one question — *"get me from here to there"* — and then does something the system must design around: they *wait, watching*. From the tap on *"request"* to a driver assignment, the rider stares at a live status screen, which turns matching into a sub-minute, user-visible SLA rather than a background job. A fare quote precedes everything: the rider says yes to a **priced** trip, not to an open-ended meter.

**Responsibilities**

- Request a fare quote (pickup + destination) and accept it — creating the ride against that `fareId`, never against a client-supplied price.
- Send *nothing* the server can compute or already knows: identity rides in the session, timestamps come from server clocks, and above all the fare is looked up server-side — any price the client supplies is a price the client can edit.
- Watch ride status live over the realtime channel: requested → matched → en route → in ride → completed.

**Where it breaks.** Impatience and retries. A rider who taps *"request"* twice, or whose app retries a timed-out POST, must not spawn two rides — which is why ride creation is idempotent per request downstream. And riders cluster: a stadium emptying puts a hundred thousand of them in one geohash cell at once, the hot-zone burst the queue in front of matching exists to absorb.

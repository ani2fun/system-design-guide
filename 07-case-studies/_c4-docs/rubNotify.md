---
title: Realtime channel
kind: Notification service
technology: WebSocket / push
---

## 🔔 Realtime channel

The **Realtime channel** solves the last mile in both directions: the *offer* must reach a specific driver's phone within a 10-second window, and the *status* must reach a rider who is staring at the screen. Neither party can poll for this — the offer window is too short and the audience too large — so the server must be able to reach out first: push notifications (APN/FCM) for drivers who can't hold open request connections all shift, persistent connections for riders watching a live screen. It's the same last-mile delivery problem WhatsApp solved with persistent connections, met here with the delivery mechanism each client can sustain.

**Responsibilities**

- Deliver ride offers to the one locked driver, fast enough that delivery latency doesn't eat the 10-second offer window.
- Stream status transitions to the waiting rider — requested, matched, driver en route — as the Trip service emits them.
- Carry no decisions: this container is transport. Locks decide who gets the offer; the trip row decides who got the ride.

**Where it breaks.** Delivery is best-effort by nature — a push can arrive late or never, and the design must not depend on it. It doesn't: an undelivered offer simply expires with the driver lock's TTL and the flow walks on to the next candidate; a missed status update is repaired by the next one. Every failure here degrades to waiting, never to inconsistency.

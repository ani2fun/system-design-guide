---
title: Sync channel
kind: Notification service
technology: WebSocket + polling
---

## 🔔 Sync channel

The **Sync channel** carries one message in one direction: *"your file changed — pull the new chunks,"* from the File Service out to a user's *other* devices. It exists because requirement 4 — files sync automatically — needs devices to *learn* about remote changes, and the design refuses to make every device hammer the change feed constantly or hold a socket forever.

**Responsibilities**

- Push change events over a **WebSocket** for **fresh** files — recently edited, where near-real-time sync is what the user actually perceives.
- Fall back to cheap **periodic polling** of `GET /files/changes?since={cursor}` for **stale** files — old, rarely touched, where a sync delay of minutes harms nobody.
- Carry *notifications only*, never file bytes: a woken device pulls changed chunks through the normal presigned download path, with the metadata store as the source of truth both directions converge on.

The hybrid is the point, and SDS argues it explicitly: a pure-WebSocket design pays for millions of mostly idle persistent connections (WhatsApp accepts that cost because instant delivery *is* the product; here it isn't), while pure polling either wastes requests or delivers the fresh-edit case too slowly. Splitting traffic by file freshness buys real-time behavior exactly where users notice and near-zero cost everywhere else.

Delivery here is best-effort by design — a device that misses an event catches up on its next poll or reconnect, because the change feed cursor, not the push, is what guarantees convergence.

**Where it breaks.** On the fresh/stale classifier and on reconnect storms. Misclassify an actively edited file as stale and collaboration feels broken while polling catches up. And like every socket tier, a server death orphans thousands of connections that redial at once — draining is an operational discipline, though here a missed event costs seconds of staleness, not lost data.

---
title: User
kind: Actor
technology: Human · multiple devices
---

## 👤 User

The **User** of this design is really *several machines wearing one identity*: a laptop, a phone, a desktop — each holding a full local copy of the folder, each accepting edits immediately, each possibly **offline for days**. That last property is not an edge case; it is the design's defining input. A device that edits in an airport and reconnects a week later is, in DDIA's taxonomy, a multi-leader replica whose replication lag is measured in hours or days.

**Responsibilities**

- Edit files locally and expect them everywhere — without ever pressing an *"upload"* button; the sync agent watches the filesystem and does the rest.
- Work offline as a first-class mode: reads and writes hit local disk, the UI never blocks on a round trip, and changes queue until connectivity returns.
- Tolerate the one honest consequence of offline leadership: **conflicted copies**. Two devices editing the same file in mutual ignorance is guaranteed by construction, and the resolution surfaces to this actor as a second file to merge, never a silent overwrite.
- Move file bytes directly against blob storage and the CDN over presigned URLs — the user's gigabytes never route through the app tier.

**Where it breaks.** Users defeat every assumption of synchrony: they close laptop lids mid-upload, edit the same file on two offline devices, and carry clocks that can't order anything. The design answers with resumable content-addressed chunks, causal (not wall-clock) conflict detection, and keep-both resolution — engineering around the actor rather than constraining them.

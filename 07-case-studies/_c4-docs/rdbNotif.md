---
title: Upload notifications
kind: Event stream
technology: S3 events
---

## 🌊 Upload notifications

**Upload notifications** are the asynchronous hop that closes the upload loop: when a chunk lands in blob storage, the store fires an event, and the File Service marks that chunk `uploaded` in the manifest. Small as it looks, this container carries the design's **trust boundary**.

**Responsibilities**

- Deliver "chunk `<hash>` landed" events from blob storage to the File Service, so manifest progress is tracked server-side.
- Make blob storage — not the client — the witness of upload completion.

Why this exists at all: the obvious alternative is the client PATCHing the manifest after each successful chunk PUT, and it is precisely the alternative SDS rejects. A client that reports its own upload status can lie — or merely be buggy — and either way the manifest ends up claiming chunks blob storage doesn't hold: corrupt state that surfaces later as a failed download on some other device. With storage-side events, a chunk is `uploaded` exactly when the store says it arrived, and the client is trusted with nothing but bytes. The manifest reflects reality because reality reports directly.

This event stream is also what arms the visibility flip: only when *every* manifest entry is storage-confirmed does the File Service commit the manifest and make the version visible — durability strictly before visibility.

**Where it breaks.** Event delivery is not a transaction. A lost notification leaves a manifest stuck at 9,999/10,000 — the file forever *almost*-visible while its bytes sit durable and complete. The backstop is a reconciliation sweep that re-lists blob storage against `uploading` manifests; measure what the sweep catches, because that's your event-loss rate telling on itself.

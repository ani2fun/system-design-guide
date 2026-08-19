---
title: Media store
kind: Object storage
technology: Object storage
---

## 🪣 Media store

The **Media store** holds attachments as **opaque encrypted blobs** — and its defining architectural property is that the chat servers never touch the bytes. Media rides a different road from messages entirely.

**Responsibilities**

- Issue-side: the client asks the chat server for a presigned upload URL (`getAttachmentTarget`) and uploads the blob **directly** here; the resulting opaque URL travels as ordinary message content.
- Serve downloads to recipients via presigned GETs.
- Expire blobs on a 30-day TTL, matching the Inbox's retention rule.

Why opaque blobs: end-to-end encryption means clients encrypt content such that servers *cannot* read it — and attachments were already structurally there before any crypto, since the message path only ever carried a URL. E2EE just makes formal what the architecture already implied: the server is a store-and-forward system for payloads it has no reason to open. Every mechanism in the design — routing, Inbox, ordering, receipts — consumes only metadata; none of it reads content, which is why this container can hold ciphertext without anything else changing.

Notably absent: a CDN. With at most 100 recipients per attachment, cache hit rates don't justify one — the exact inverse of the URL shortener's 1000:1 read skew, where caching was the whole game.

**Where it grows.** Media dominates the byte budget while messages dominate the operation budget — text messages are tiny and hot, blobs are large and touched a bounded number of times. Keeping the two on separate paths is what lets each tier be sized for its own shape.

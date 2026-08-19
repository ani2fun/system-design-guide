---
title: LinkCreator
kind: Code
technology: Python
---

## 🧩 LinkCreator

**LinkCreator** is the write path in one class: everything `POST /links` does between receiving a long URL and returning a short one.

**Responsibilities**

- Validate the long URL (and the optional custom alias, when offered).
- Take the **next id** from the node's **RangeLease** — a local, in-memory operation on the amortized-lease design, no allocator round trip.
- Turn the id into a code via **Base62Codec** and `INSERT` the `code → long URL` row into the link store, unique index on `code` as belt-and-braces.

The class embodies the lesson's chosen strategy — *uniqueness by construction*. It never hashes, never generates-and-checks, never retries on collision: the id it encodes came from a range no other node holds, so the code is unique before the database ever sees it. The dependency arrows are one-way and the read path (`RedirectHandler`) shares none of them, which is what makes *"no coordination on the read path"* literally true.

**The invariant it protects:** every code it mints comes from the leased range and is used exactly once — so two concurrent creates, on this node or any other, can never produce the same code.

**Where it grows.** At ~1 write/second the class is nowhere near a bottleneck; its natural evolution is a write-time cache fill (populate the redirect cache on create), which closes the replication-lag 404 on brand-new links. Implemented in the forthcoming POC at `06-case-studies/examples/url-shortener/app/link_creator.py`.

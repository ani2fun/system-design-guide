---
title: Origin API
kind: Service
technology: Rust · axum
---

## ⚙️ Origin API

The **Origin API** is stateless by construction — the property every scaling stage leans on. No
sessions, no sticky routing: identity arrives as a JWT verified against the IdP's cached public
keys (local crypto, no network call), so any replica can serve any request and horizontal scaling
is a replica count.

**Responsibilities**

- **Content reads** — serve the derived read model (catalog index, lesson payloads) from the
  git-sync checkout, stamping every response with `contentVersion` (the checkout's HEAD SHA) so
  every cache above keys correctly.
- **Run gateway** — `POST /run`: rate-limit, then execute synchronously in the sandbox inside the
  ~2 s interactive budget. Back-pressure is a `429`, never a queue.
- **Submissions** — `POST /submissions` → `202 {id}`; judge the hidden suite asynchronously in the
  sandbox; advance the row `pending → completed`; answer polls. The hidden suite never leaves this
  process.
- **Grants & account** — the allowlist gate on submit-and-save; account deletion via a
  least-privilege service-account client (one permission, one realm — blast radius by design).

Internally a **modular monolith**: hexagonal bounded contexts (catalog, execution, submission,
identity) whose package seams are the extraction lines if a context's scaling ever measurably
diverges. The designated first extraction is the run path.

---
title: Web app
kind: Web application
technology: Astro SSR · TS islands
---

## 💻 Web app

The reading UI, server-rendered: a lesson's prose arrives as HTML in the response, so reading
works before — and without — any JavaScript. The interactive parts hydrate as **islands**: the
code editor, diagram rendering, the algorithm visualiser and the search palette are separate,
lazy bundles that load only on pages that use them. Per-page eager JavaScript measures in the
tens of KiB and is enforced by a per-page budget in CI.

**Responsibilities**

- Render lessons server-side from the same public content API the edge caches — this tier holds
  no state and no secrets of its own.
- The workbench island: edit a starter, `POST /run` for interactive feedback, `POST /submissions`
  and poll for the verdict (the ~1 s poll loop is the client's half of the async judging
  contract).
- The OIDC dance (authorization code + PKCE) against the identity provider — once per session;
  the resulting token rides API calls and is verified locally at the origin.

**Design notes**

Anonymous readers get the full reading + run experience — sign-in gates only editing persistence
and submissions. The judged verdict, including the one revealed failing case, is rendered from
the server's response; the hidden suite itself never reaches this component.

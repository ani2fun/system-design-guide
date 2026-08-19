---
title: Identity provider
kind: Identity provider
technology: Keycloak
---

## 🪪 Identity provider

OIDC (authorization code + PKCE) — the platform owns **zero passwords** and delegates the entire
credential lifecycle, including federated sign-in (e.g. GitHub).

**The load-bearing property: it is on the login path only**

Per request, the origin verifies the JWT's signature against this provider's public keys, cached
(JWKS). No identity network call ever rides a read, run, or submit — so the IdP is sized for login
bursts (tens/s even at 1M MAU), and an IdP outage degrades *sign-in*, not reading: anonymous
reading is an availability decision disguised as a product decision.

**Operational lessons carried in the design**

- Usernames compare **canonicalized** (lowercase) everywhere — or `Alice` and `alice` silently
  become two identities and surface later as a confusing 403.
- The platform's admin credential against this provider is a service-account client scoped to one
  permission on one realm — least-privilege by *named blast radius*: a stolen credential can
  delete users in one realm, not administer them all.

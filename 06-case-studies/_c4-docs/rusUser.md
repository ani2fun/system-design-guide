---
title: User
kind: Actor
technology: Browser or mobile app
---

## 👤 User

The **User** is anyone on either side of a short link: the person who creates one, and the (far more numerous) people who click one. That asymmetry is the whole system in miniature — a link is created once and clicked forever, which is why the architecture behind this box is built almost entirely for reads.

**Responsibilities**

- Create short links: `POST /links` with a long URL, optionally a custom alias and an expiration date.
- Follow short links: `GET /{code}`, receiving a `302 Found` whose `Location` header the browser follows automatically — the user never sees a page from this system at all.

The user's browser is quietly part of the design. Because the redirect is a `302` (temporary), every click — first or repeat — comes back to the system, which keeps click analytics possible and links revocable. A `301` would invite the browser to cache the redirect itself: free capacity, but repeat clicks would vanish from view permanently.

**Where it grows.** One of these users is eventually a celebrity, and one click becomes hundreds of thousands per second on a single code — viral traffic is overwhelmingly *first* clicks from *distinct* browsers, so browser-side caching can't absorb it. Everything downstream of this actor is shaped by that moment.

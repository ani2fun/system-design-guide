---
title: Base62Codec
kind: Code
technology: Python
---

## 🧩 Base62Codec

**Base62Codec** is the smallest class in the system and the one carrying the product's name: it turns counter ids into *short* URLs.

**Responsibilities**

- `encode(id)`: integer → base62 string over `a–z A–Z 0–9` — the lesson's alphabet choice, picked over base64 because `+` and `/` collide with URL syntax.
- `decode(code)`: the exact inverse, used wherever a code must map back to its id.

The arithmetic is why 62 symbols suffice: six characters give 62⁶ ≈ 56.8 billion codes against a 1-billion-link requirement — `1,000,000,000` encodes as `15ftgG` — and codes only gain a character at each power of 62, so they stay as short as the space allows.

Deliberately, this is a **pure function pair**: no I/O, no state, no clock. That makes it trivially testable (round-trip every boundary value) and means correctness here is a unit test, not an integration concern.

**The invariant it protects:** `encode` and `decode` are a strict bijection — `decode(encode(n)) == n` for every id, and distinct ids never encode to the same code. Uniqueness of codes is exactly uniqueness of ids passed in; the codec can neither create nor destroy it.

**Where it grows.** Sequential inputs make codes enumerable (`15ftgG` implies `15ftgF` exists); deployments that care insert a cheap bijective scramble between counter and codec — the bijection property is what makes that a drop-in. Implemented in the forthcoming POC at `06-case-studies/examples/url-shortener/app/base62_codec.py`.

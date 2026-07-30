---
title: Ad viewer
kind: Actor
technology: Browser · mobile app
---

## 👤 Ad viewer

The **Ad viewer** is whoever clicks the ad — and the system's founding realism is that *"whoever"* includes a double-clicker, a flaky network that retries a lost POST, and a malicious script fabricating clicks for profit. Every one of those produces an HTTP request that looks like a click; only one of them is a billable event. The viewer is therefore not just a traffic source but the origin of the pipeline's hardest requirement: idempotency has to hold **end to end**, from the browser down, because a browser retry happens *above* every framework guarantee in the stack — no amount of Kafka or Flink machinery can see it.

**Responsibilities**

- Carry the **signed impression ID** minted when the ad was shown — the click's identity — back with the click. The unit of idempotency is the *impression*, not the (user, ad) pair: the same user legitimately clicking the same ad shown twice is two billable clicks.
- Reach the advertiser's site only through the tracker's **302 redirect**, so no click escapes counting.
- Retry freely: the design's promise is that a re-sent POST collapses to one count at ingest, not that the viewer behaves.

**Where it breaks.** The adversarial tail — click fraud. An *unsigned* unique ID would let a script mint endless fresh *"impressions,"* each one unique and each one counted; the signature check at ingest closes that hole. Broader fraud detection (bots, click farms) is deliberately out of this design's scope.

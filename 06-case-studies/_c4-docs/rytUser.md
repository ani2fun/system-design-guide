---
title: Creator / Viewer
kind: Actor
technology: Human · any device, any network
---

## 👤 Creator / Viewer

One identity, two wildly asymmetric roles. As **creator**, this actor hands the system its hardest write: a video of up to tens of GBs, uploaded over a residential uplink where the transfer is measured in **hours** — laptop lids close, Wi-Fi roams, phones change towers. As **viewer**, the same actor expects playback to start in under a second and to survive a train tunnel, on whatever codec their device happens to decode and whatever bandwidth their network happens to sustain. At 1M uploads against 100M watches per day, the viewer role outnumbers the creator 100:1 before you even count segments.

**Responsibilities**

- Upload originals in fingerprinted 5–10 MB chunks over presigned PUTs, **directly to the raw store** — video bytes never route through the API tier.
- Crash and re-ask as the normal upload loop: fetch the chunk manifest, skip what storage already confirmed, resume.
- Watch adaptively: the *player* is the smart party — it fetches metadata from the API, manifests and segments from the CDN, and picks a rendition per measured throughput, switching quality at segment boundaries with no server involved in the decision.

**Where it breaks.** This actor defeats every assumption of a stable connection — mid-upload interruption is the expected path, and viewer bandwidth swings by an order of magnitude mid-video. The design answers with resumable chunked ingest on the write side and client-steered adaptive bitrate on the read side, engineering around the actor rather than constraining them.

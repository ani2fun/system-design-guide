---
title: Metrics API
kind: Service
technology: Python · FastAPI
---

## ⚙️ Metrics API

The **Metrics API** is the advertiser's window into the counts: `GET /ads/{adId}/metrics?granularity=minute&from=…&to=…`, answered sub-second. Its speed is inherited, not engineered — it reads rows the pipeline already aggregated, so a week of an ad's traffic is ~10,080 pre-built numbers rather than a 50M-row scan. Notice what the endpoint deliberately *doesn't* offer: arbitrary ad-hoc queries. Constraining the read surface to pre-aggregated shapes is precisely what makes the latency promise keepable — the naive design died on exactly the flexibility this API declines to provide.

**Responsibilities**

- Serve range reads over `(ad_id, minute_bucket) → count` at 1-minute minimum granularity; answer coarser granularities (hour, day) from OLAP roll-up tables rather than widening any streaming window.
- Present the current minute honestly: open windows flush early and provisional, so the freshest number is live-but-incomplete and firms up when the watermark closes the window.
- Merge salted sub-rows where a hot ad was split into `AdId:0…N` — the read side pays salting's bookkeeping tax, either here at query time or in a second-stage aggregation upstream.

**Where it breaks.** The API can only be as correct as the rows beneath it, and those rows are *revisable*: late-click corrections and batch reconciliation both rewrite history. A number an advertiser screenshotted yesterday may legitimately differ today — the design's stance is that a corrected count beats a stable wrong one, and the invoice trusts the reconciled figure, not the dashboard's first draft.

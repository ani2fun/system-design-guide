---
title: L4 load balancer
kind: Load balancer
technology: L4 / TCP
---

## 🛃 L4 load balancer

The **L4 load balancer** is the front door for every persistent connection — and the notable thing about it is what it *doesn't* do. It operates at layer 4, raw TCP pass-through, not layer 7.

**Responsibilities**

- Pick a chat server **once, at connect time**, for each incoming `wss://` connection.
- Then get out of the byte stream's way: the WebSocket, once established, stays pinned to its chat server for the connection's whole life.

Why L4 and not L7: an L7 balancer parses and re-routes individual HTTP requests, which is exactly the wrong shape for a WebSocket — there are no individual requests to route, just one long-lived TCP connection carrying frames in both directions. Terminating and re-balancing mid-stream would sever the very thing the design depends on: a stable server-side endpoint where the recipient's socket can be found. The balancer's job here is placement, not routing.

One consequence worth saying out loud: this balancer does **not** solve message routing. It decides where *connections* live and gives senders no way to reach the server holding the *recipient's* connection — that's rung 1 of the lesson's routing ladder, broken outright, and the reason the pub/sub bus exists.

**Where it breaks.** Correlated reconnection. When a chat server dies (or a deploy drains one), millions of orphaned sockets redial through this tier at once, each paying the expensive path: TLS handshake, subscribe, Inbox drain. The balancer must spread that herd, not amplify it.

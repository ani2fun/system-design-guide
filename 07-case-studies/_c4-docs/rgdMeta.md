---
title: Doc metadata DB
kind: Relational database
technology: PostgreSQL
---

## 🗄️ Doc metadata DB

The **Doc metadata DB** holds everything about a document that is *not* its content: title, owner, sharing/ACLs, and — the load-bearing column — the **snapshot pointer** (`documentVersionId`). Content lives as ops in the log and folds in the snapshot store; this database is the small, relational, strongly-consistent index that says which document exists, who may touch it, and where its current checkpoint is. Ordinary CRUD (`POST /docs` creates the row) — deliberately boring, because the interesting state lives elsewhere.

**Responsibilities**

- Answer the ACL check when an editor joins a session: may this user open, edit, or only read document X?
- Own the `documentVersionId` pointer — the single atomic act that makes compaction safe. A new snapshot is written beside the old one, then this pointer **flips**; readers before the flip fold the old version, readers after fold the new one, and nobody sees a torn state.
- Route the flip through the Document server (the document's single owner) so a pointer swap can never race a live editing session.

Note what it does *not* store: cursors and presence. That data's lifetime is the connection, so it lives in Document-server memory and dies with the socket — a write path for it would be churn at cursor-move frequency for data nobody wants historically.

**Where it grows.** With document *count* — billions of small rows — not with editing activity. Keystrokes never touch this database; only creates, shares, and compaction flips do, which is what keeps PostgreSQL comfortable here.

---
title: Content repository
kind: Source repository
technology: git (GitHub)
---

## 📚 Content repository

Books as Markdown in git — the authoring plane of the whole platform. `git push` **is** the
publish action: no CMS, no pipeline rebuild, no redeploy.

**Why git is the right database for content**

- **One writer, many readers.** The entire multi-writer problem space — conflicts, replication
  protocols, consensus — is absent by construction.
- **Versioning for free.** Every state of the content has a SHA; the running system stamps reads
  with the SHA they were derived from, which is what makes every cache above it correct by key.
- **Review and rollback are git.** A bad push is a revert; authorship, history, and diff tooling
  come along at zero design cost.

The trade-off, named honestly: CMS ergonomics (previews, WYSIWYG, drafts for non-technical
authors) are given up. For a platform whose authors write in Markdown anyway, that's the cheap
side of the trade.

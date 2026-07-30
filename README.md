# System Design from First Principles

The **System Design from First Principles** book for [Synapse](https://synapse.kakde.eu). This repository *is* the book: the
chapters sit at the root, and Synapse mounts it at `/synapse/system-design-from-first-principles`.

## How this repo is read

- **`book.json` is the book's identity** — title, description, tags, and the `slug` that fixes the
  URL. Treat `slug` as immutable once published: every link and media path embeds it.
- **Chapters are directories, lessons are `.md` files.** Ordering comes from the `NN-` prefix
  (`01-first-steps/`), and the prefix is stripped from the URL — `01-first-steps/02-variables.md`
  becomes `/synapse/system-design-from-first-principles/first-steps/variables`. An `index.md` sorts first; anything unnumbered sorts last,
  alphabetically.
- **Where the book sits in the library is Synapse's business, not this repo's.** It is registered
  from the admin panel, which is what places it under the top level of the library.
- Names starting with `_` or `.`, files ending `.editorial.md`, and the `examples/` and `c4/`
  directories are never rendered as lessons. Neither is this README.

## Every lesson needs frontmatter

```yaml
---
title: "Variables & Basic Types"
summary: "One line, shown in the catalog and the page description."
---
```

`essential: false` marks an optional deep-cut. `kind: problem` turns the page into a runnable
workbench, which additionally expects two sidecars beside the lesson, sharing its exact filename
stem: `<stem>.tests.json` (the judged suite; cases marked `"sample": true` are the only ones the
browser sees) and `<stem>.editorial.md` (the spoiler-safe walkthrough).

## Media

Assets live at `_media/system-design-from-first-principles/<lesson-slug>/…` and are referenced app-absolutely:
`![alt](/media/system-design-from-first-principles/<lesson-slug>/diagram.svg)`. Supported: svg, png, webp, jpg, gif, mp4, webm.

## Links

Intra-book links are app-absolute and are **not** rewritten: `/synapse/system-design-from-first-principles/<chapter>/<lesson>`. Relative
`.md` links do not resolve. Only link to lessons that already exist.

## Contributing

Open a pull request. Readers on the content-editor allowlist can also propose prose edits from the
lesson page itself — "Suggest an edit" opens a PR here automatically. Note that the `.tests.json`
and `.editorial.md` sidecars are not editable in-app; those are ordinary pull requests.

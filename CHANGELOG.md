# Changelog

## 0.1.0 — 2026-10-14

Initial release of the `plasmic-skills` plugin.

- `create-plasmic-component` — Figma component → native Plasmic component, with plan gate, run
  record and project cache.
- `fill-plasmic-page` — Figma page frame → content of an existing Plasmic page; per-field
  inventory against registered defaults, gate, Strapi upload via `figma-to-strapi`, read-back
  verification, run record. Verified on a destination page: array props store; `<img src>` needs
  `insertHtml` replace.
- `figma-to-strapi` — Figma frame images → Strapi Media Library folder → `cdn-urls.json`.

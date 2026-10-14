# claude-skills

Claude Code skills for sanservices projects, packaged as a plugin marketplace. One plugin so far:
**`plasmic-skills`** — the Plasmic + Figma + Strapi workflow.

| Skill | What it does | Invoke |
|---|---|---|
| `create-plasmic-component` | Rebuilds a Figma component or component set as a native Plasmic component (base markup, variants, breakpoints), gated by a plan you approve, verified visually, recorded so a re-run updates instead of rebuilding. | `/create-plasmic-component <figma-url> …` |
| `fill-plasmic-page` | Fills content into an existing Plasmic page from a Figma page frame: inventories every field as empty / filled, tells registered defaults from real content, maps copy and images, uploads assets to Strapi, writes through Plasmic's in-browser AI tools, verifies by read-back, records the run. | `/fill-plasmic-page` + Studio page URL (`branch=`, `arena=`) + Figma frame link |
| `figma-to-strapi` | Exports a Figma frame's images into a Strapi Media Library folder and returns `cdn-urls.json` (local file → CDN URL). Used by `fill-plasmic-page`; also useful alone. | `/figma-to-strapi` + Figma link + Media Library folder link |

## Install

```sh
claude plugin marketplace add sanservices/claude-skills
claude plugin install plasmic-skills@sanservices
```

`/skills` should now list the three skills. Update later with `claude plugin update plasmic-skills@sanservices`.

## Prerequisites

- **Chrome DevTools MCP** — `claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest --no-usage-statistics`.
  Its Chrome profile must be signed in to Plasmic Studio (and to the Strapi admin for uploads).
  `fill-plasmic-page` drives Studio through it.
- **Claude in Chrome** (the browser extension) — `create-plasmic-component` drives Studio through
  your own Chrome instead; see its SKILL.md for why.
- **Figma MCP** — the official Figma server (`get_metadata`, `get_design_context`, `get_screenshot`).
- **Strapi admin access** on the instance whose CDN the pages use, for `figma-to-strapi`.
- `python3` (stdlib only), `curl`, `file`; ImageMagick (`magick`) for oversize images; `mkcert` once
  for the local HTTPS server that `figma-to-strapi` uses.
- Plasmic's own `plasmic-designer` skill is the general-purpose Studio editor and is **not** bundled
  here. Install it from the upstream repository:
  https://github.com/plasmicapp/plasmic/tree/master/ai/skills/plasmic-designer (README has the steps).

## Where things land in a project

The skills write run records and a per-project cache into the consuming repository under
`plasmic-docs/projects/<projectId>.md` and `plasmic-docs/generated/`. Those directories are
skill-owned: never hand-edit them. The reference docs that explain the Studio tool API live with the
frontend repo (`plasmic-docs/studio-tooling.md`).

## Contributing

- One directory per skill under `skills/`, with `SKILL.md` (frontmatter `name`, `description`),
  `references/`, `templates/`, `scripts/` as needed. No secrets, no machine paths, no vendored copies
  of upstream skills.
- House rules the skills follow: a missing input is a prompt, not an abort; a plan gate before any
  irreversible step; read back every write instead of trusting `success`; mirror what already
  exists in the target before applying defaults; record every run.
- Bump `version` in `.claude-plugin/plugin.json`, add a `CHANGELOG.md` entry, tag `vX.Y.Z`.
- Test locally before pushing: `claude plugin marketplace add /path/to/claude-skills`, install,
  run `/skills`, then remove the local marketplace.

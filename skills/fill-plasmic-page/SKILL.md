---
name: fill-plasmic-page
description: Fill content into an existing Plasmic Studio page from a Figma design — inventory every section and field, classify each as empty / partial / filled, map Figma copy and imagery onto it, upload static assets to Strapi (CDN URLs), write through Plasmic's in-browser AI tools, verify by read-back, and record a run file so re-runs become diffs. Use when asked to populate, fill, seed or update a Plasmic page's content from Figma, to check which parts of a page are still placeholder, or to refresh a page's copy and images from an updated design.
---

# Fill Plasmic Page

Take a Plasmic **page that already exists** (its sections and components are in place) and fill its
content from a Figma frame: slot text, images, and the props of code components. Content only. Never
create or restructure components, never restyle, never publish, never touch `main` without being told.

The run is judged on three things: nothing is written that the user did not approve at the gate,
every write is proven by reading it back, and the next run can tell what changed since this one.

Plasmic is driven through Chrome DevTools MCP and the Studio tab's `window.PLASMIC_AI_TOOLS` — the
mechanism Plasmic documents at https://docs.plasmic.app/learn/plasmic-mcp/ and ships as the
`plasmic-designer` skill (v1.3.3). There is no separate Plasmic MCP server. Images reach Plasmic as
CDN URLs, never as Studio uploads (project rule: the upload dropzone bypasses CDN optimisation).

## Inputs

Two inputs are required; everything else is derived or asked only when the run proves it is
needed. Ask for a missing required input in one short line and end the turn. A missing input or
unmet precondition is a prompt, never an abort — and never a list of optional things.

- `PLASMIC_PAGE_URL` — a Studio URL containing `/projects/<id>/`, `branch=<name>` and
  `arena=<uuid>`. The arena uuid **is** the page component uuid; no listing call is needed. No
  `branch=` → ask which branch; never assume `main`. `arena_type` must be `page`.
- `FIGMA_LINK` — `figma.com/design/<fileKey>/...?node-id=<a>-<b>` pointing at the **page frame**
  (one artboard, e.g. "Destination - Curacao - Desktop"). Node id `7770-33969` becomes `7770:33969`.
- `STRAPI_FOLDER` — the Media Library folder that receives this page's images, as a path
  (`Destinations/Curacao`) or an admin folder link (`…/admin/plugins/upload?…&folder=NNNN`).
  **Asked only after the Strapi session check passes** (Step 1b): a signed-in admin is the
  precondition, the folder is the question. Never ask the user for image URLs instead.
Derived, never asked: `PROJECT`, `BRANCH`, `PAGE_UUID` from the URL; `TARGET` = the page's path
slug (`/curacao` → `curacao`); `RECORD_PATH` = `plasmic-docs/generated/fill-<TARGET>.md` in the
current repository (skill-owned, never hand-edited; no repo → scratchpad, and say so). A record
that already exists simply makes this a re-run — mention it, do not ask about it.

Asked only when the run finds the need, folded into the gate message:

- `COPY_SOURCE_URL` — a live or staging page URL holding copy the Figma file hides (collapsed
  accordions, truncated lists). Only when Step 4 finds `missing-in-figma` fields.
- `VIDEO_FILES` — local paths for video cells; the Figma MCP cannot export a video fill. Only when
  Step 4 finds a video cell **and** the Strapi search finds no existing upload. Uploaded to the same folder.

## Requirements

- **Chrome DevTools MCP** (`mcp__chrome-devtools__*`): `new_page`, `evaluate_script`,
  `take_snapshot`, `take_screenshot`, `list_pages`. If deferred, load them in one `ToolSearch`
  batch before Step 1. Its Chrome profile must be **signed in to Plasmic and to the Strapi admin**.
  A login page is a prompt: ask the user to sign in in that window, then re-check. This skill deliberately differs from `create-plasmic-component`, which
  drives the user's own Chrome: DevTools MCP's `filePath` output and absence of secret-redaction make
  the 50–150 KB page reads here practical.
- **Figma MCP**: `get_metadata`, `get_design_context`, `get_screenshot`. Load the
  `figma-design-to-code` guidance before the first `get_design_context`, as that tool requires.
- **`figma-to-strapi` skill** for the upload itself (it owns the Strapi endpoints, the local HTTPS
  server, token handling and `cdn-urls.json`). Invoke it; do not re-implement it. The Strapi admin
  origin comes from the repo's environment config for the brand and stage (or the project cache);
  `references/strapi-session.md` has the session check and the folder-path resolution.
- `python3` for `scripts/plasmic_fill.py` (stdlib only; always run with `python3 -I`).
- **The host app** behind the Studio canvas must be reachable: Step 2 reads registered prop schemas
  and defaults from it. Its URL is the `src` of the canvas iframe in the Studio tab.

**The run stops for the user by design at the gate** (Step 6). Say so when you start. The gate is
never skipped and never self-approved; an agent that cannot reach a user returns the gate table as
its result and writes nothing.

## Step 0 — Resolve inputs and mode

Parse `PLASMIC_PAGE_URL` into `PROJECT`, `BRANCH`, `PAGE_UUID`; `TARGET` comes from the page path
after Step 2's read (use the arena uuid until then). If `RECORD_PATH` exists, this is a
**re-run**: load its JSON node map; Step 6 then diffs *figma vs recorded vs current* per field and
proposes updates only where the source changed. Also read `plasmic-docs/projects/<PROJECT>.md` if
present (project cache from the sibling skill: host URL, placeholders learned, routes that worked).

## Step 1 — Session

1. `new_page` the exact `PLASMIC_PAGE_URL` (fresh tab, foreground; a reload often hangs on "host app
   is taking a while"). Note the `pageId`.
2. Run `scripts/bootstrap.js` through `evaluate_script` with `waitForStableDom: false`. It polls
   for `PLASMIC_AI_TOOLS` (≤45 s), asserts the URL **and** `document.title` carry `BRANCH`, calls
   `identify`, and returns `{ ok, branch, title, visibility, hostUrl, tools, schemas }`. Fix the
   `model` / `client` values in the call to what you are.
   - `ok:false, reason:'login'` → ask the user to sign in; re-run.
   - `reason:'hidden'` → ask the user to bring the tab to the front; re-run.
   - `reason:'branch'` → the tab is on another branch; re-navigate, wait, re-run.
   - `reason:'no-tools'` → fresh tab, not a reload.
3. Treat `schemas` (the `inputSchema` of `read`, `changeElement`, `insertHtml`) as authoritative
   over anything written here. Every later call branches on `success`; an `EXECUTION_FAILED` whose
   message is the identify instructions means the page navigated — re-identify.

## Step 1b — Strapi session, then the folder

Run before any question about assets, in parallel with Step 2 (independent tabs):

1. Find the Strapi admin origin (`references/strapi-session.md`: repo env config for the brand and
   stage, else the project cache, else ask once and cache it).
2. `list_pages` for an open `<origin>/admin` tab; otherwise `new_page` it in the background.
3. `evaluate_script` the session check from the reference: it calls `GET /admin/users/me` with the
   stored admin token and returns `{ signedIn, user, origin }`.
   - `signedIn:false` → **prompt**: "Sign in to Strapi at `<origin>/admin` in the DevTools Chrome
     window, then say go." End the turn. Re-run the check on resume; never ask for URLs instead.
   - `signedIn:true` → ask for `STRAPI_FOLDER` (path or link) if the request did not name it; fold
     that question into the same message as any other missing input.
4. Resolve the folder path to an id by walking `GET /upload/folders` from the root; a missing leaf
   is created only after the gate (it is listed there as "will create folder …").

## Step 2 — Read the page and the registry

Two reads, both saved to files; never return a whole tree inline.

1. Page tree: `evaluate_script` with `filePath: <scratch>/tree.json`:
   ```js
   async () => await window.PLASMIC_AI_TOOLS.read({ components: ["<PAGE_UUID>"] })
   ```
   If the call nears the ~45 s CDP limit on a very large page, use the start-and-poll pair in
   `references/studio-session.md`.
2. Registry: `new_page` the `hostUrl` from Step 1 in the background, then `evaluate_script` with
   `filePath: <scratch>/registry.json` using the snippet in `references/content-model.md`
   (strips functions, keeps `name`, `props` with `type`, `defaultValue`, `itemType`, `fields`,
   `options`, `advanced`). Empty registry after 20 s → the host is down or on another build; prompt.

## Step 3 — Inventory

```sh
python3 -I scripts/plasmic_fill.py parse tree.json --registry registry.json \
  -o inventory.json --md inventory.md
```

`inventory.md` is the page as a list of **field ids** — one line per writable thing, with its kind,
status and current value. Read it whole; it is the vocabulary for everything after. Field ids are
`<tplUuid>/text`, `<tplUuid>/attr.src`, `<tplUuid>/props.<name>`. Status per field:

| status | meaning |
|---|---|
| `empty` | kit placeholder copy or image, or a code-component prop that is unset / equals its registered default (the canvas renders defaults, so it *looks* filled) |
| `filled` | real content |
| `optional-empty` | an instance prop left blank on purpose (e.g. a marker's link); not counted |
| section `unfillable` | a `PLACEHOLDER`-labelled element with no component behind it — report, never guess |

The parser is `references/tree-format.md`; the placeholder vocabulary is
`references/placeholders.json` (extend it when a project uses other stand-in copy — that is a
project-cache note too).

## Step 4 — Figma inventory

1. `get_metadata` on the page frame → top-level section frames. Skip `hidden="true"` frames,
   sticky/menu/footer chrome (not authored in Plasmic), and anything the project cache says is
   app layout.
2. `get_design_context` with `excludeScreenshot: true` on every remaining section frame — all calls
   in one message, they are independent. On a frame that returns metadata only (too large), call
   its child instances instead.
3. Write `<scratch>/figma-content.json` yourself, in the shape `references/figma-extraction.md`
   describes: per section, the instance name, node id, ordered texts, repeated items (cards,
   slides, questions), image assets (node id + temporary URL + role), and **what is hidden**.
   Hidden layers never come back from `get_design_context`; a collapsed FAQ answer or a tab's
   inactive panel is simply absent. Mark those fields `missing-in-figma`.
4. An image cell with no asset is a suspected video (`references/figma-extraction.md`): confirm with
   `get_screenshot`, search Strapi for an existing video. `missing-in-figma` fields and unresolved video cells are **gate questions**, not blockers: carry on through
   Steps 5–6 and ask for `COPY_SOURCE_URL` / `VIDEO_FILES` in the gate message, next to the rows
   that need them. With a URL: fetch it, match by the visible text (question → answer), and cite
   `copy-source` as the field's source.

## Step 5 — Download assets (local, before the gate)

For every image role that maps to an `empty` image field, download now — it is side-effect free,
surfaces oversize files and expiry at the gate, and the Figma URLs die after 7 days:
`curl -L` into `<scratch>/assets/<section>/<TARGET>-<section>-<nn>`, fix the extension from
`file --mime-type`, note size. Videos: only from `VIDEO_FILES`; a video cell without a source is a
gate row. Record Figma **node ids** as the asset keys, never the URLs.

## Step 6 — Map, plan, gate

Write `<scratch>/fill.json` — the mapping is yours to make, the script's job is to refuse what cannot
work. Shape (full example in `templates/fill.example.json`):

```json
{
  "sections": { "<section tplUuid>": { "name": "Resort FAQs", "node": "7770:34016" } },
  "writes": [
    { "field": "<tplUuid>/text", "value": "Curaçao FAQs", "source": "figma:I7770:34016;1026:14784" },
    { "field": "<tplUuid>/props.faqs", "value": [ { "question": "…", "answer": "…" } ], "source": "figma+copy-source" },
    { "field": "<tplUuid>/attr.src", "value": "{{asset:7770:33996:image}}", "source": "figma:7770:33996" }
  ],
  "assets": { "7770:33996:image": "assets/experiences/curacao-experiences-01.png" }
}
```

Rules that `references/mapping-rules.md` spells out: match sections by **component type sequence**
(FaqListing ↔ "Resort FAQs", ContentCardA ↔ "Content Card A …", …), then by order inside the
section; a kit text slot takes the Figma text verbatim (NFC, single spaces, no trailing period
added); a code-component array prop is written **whole** (the registry's `itemType.fields` are the
only legal keys); an image field takes `{{asset:<key>}}`, never a Figma URL; a count mismatch
(Figma 6 cards, Plasmic 3 slides) on **slot lists** is a gate question, on array props it is just
the array length.

Then:

```sh
python3 -I scripts/plasmic_fill.py plan inventory.json fill.json --registry registry.json \
  [--record record.json] -o plan.json --md gate.md
```

The script rejects unknown field ids, unknown prop keys (Plasmic accepts them silently and stores
nothing), wrong value types, choice values outside the options, and Figma URLs in `src`. It decides
per field: `write` (empty, or re-run source change), `skip` (already matches), `ask`
(`filled-differs`: real content that differs from Figma, or a Studio edit since the last run). It
records the **before** value of every write — that is the rollback.

**Post `gate.md` as the message and end the turn.** One row per section: status, Figma source,
writes (text/props/images), assets, issues, action. The user answers in row edits (`3: skip`,
`5: overwrite`, `7: use live URL`). Apply them to `fill.json` (`"overwrite": true` on a write turns
`ask` into `write`), re-plan, and continue only when the re-planned gate has no `ask` rows left or
the user said to proceed with them skipped. Record the approved gate text verbatim for the record.

## Step 7 — Upload assets

Invoke `figma-to-strapi` with `FIGMA_LINK`, the resolved folder link (`<origin>/admin/plugins/
upload?folder=<id>`), `SET_NAME = TARGET` and `OUTPUT_DIR = <scratch>/assets`, so it reuses Step 5's
downloads and `VIDEO_FILES`; its loop skips files already in the folder, so a re-run never
duplicates. Its `cdn-urls.json` is the map. A 401 mid-run is a rotated or expired session: re-run
the Step 1b check, prompt if needed, resume — the loop is restartable. Then:

```sh
python3 -I scripts/plasmic_fill.py payload plan.json --cdn cdn-urls.json -o writes.json
```

It substitutes every `{{asset:…}}` and exits non-zero naming any key still unresolved — those
fields stay unwritten and go to the gaps list; everything else proceeds.

## Step 8 — Write

If more than ~10 minutes passed since Step 2 (a designer may have touched the page), re-read the
tree and re-run `parse` + `plan`; field ids that vanished are reported, not retried blindly.

`writes.json` holds, per section, one `changeElement` call — text slots as `{ tplUuid, text }`,
code-component and instance props as `{ tplUuid, props: { name: value } }` with arrays and objects
passed as JSON values — plus one `insertHtml … insertRelLoc: "replace"` call per image (`src` is a
reserved attribute that `changeElement.props` silently ignores; the replacement `<img>` carries the
read's `style`, `loading`, the new `src` and an `alt`). Run each through `evaluate_script`:

```js
async () => await window.PLASMIC_AI_TOOLS.<tool>(<input object pasted verbatim>)
```

Per call: `success:false` → read the message; a uuid error means re-read and remap by label +
component + ordinal, retry once. Read `output.messages` too — "ignored reserved attrs" or "Dropped
styles" there is a partial failure behind `success:true` — and inspect `results` for
`InvalidResource` rows. Section-sized batches keep failures isolated and undo meaningful. A replaced
image gets a **new tpl uuid**; Step 9 finds it by path and the record stores the new one.

Multi-paragraph body copy: write it with `\n` between paragraphs first; if the read-back collapses
it, the field needs rich text — `insertHtml` replace with `<p>` children — and the record says so.

## Step 9 — Verify

Re-read the tree to `tree-after.json` (same call as Step 2), then:

```sh
python3 -I scripts/plasmic_fill.py diff plan.json tree-after.json --cdn cdn-urls.json \
  --registry registry.json -o verify.json --md verify.md
```

Every planned field is compared to what Studio actually stores (whitespace-normalised text,
deep-equal props, exact `src`). **`success:true` is not verification; this is.** Then one
`take_snapshot` of the Studio tab and confirm three sentinels: a written heading is present, one
registered default that was replaced is gone ("What is included in my stay?"), one kit placeholder
that was replaced is gone ("Enter some text"). The snapshot sees inside the canvas iframe; a stale
canvas is a reason to screenshot after a fresh `navigate({ componentUuid })`, not to trust `success`.

At most three correction rounds (fix `fill.json` or the route, re-plan, re-write the failed fields
only). Then report what still differs.

## Step 10 — Record and report

```sh
python3 -I scripts/plasmic_fill.py record plan.json --verify verify.json --cdn cdn-urls.json \
  --meta meta.json -o <RECORD_PATH> --json record.json
```

`meta.json` carries the inputs, dates and the approved gate text (`templates/run-record.md` shows
the result). The record's JSON block maps every written field to its tpl uuid, the value written,
its hash, the value before, and the asset keys → CDN URLs. **Write it even when the run stopped
early** — after the gate, after a rejected plan, after three failed rounds.

Update `plasmic-docs/projects/<PROJECT>.md` with anything learned about the project (host URL,
image route, placeholders, a convention). Close the tabs you opened.

Chat report, short: fields written / verified, sections skipped as filled, unfillable sections and
missing-in-figma fields, assets uploaded, anything that needs a human in Studio, and the cost line
(wall-clock, tool calls, gate round-trips).

## Notes

- Each prompt to the user ends the turn; finish everything that does not depend on the answer first
  (Step 5 downloads, the inventory) and resume from the files in the scratchpad. A Strapi login
  prompt is the usual one; the Plasmic tab and all local files survive it.
- One tool call ≈ one Studio undo entry; section batches are what makes ⌘Z useful.
- `read` cannot see slot *defaults*, screen-variant overrides or dynamic `style` attributes; none of
  those are content, so this skill never needs to.
- Never write to a branch whose name warns you off (`…-DO-NOT-EDIT`), never to `main` unless the
  user named it, never publish, never create tokens or components. Structure problems (a section
  missing, a placeholder div where a component should be) are reported for `create-plasmic-component`
  or a human — not patched here.
- `references/failure-modes.md` is the full table of what fails silently and how each case is caught.

# Getting content out of the Figma page frame

## Calls

| Call | Use | Notes |
|---|---|---|
| `get_metadata(fileKey, nodeId)` | the page frame's section list | returns ids, names, geometry, `hidden="true"`; no text |
| `get_design_context(fileKey, nodeId, excludeScreenshot: true)` | text + assets per section | React/Tailwind reference code; read it for `data-name`, `data-node-id`, text nodes and `const img… = \`${assetPathPrefix}/…\`` lines. Returns metadata only when the node is too big — call its children then |
| `get_screenshot` | a visual check of one section | plain `123:456` ids only; nested `I…;…` ids are rejected |

`fileKey` is the segment after `/design/`; `node-id=7770-33969` → `7770:33969`. Nested instance ids
(`I7770:34016;1338:20742`) work with `get_metadata` and `get_design_context`.

`get_design_context` may stop with a Code Connect prompt ("components are missing code connect
mappings"). Answer it with `disableCodeConnect: false` on the retry — Code Connect is not used here.

## What a destination page frame looks like

Top-level frames are `Content Block N`, each wrapping one or two **instances** whose names say what
they are: `Collage Hero`, `Sub Menu`, `Copy Main Intro`, `Resort Card Instances`, `Map Destination`,
`Destination Intro Slider`, `Content Card A Color List` (×N cards), `Collage`, `Content Card B2`,
`Flight Itinerary`, `Resort FAQs`, `Closer`, `Quick Quote Bar…`, `Footer`. Frames named `sticky`,
`footer`, and menus are app chrome — not authored in Plasmic. `hidden="true"` frames are design
leftovers; skip them.

## Hidden content

`get_design_context` **omits hidden layers entirely** — not as empty, as absent. Known cases:

- Accordion answers (`Resort FAQs` → each `FAQ Listing` has `copy auto layout` hidden): only the
  questions come back.
- Inactive tab panels, "show more" lists, alternate states.

`get_metadata` on the item shows the hidden node, so the skill can *prove* content is missing. Such
fields are `missing-in-figma`; their copy comes from `COPY_SOURCE_URL` (fetch the page, match
question → answer by text) or from the user, never invented.

### Reading a copy source

`curl -sL -A "Mozilla/5.0" <url>` and look, in this order:

1. **JSON-LD** (`<script type="application/ld+json">`): an `FAQPage` object carries every question
   and answer verbatim; find `"@type":"FAQPage"` and take the balanced `{…}` around it (it is often
   nested inside a `@graph` array, so a per-script `json.loads` is not enough).
2. The framework's data blob (Next.js `self.__next_f.push` strings) — flight tables, card copy and
   other structured content live there as escaped JSON.
3. Rendered HTML as the last resort.

Match live items to Figma items by **normalised question text** (NFC, lowercase, punctuation
stripped), then by word-set overlap when the wording drifted ("Sandals Curaçao" vs "Sandals Royal
Curaçao", "U.S" vs "U.S."). Keep the **Figma** wording for the visible text and the live answer for
the hidden part; say in the gate which items were fuzzy-matched. Strip HTML from answers unless the
target prop says HTML is allowed.

## Assets

- Image URLs are `https://www.figma.com/api/mcp/asset/<id>/<hash>.<ext>` and expire in ~7 days.
  Download in the same step; key every asset by the **Figma node id** of the layer that uses it,
  with a role suffix when a layer has several (`7770:33996:image`, `7770:33996:icon`).
- `curl -L -o <file>`, then `file --mime-type` to fix the extension; convert anything over ~20 MB
  (`magick in.png -quality 90 out.jpg`) because Strapi rejects it.
- A repeated asset is downloaded once and referenced by every field that uses it.
- Vector icons that are part of a component's design (chevrons, plus signs) are **not** content;
  only images that fill an image field or an `imageUrl` prop are.
- **Video cells look empty.** A layer with a video fill comes back from `get_design_context` as an
  empty `<div>` with no asset, and `download_assets` returns image fills only (`export_video` renders
  a frame's prototype timeline, not a fill). An image-role layer (`data-name="Image"`, a collage or
  card cell) with no `<img>` is therefore a **suspected video**, never "empty": `get_screenshot` the
  parent to confirm (a play glyph or a frame that is not a flat fill), then search the Strapi Media
  Library for an existing video (`mime $contains video`, name match on the layer's file name or the
  destination) before asking for `VIDEO_FILES`. Only a confirmed empty cell is a "leave empty" row.
  Write a found video as the project's video component (`hostlessHtmlVideo`, `autoPlay`, `muted`,
  `loop`, `playsInline`, `src`) replacing the cell's `<img>`.

## `figma-content.json` (written by you, consumed by you)

```json
{
  "page": { "fileKey": "ckBNMXfJepTYQp6vYYAFOk", "node": "7770:33969", "name": "Destination - Curacao - Desktop" },
  "sections": [
    {
      "node": "7770:34015", "name": "Content Block 6", "instance": "Resort FAQs",
      "texts": { "title": "Curaçao FAQs" },
      "items": [ { "node": "I7770:34016;1338:20742", "question": "Does Curaçao have all-inclusive resorts?", "answer": null } ],
      "assets": [],
      "missing": [ "items[*].answer (hidden layer 'copy auto layout')" ]
    },
    {
      "node": "7770:33992", "name": "Content Block 10", "instance": "Content Card A Color List",
      "texts": { "intro.heading": "…", "intro.tag": "…" },
      "items": [ { "node": "7770:33996", "title": "Convertible MINI Cooper", "body": "…", "pill": "In select rooms", "link": "View Qualifying Rooms", "image": "7770:33996:image" } ],
      "assets": [ { "key": "7770:33996:image", "url": "https://www.figma.com/api/mcp/asset/…/3f910.png", "file": "assets/experiences/curacao-experiences-01.png" } ]
    }
  ]
}
```

The shape inside `texts` / `items` is free; what matters is that every value you later put in
`fill.json` can be traced to a node id here (`source`).

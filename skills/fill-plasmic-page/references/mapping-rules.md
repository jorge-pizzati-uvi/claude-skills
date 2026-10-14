# Mapping Figma content onto Plasmic fields

The script validates; the mapping is a judgment you make and show at the gate. These rules keep it
predictable.

## Sections

1. Match by **component type**, not by frame name. Figma frame names ("Content Block 10") carry
   no signal; the instance names inside them do:

   | Figma instance | Plasmic component(s) |
   |---|---|
   | Collage Hero | hero slider / collage hero — often still a `PLACEHOLDER` div → unfillable |
   | Sub Menu | `submenusDefault` (slot `title`, `links` → `formsComponentsDropdownLink` children) |
   | Copy Main Intro | `copyMainIntro` (`heading`, `tag`, `body`) — one per section, matched by order |
   | Resort Card Instances | `slidersResortSlider` (data-driven by `resortCodes`; no copy to fill) |
   | Map Destination | `tabsDestinationMapTabs` + marker tooltips (usually already filled) |
   | Destination Intro Slider | `slidersDestinationSlider` (title slots + slide instances) |
   | Content Card A Color List (×N) | `contentCardA` → `items[]` (one entry per Figma card, in canvas order) |
   | Collage | `collage` → `items[]` (cell order follows the registered layout) |
   | Content Card B2 | `cardContentB2` (slots `children` img, `title`, `tag`, `body`, `bulletTitle`, `link/label`) |
   | Flight Itinerary | `flightsItinerary` → `title`, `country`, `destinations[]` |
   | Resort FAQs | `faqListing` → `title`, `faqs[]` |
   | Closer / Closer Link / Quick Quote | `quickquote` and closer copy — configured, usually ignored |

2. When a type occurs more than once (two `copyMainIntro`, two `slidersDestinationSlider`), pair
   them in **document order** within the matched sections. A leftover on either side is a gate
   issue (`unmapped` field, or Figma content with no home), not a guess.
3. A section whose Plasmic status is `filled` and whose copy matches Figma → nothing to do; say so
   in the gate row. `filled-differs` → `ask`, with before → after shown.

## Fields

- **Text slots**: Figma text verbatim; NFC-normalise; collapse runs of whitespace; keep Figma's
  casing and punctuation (do not add a trailing period, do not title-case). Soft line breaks in a
  single Figma text node → a space. Paragraph breaks (separate text nodes in one body) → `\n`.
- **Tags / eyebrows** (`tag` slots): the small line under or above a heading in Figma.
- **Links**: label from Figma; `href` only when Figma or the brief gives a destination. A link
  without a destination is written with its label only and listed in the gaps.
- **Images**: `{{asset:<key>}}` placeholder; `alt` from the Figma layer name or the card title,
  humanised. Never a Figma URL.
- **Array props** (`items`, `faqs`, `destinations`): build the whole array; one entry per Figma
  repetition; keys exactly as the registry's `itemType.fields`; omit a key rather than write `""`
  when the design has nothing for it (an empty `pillCopy` hides the pill, a `""` disclaimer still
  hides — but keep it clean). Colours only when the design clearly uses a non-default (hex).
- **Counts**: array props take the design's count. Slot lists (slides) with fewer instances than
  the design → an `inserts` entry in `fill.json`, gated; more instances than the design → report,
  do not delete.
- **Hidden in Figma** (`missing-in-figma`): from `COPY_SOURCE_URL` with `source: "copy-source"`,
  or left out and listed. Never paraphrase or invent.
- **Overwrite** only with `"overwrite": true` on that write, and only after the gate said so.

## `fill.json`

```json
{
  "sections": { "<section tplUuid>": { "name": "<Figma instance>", "node": "<Figma node id>" } },
  "writes": [ { "field": "<field id>", "value": <string|array|object>, "source": "figma:<node>|copy-source|user", "overwrite": false } ],
  "inserts": [ { "section": "<section tplUuid>", "target": "<slot-holder tplUuid>", "insertRelLoc": "append",
                 "component": "slidersDestinationSlide", "count": 3, "html": "<plasmic-component …>…</plasmic-component>", "source": "figma:<node>" } ],
  "assets": { "<key>": "<local file>" },
  "notes": [ "anything the gate should say that is not a row" ]
}
```

`templates/fill.example.json` is a filled example for a destination page.

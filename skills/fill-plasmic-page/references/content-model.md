# Where content lives on a Plasmic page, and how to tell "empty"

Pages are a stack of kit layout instances (`layoutSection` → `layoutContainer`) whose `children`
slots hold content instances. Content takes two forms and each has its own write recipe.

## 1. Kit native components — content in slots

`copyMainIntro { heading, tag, body }`, `cardContentB2 { children(img), title, tag, body,
bulletTitle, link → ctAsLink { label } }`, `submenusDefault { title, links → dropdownLink {
children } }`, `slidersDestinationSlider { children → slides }`, `tabsDestinationMapTabs { tabs,
map }`, marker tooltips (props). The slot fill is a text element (`<div>` / `<span>`) or an `<img>`.

- Text → `changeElement` on the **text element's** uuid with `text`. Verbatim copy, NFC, single
  spaces. Plasmic keeps `\n`; whether it renders as paragraphs depends on the slot's text style —
  read back and look.
- Image → **`insertHtml` with `insertRelLoc: "replace"`** on the `<img>` uuid, re-emitting the
  element with the new `src` plus the `style`, `loading` and `alt` copied from the read (`payload`
  builds this). `changeElement.props` does set `alt` on a tag but **ignores `src` as a reserved
  attribute** (the call still says "attrs changed successfully" — verified 2026-10). The replacement
  gets a **new tpl uuid**; verification finds it again by section + path, and the record stores the
  new uuid.
- Instance props on a kit instance (marker `title`, `body`, `image`, `linkLabel`, `linkHref`) →
  `changeElement` with `props`. Blank strings there are usually deliberate (`optional-empty`).

**Kit placeholder copy** marks an empty slot: `Title`, `TAG`, `Tag`, `Link`, `Enter some text`,
`Heading`, `Body`, and the kit's documentation image `Component_Documentation_Image_*.jpg`. The
list is `placeholders.json`; add a project's own stand-ins there when you meet them. A slot holding
real copy that differs from Figma is `filled-differs` → a gate question, never an overwrite.

## 2. Code components — content in props

Host-registered React components (`FaqListing`, `FlightsItinerary`, `ContentCardA`, `Collage`,
`FilterListing`, …). Studio names them lowerCamel in the tree (`faqListing`). Their content is
**props**, often arrays of objects.

- The registered schema (`type`, `itemType.fields`, `options`, `defaultValue`, `advanced`) comes from
  the host page: open the canvas host URL (the iframe `src` in the Studio tab, without the `#…`)
  and run, with `filePath`:

  ```js
  () => {
    const strip = (v, d) => {
      if (d > 8 || typeof v === 'function') return undefined;
      if (Array.isArray(v)) return v.map(x => strip(x, d + 1));
      if (v && typeof v === 'object') { const o = {}; for (const [k, x] of Object.entries(v)) { if (typeof x === 'function') continue; const s = strip(x, d + 1); if (s !== undefined) o[k] = s; } return o; }
      return v;
    };
    return (window.__PlasmicComponentRegistry || []).map(r => ({ name: r.meta.name, displayName: r.meta.displayName, props: strip(r.meta.props, 0) }));
  }
  ```

  The registry is empty in the Studio top window (registrations live in the host iframe). Poll a
  few seconds on the host page before concluding it is down.
- **Empty** = the prop key is absent from `data-props`, or its value deep-equals `defaultValue`.
  The canvas shows the default either way ("What is included in my stay?", "Lorem ipsum…",
  "Montego Bay"), which is why a screenshot cannot judge completeness.
- Write the whole array in one `changeElement` `props` entry. Keys must be exactly the
  `itemType.fields` names — Plasmic accepts unknown keys silently and stores nothing useful;
  `plasmic_fill.py plan` rejects them before the call. `choice` fields must use the option
  `value`. `imageUrl` fields take CDN URLs. Colours (`disableTokens`) take hex.
- Props typed `choice`, `boolean`, `number`, `color`, or marked `advanced` are configuration;
  the inventory leaves them out unless the brief names them.
- Some code components are **configured, not filled** (booking widgets): `placeholders.json →
  ignoreComponents` keeps them out of the inventory.

## 3. Things that look like content but are structure

- A `label="… PLACEHOLDER"` element with no component → the section was never built. Report it
  for `create-plasmic-component` or a human; do not insert raw HTML in its place.
- A slot list with fewer instances than the design (a slider with no slides) → adding instances is
  a structure change. It can be done (`insertHtml` of `<plasmic-component …>` with the slot fills,
  copying an existing sibling's markup), but only as an approved gate row, and the inserted copy
  comes from the same source rules as any other field.

## Silent writes relevant to content (observed on this Studio build)

| Write | Result |
|---|---|
| unknown prop key on an instance | `success`, nothing stored |
| `text` on a non-text element | error — target the leaf |
| a static colour on an instance | rejected — leave colours alone |
| dynamic value on a variant-group prop | stored but invisible to `read` — not a content case |
| `src` through `props` on `<img>` | "attrs changed successfully" + "ignored reserved attrs: src" — nothing stored; use `insertHtml` replace |
| `alt` through `props` on `<img>` | stored; `unsetProps: ["alt"]` removes it |
| `text` on a slot's text `<div>` | stored, reads back exactly |
| array prop on a code component | stored whole, reads back deep-equal (FaqListing `faqs`, 10 items) |

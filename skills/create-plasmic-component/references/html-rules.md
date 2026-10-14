# The HTML Plasmic accepts, and what it rewrites on the way in

`createComponent({ html })` and `insertHtml` share one importer. It is lenient — it repairs malformed
JSON, rewrites unknown tags, drops what it does not recognise — and almost none of that is reported.
Write to the subset.

## Shape

- **Exactly one root element** for `createComponent`. Make it a stack.
- Styling goes in a `<style>` block using BEM-ish class names. **No inline `style` attributes**: an
  inline value lands outside the style system where the right panel cannot comfortably edit it.
- **Flex only in the HTML you insert.** CSS Grid properties are ignored or produce layout errors on
  this path. Set `flex-direction`, `justify-content` and `align-items` on every flex container, and
  build tile layouts as a wrapping flex row with sized children. Studio's own Grid element is a
  different thing — a designer can insert one later, and grid *child* placement does apply to an
  element already inside one; you simply cannot author the grid itself through inserted HTML.
- **Be explicit.** Plasmic does not assume browser defaults; style every element you care about.
- **Emit every repeated item in full.** The importer takes HTML literally, so a `<!-- repeat ×6 -->`
  comment produces one item.

## Components, slots and props

```html
<plasmic-component
  data-plasmic-component="ComponentName"
  data-plasmic-project="importedProjectId"
  data-plasmic-name="Primary CTA"
  data-props='{"propName":"value","variantGroup":"optionName"}'
  style="margin: 16px">
  <slot name="slotName">Slot content here</slot>
</plasmic-component>
```

The `style` attribute on the instance above is the **one sanctioned inline style**: only layout and
position properties apply to an instance at all (see below), so they go inline there. Everything else
belongs in the `<style>` block as classes.

- `data-plasmic-component` is matched after normalisation, but treat it as exact — copy the name from
  a `read`.
- `data-plasmic-project` scopes the lookup to that one direct dependency; transitive deps are not
  searched. Omit it for the current project.
- `data-props` is one JSON object for props **and** variant activations: boolean/standalone group →
  `true`, single-choice → the option name, multi-choice → an array. Slot content never goes here.
- `<slot name="…">` fills a slot on an instance. `<slot-target name="…">default</slot-target>`
  **defines** a slot in the component being built; its children are the default content. Slots cannot
  nest.
- Unknown prop names, unknown slot names and wrong types throw with a clear message — that is the
  one place the importer is strict, and it is worth reading the error rather than guessing.

## Styles on a component instance

Only layout-ish properties apply to an instance of a plain Plasmic component: position, top/left/
bottom/right, z-index, order, margin, width/height and min/max, align-self, flex-grow/shrink, grid
child placement, opacity, `display:none`, and transform properties. Transition properties *apply* to
an instance but do not survive insertion — see below, and `references/studio-session.md`. Background,
padding, colour, font and border on an instance are ignored — style the component's own root instead.
(Code-component instances are the exception: they accept everything.)

## Dropped or rewritten without warning

- **All `transition*` properties** are dropped on import (the full rules, including what
  `changeElement` can and cannot patch afterwards, are in `references/studio-session.md`). Those, and
  the other ignored styles
  (`white-space`, `text-decoration`, `outline`, `pointer-events`, `list-style`, `vertical-align`,
  `box-sizing`, `content`, vendor-prefixed properties) are **dropped on import**. Patch transitions
  afterwards with `changeElement`, and create the first one in the Studio UI.
- `<script>`, `<style>` outside the block the importer consumes, `<head>`, `<noscript>`, `<source>`,
  `<iframe>` and **`<br>`** are dropped.
- Any tag that is not a known container or `img` is **rewritten to `div`**; an empty container is
  dropped entirely.
- `<p>`, `<h1>`–`<h6>` and `<span>` become text nodes when they carry no layout styles; if the text
  is empty the node disappears.
- `inline-flex` → `flex`; `!important` stripped; `transparent` → `rgba(0, 0, 0, 0)`;
  `env(a, b)` → `b`.
- `%` positions on component instances are dropped, and `position:absolute` on `<img>` is flattened.
- Anything outside the recognised style set survives only as an unparsed `style` attribute rather
  than a real style value — it renders, but the right panel cannot edit it. (That is something the
  importer does *to* you, not the sanctioned inline style described above.) One more reason to stay
  in the subset.

## Media queries

A `@media` rule is matched to an **existing project breakpoint by exact numeric equality** —
`max-width` under a desktop-first project, `min-width` under mobile-first. A rule with neither, or
with a width that does not equal a breakpoint, is **discarded with no error**. Read
`screenBreakpoints` first and use those exact integers.

Breakpoints are cumulative, so write overrides as a cascade rather than as bands.

## Pseudo-classes

`:hover` and friends on a plain tag become element (private style) variants. On a
`<plasmic-component>` instance or a slot they are **silently dropped** — use an interaction variant
on the component itself. A selector containing a pseudo-element (`::before`) discards the whole rule.

## Animations

`@keyframes` in the `<style>` block are matched to existing animation sequences **by name** and
overwrite them. An `animation:` shorthand naming a sequence that does not exist is dropped silently.
The name is stored as `var(--anim-<uuid>)` and a `var()` delay inside the shorthand is discarded — set
`animation-delay` in a separate `changeElement` call.

## Prohibited

| Pattern | Why |
| --- | --- |
| JavaScript, `on*` handlers | Turns into a "Run code" handler you did not intend, or is stripped. |
| Vendor prefixes | Plasmic normalises CSS; prefixes create duplicate, conflicting rules. |
| `data:image/svg+xml` in backgrounds | The parser cannot handle data URIs. |
| `currentColor` | Not resolved the way browsers do; produces unexpected inheritance. |
| `:root` | Conflicts with Plasmic's own `:root` and the token system. |
| Font fallback lists | Use one Google font name; a list breaks the visual editor. |
| Background images for content | Only real image elements are optimized. |
| Illegal nesting (link in link, `div` in `p`, button in link) | Hydration errors. |

## Images and icons

- Real `<img>` elements at `https://placehold.co/<w>x<h>`, with explicit `width`, `height` and `alt`.
  External URLs are only optimized when width and height are set.
- Icons: instance Plasmic's icon component by the exact name it has in the project's component
  listing; it ships its own placeholder. If the project has none, emit a correctly sized empty box,
  name the layer for the icon it wants, and list it in the report. Do not inline SVG, do not reach
  into an icon library project, and colour it through the instance's props or its container's token
  rather than `currentColor`.

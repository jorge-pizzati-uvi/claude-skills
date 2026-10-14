# Driving Studio through `window.PLASMIC_AI_TOOLS`

Session mechanics, and the writes that report success while storing nothing. Everything here was
learned by watching a "successful" call do nothing.

## The golden rule

**Read back the exact value, never `success`.** After every mutation, read the element again and
assert on the specific attribute. When `read` cannot see the category at all, verify visually.

## Session

- **Prefer a fresh tab over a reload.** Reloads hang on "Looks like the host app is taking a while to
  load", or paint blank while the tools still answer.
- **The host app must be running and must be the build carrying its registrations.** A production
  host serves a frozen build, so registration changes do not appear until someone rebuilds.
  `window.__PlasmicComponentRegistry` on the host page lists every registered meta — the only
  reliable check of what Studio is being offered.
- **Long calls die at the CDP ~45s timeout.** Whole-project reads, multi-variant loops and
  screenshot sweeps must use the start-and-poll pair in SKILL.md Step 0.
- **Introspect `_meta`; trust its keys.** The registry key is what is callable, even if an entry's
  `toolName` diverges. Input schemas there are authoritative.
- Mutating a component whose arena is not open works — they are model edits — but the canvas can
  render stale. Open it in a fresh tab before trusting a screenshot.
- **A background tab may never initialize.** Studio renders inside the host iframe; a hidden tab is
  throttled until the handshake stalls — blank page, "host app is taking a while" toast,
  `visibilityState === 'hidden'`, no tools. Have the user foreground the tab. Keep one loaded tab and
  switch arenas with the tools' own `navigate({ componentUuid })` rather than opening a second.
- **Check the branch in the URL every time you resume.** A teammate can rename a branch mid-session.
- **After navigating to another branch, the tools serve the old model until the page finishes
  loading.** Wait for `document.title` to contain the branch name before the first read; a known
  component "missing" from the listing means you read too early.
- One tool call ≈ one undo entry.

## Reading the output

`output` is a **string**. With `outputFormat: 'json'` that string is JSON — parse it and pull out the fields you want. Do not return a whole-project read
wholesale; extract in the page and return only what you need:

```js
// after the poll reports success — extract, don't dump
(() => {
  const r = JSON.parse(window.__t.result.output);
  const project = r.results.find(x => x.__type === 'Project') || r.results[0];
  return {
    breakpoints: project.screenBreakpoints,                  // name, uuid, minWidth/maxWidth
    tokens: (project.tokens || []).map(t => ({ name: t.name, uuid: t.uuid, value: t.value })),
    mixins: (project.mixins || []).map(m => ({ name: m.name, uuid: m.uuid })),
    components: (project.components || []).map(c => c.name),
  };
})()
```

Field names vary by build, so if a key comes back `undefined`, return `Object.keys(project)` and the
keys of one entry, then adjust.


- The element tree (`baseVariantTplTree`) is markup inside the JSON: element `id` is the tpl uuid,
  `label` the element's name, `data-props` a JSON blob of props and variant activations, `style` a
  `prop: value;` string. In the live build its attribute values arrive single-quoted with `\"`
  escapes, while `&`, `<` and `'` appear raw — so one apostrophe in a text value truncates a naive
  `data-props='([^']*)'` match and the element silently drops out of your sweep. Slice a window
  around the element id; never hand that field to a strict XML parser.
- Missing uuids do not throw — they come back as `InvalidResource` rows inside `results`.
- Interactions store targets as object paths (`{"path":["$state","x","y"]}`); grepping for
  `$state.x` finds nothing. Parse, don't text-search.

## Identifiers and the workhorse call

`read` returns every uuid, and creation calls report the ones they make:

- component uuid → the `createComponent` result, or `read({ project: { components: true } })`.
- element (tpl) uuid → the component's tree from `read({ components: ['<uuid>'] })`; each element
  carries `id` (the tpl uuid) and `label` (its name).
- variant and variant-group uuids → `read({ components: ['<uuid>'] })` **after** creating them; the
  component's `variants` list carries each variant's `uuid`, its `name`, and the `group` it belongs
  to. `createComponentVariantGroups` also reports the group it made — capture that, and confirm
  against `_meta.addVariantsToComponentVariantGroup.inputSchema` whether that call wants the group's
  uuid or its name before the first use.
- preset (mixin) identifiers → `read({ project: { mixins: true } })`. Apply one with
  `changeElement({ changes: [{ tplUuid, mixins: [...] }] })`, taking the element shape of that array
  from `_meta.changeElement.inputSchema` — it is the one payload field this skill cannot pin down for
  you.
- screen-variant (breakpoint) uuids → `read({ project: { screenBreakpoints: true } })`.
- arena uuid → **the component's own uuid**; Studio's arena URL carries it directly:
  `https://studio.plasmic.app/projects/<project>/-/<Component-Name>?branch=<branch>&arena_type=component&arena=<component uuid>`
  (`arena_type=page` for a page). Build it from what you already hold, and confirm it against the
  address bar the first time — that is the URL the run record wants.

**A worked `changeElement`** — the workhorse, used for every per-variant style and every post-insert
patch. `componentUuid` is the component being edited, `tplUuid` an element inside it, `variantUuids`
the variants being recorded into (omit for base):

```js
await window.PLASMIC_AI_TOOLS.changeElement({
  componentUuid: '<component uuid>',
  variantUuids: ['<variant uuid>'],            // omit → base variant
  changes: [{
    tplUuid: '<element uuid>',
    styles: { 'flex-direction': 'column', 'padding-top': '16px' },
    props:  { title: 'Hello' },                 // component instances only
    text:   'Hello',                            // text elements only
  }],
})
```

Confirm each field against `_meta.changeElement.inputSchema` before the first call; the payload
accepts more than this (mixins, visibility, repeat, name, unsetProps).


## Writes that silently do nothing

All of these return `success: true` and store nothing.

| What | Detail | Workaround |
| --- | --- | --- |
| Dynamic value on a variant-group prop | via `changeElement` or inserted HTML. Static option values do persist. | Studio UI: right-click the prop → Use dynamic value → Switch to Code. |
| `transition` shorthand | Never stores, from inserted HTML or from `changeElement`. | Create the transition once in the UI (Design → Transitions **+**), then patch the parts with `changeElement` — never the shorthand. |
| `transition-property` / `-duration` | Store only on an element that already has a transition; dropped outright from inserted HTML. `-delay` and `-timing-function` persist through `changeElement` (the importer drops all four), which is what makes a half-written transition look plausible. | Same as above. This table is the authoritative statement on transitions; SKILL.md Step 7 and html-rules defer to it. |
| Unsetting a slot override | `null` and `unsetProps` both no-op; there is no "revert to default slot content". | Insert a fresh instance, copy props across, delete the old one. |
| `deleteComponentVariants` | Reports success; variants remain. | Delete in the Variants panel. |
| Unknown prop or variant-group key | Accepted silently. A group named `listMode` written as `list` costs an afternoon. | Copy names verbatim from a fresh read. |
| `createComponentProps` with `type:'any'` + `defaultValue` | The prop is not created at all. | Create it without a default. |
| Renaming an element back to a taken name | Studio uniquified the duplicate on insert; renaming back keeps the suffix. | Pick distinct names up front. |
| Colour-typed props on instances | Cannot be set. | Never rebuild an instance carrying colour props via inserted HTML — the values are lost. |
| Renaming a **variant group** via `changeComponentProps` | Renames a prop fine; reports success and stores nothing for a group. There is no `deleteComponentVariantGroups`. | Get group names right the first time (see namespace below); a badly named group means rebuilding the component. |
| The **last `@media` block** in inserted HTML | Imports without error and may not apply. | Author the narrowest breakpoint with `changeElement` against its screen-variant uuid after the insert. |
| **A style bound to a prop** | `styles: { color: '{{ $props.x }}' }` is "Dropped invalid style … (Unexpected input)" **while the same call reports "styles changed successfully"**. `props: { style: … }` is "ignored reserved attrs". A `--var: {{ }}` declaration is dropped too. | Pass the colour through to a component instance instead: `{{ $props.x }}` **does** store on a colour-typed instance prop (insert `data-props` or `changeElement props`). Bind that component's own style once in the Studio UI. |
| **A static colour on an instance prop** | `data-props='{"background":"#ff0000"}'` → "Invalid prop"; same via `changeElement`. | Only expressions store on colour props. Set static colours in the Studio UI, or pass a `{{ }}` expression. |
| **Hiding a default slot child from a variant** | Base `displayNone` + variant `visible` never renders; instances reject a `display` style. | Base visible + variant `notRendered`. Reaches only instances that have not edited the slot — they own copies of the defaults. |
| **A screen-variant style under a component variant** | The component variant's rule outranks the breakpoint's. | Author the `[variant, breakpoint]` combination explicitly. |

**One namespace.** A component's prop names, variant-group names and element layer names share a
single namespace. A prop `title` next to a layer `Title` becomes `title2`; a group `Tag` next to a
layer `Tag` becomes `tag2`; nothing warns. Decide prop and group names first, then name layers out of
their way (`Title Text`, `Icon Well`).

## What `read` cannot see

Authoritative for the base tree, props, Plasmic variants and their overrides, and interactions.
**Blind** to:

- Registered (code-component) variants and their style overrides.
- Interaction variants such as Hover, even when the arena shows them.
- Variant group uuids for registered variants — which is why the tools cannot target them.
- Dynamic bindings on variant props: the panel shows the expression, `data-props` reads empty.
- Preview values and **slot default content** — a slot using its default prints identically to one
  overridden with nothing.
- **A style bound to a prop in the Studio UI.** `Layout/Section` binds its inner div's background to
  `$props.background`; `read` shows three plain tags and no expression. You cannot discover an
  existing colour primitive by reading — the project cache has to name it.
- **Screen-variant overrides, including visibility.** An element rendered only on Mobile reads as
  simply unrendered. Expect wrong conclusions like "that element is dead code".
- Imported projects' **components** beyond little more than id and name; code components never
  appear at all. Imported *assets* are a different matter — tokens, presets and breakpoints do come
  back from a project read, tagged with `fromProject`.

Everything in this list is why Step 8 screenshots.

## Transformations to expect — writes that land, changed

- Inserted HTML flattens `position:absolute; left/top:50%` on `<img>`, and drops `%` positions on
  component instances. Re-apply with `changeElement`.
- Relative hrefs to non-Plasmic pages are dropped; write them as `{{ "/some-path/" }}`.
- `transform: scale(0.8)` is stored as `scale3d(...)`; `box-shadow` hex-with-alpha becomes `rgba()`.
- Sizes use Plasmic's dialect (`width: wrap` for hug); writing `auto` reads back as the dialect value.
- `var(--token-<name>)` and `var(--token-<uuid>)` both resolve. Use the uuid whenever the name
  contains a `/` or a space, since that is not valid CSS on its own.
- `inline-flex` becomes `flex`; `!important` is stripped.
- A styled text `<div>` is split into a named container plus a `<span>`; only the span is a text
  element, so `changeElement({ text })` targets the span (`… is not a text element` otherwise).
- On a project whose tokens live in a dependency, every insert logs `Kept unresolved token reference
  "var(--token-…)"`. The reference is stored verbatim and resolves at render — noise, note it once.

## Structural operations

- **Cannot replace or unwrap a component root** — a human does that in Studio (right-click → unwrap).
- **`moveElement` across a layout parent resets position**: an absolutely-positioned child arrives at
  `left: 0px; top: 0px` and percentages are gone. Capture `left`/`top` first, re-apply after. A
  reorder **within the same parent** preserves styles — verified on eight pages of `%`-positioned
  markers.
- `moveElement` cannot make an element the root.
- `extractComponent` loses variant overrides that live on the parent's variants and target elements
  inside the extracted subtree; its name is **uniquified**, so re-read to learn the real one.
- `deleteElement` takes a singular `tplUuid`; loop for many.
- `moveElement`'s placement field is `position`, not `insertRelLoc`.
- Slot-targets cannot be renamed; replace one with `insertHtml … 'replace'`. A layer named `Pill` next to
  a slot `pill` uniquifies the slot to `pill 2` — the namespace rule covers slots too.
- `display: grid` + `grid-template-columns` store fine through `changeElement`; only the HTML import
  path is flex-only.
- `read({ project: { themes: true } })` is rejected — the field wants `'active' | 'all'`.
- Slots cannot nest, and a component cannot instance itself (cycle detection rejects it).

## Studio UI steps the tools cannot do

Ask the user for these rather than reporting success over a write that stored nothing:

- Creating the first transition on an element (Design → Transitions **+**). Its Delay field rejects
  `var(...)`; write the delay with the tools afterwards, and note that re-editing the transition in
  the UI silently resets it to `0s`.
- Styling registered variants (the variant chip records styles in the Design tab).
- Deleting variants, and unwrapping or replacing a component root.
- Opacity lives under Visibility; Scale under Transform.

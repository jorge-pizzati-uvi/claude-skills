# Plasmic's documented rules — the standard a built component is judged against

Every rule here comes from Plasmic's own docs, with the page it came from. They describe what makes a
component pleasant to keep editing in Studio. Where these and observed tool behaviour disagree,
follow what you observe and note the divergence in the run record.

## Structure, naming, slots, variants

The procedure (SKILL.md Steps 5a–6) carries these as instructions; the citations are
`learn/components`, `learn/best-practices`, `learn/layout`, `learn/slots`, `learn/variants`,
`learn/element-variants`, `learn/interactions-reference`. The one rule worth repeating here because
it decides the gate: "Generally, prefer using slots to variants when you can" and "if all that's
changing is some text or a configuration, then props are the recommended approach" — a slot is for a
custom **node**.

## Variant vs prop vs slot

The decision, verbatim from `learn/slots`:

> Are the content, component structure, and styles static and predictable? … If yes, you should use a
> **variant**.
> Are styles and component structure fixed, but only the content is different? … If yes, then you
> should use a **prop**.
> Are the content, component structure, and styles all different and unpredictable? … If yes, then
> you should use a **slot**.

Supporting rules:

- "when there's a fixed set of variations that should be controlled by the component author, then use
  variants. When the variations should be set by the component consumers… use slots."
  `learn/best-practices`
- "Generally, prefer using slots to variants when you can. (For developers: this is equivalent to
  favoring composition.)" `learn/best-practices`
- "if all that's changing is some text or a configuration, then props are the recommended approach";
  a slot is for adding a custom **node**. `learn/props`
- Minor content variations → variants. "For more substantial content differences, use different
  components", with shared chrome in a template component exposing a slot. `learn/best-practices`

## Where a style is allowed to live

Verbatim from `learn/style-presets`:

> Use **style tokens** when you want to reuse a single value across your project.
> Use **components** when you're reusing both structure and behavior.
> Use **style presets** when you want to reuse a combination of styles without enforcing structure.
> This is the middle ground.

Consequences:

- Token types are exactly: color, font size, line height, opacity, spacing, font family. **Radii,
  shadows and borders cannot be tokens** — they belong in a preset. `learn/tokens`
- Tokens can reference tokens: a semantic `Primary Color` pointing at `Blue-700`. `learn/tokens`
- Token names use `/` for folders, like component names. `learn/tokens`
- Project-wide **default styles** carry text and heading styling "without needing to apply styles to
  each element". `learn/page-building-tips`
- **CSS inheritance is blocked at component boundaries**: "each component fully specifies its own
  styles; we block css inheritance at component boundaries." A font on an ancestor will not reach a
  nested component. `learn/styling-and-layout`
- Do not rely on global element selectors in either direction — "we reset styles so that a global
  `h1` won't affect Plasmic". `learn/styling-and-layout`
- Prefer a stock Google font; a custom font needs CSS embed or app-host plumbing and Studio warns
  about it. `learn/custom-fonts`

One `h1` per page with correct levels below it, alt text on every image, and real image elements
rather than background images — only image elements are optimized, and an external URL needs explicit
width and height (`learn/page-building-tips`, `learn/page-performance`).

## Downstream, for a library component

Only the two rules that change how you design the component — the publishing mechanics are out of
scope for this skill:

- Imported components are **read-only in consuming projects**; only imported token values can be
  overridden there. Anything not exposed as a prop, slot or variant is unreachable downstream, so
  decide that surface now. `learn/publishing-importing`
- "keep your components as backward compatible as possible", avoiding "renaming props, deleting
  props, changing types". A breaking change means a new component and a deprecation, not a mutation.
  `learn/libraries-advice`

Doc root: `https://docs.plasmic.app/` — each path above is under `https://docs.plasmic.app/learn/`.

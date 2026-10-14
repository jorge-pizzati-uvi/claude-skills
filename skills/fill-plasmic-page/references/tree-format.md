# The page tree as `read` returns it

`read({ components: [uuid] })` with `outputFormat: 'json'` resolves to `{ success, output }` where
`output` is a JSON string: `{ results: [ { __type: 'Component', name, uuid, type, pageMeta, props,
variants, baseVariantTplTree } ] }`. The tree is **HTML-like markup inside that JSON string**.
`scripts/plasmic_fill.py parse` takes the raw `evaluate_script` result file as-is.

## Grammar observed (Studio build of 2026-10)

| Element | Meaning | Attributes that matter |
|---|---|---|
| `<div id style label?>` | a box, or a text element when it has only text inside | `id` = tpl uuid, `label` = layer name |
| `<span>`, `<p>`, `<a>`, `<h1..6>` | text elements; `<a>` carries `href` | `id` |
| `<img id src alt loading style>` | image element | `src` is the stored URL |
| `<svg id>` | icon (inline svg) | — |
| `<plasmic-component id data-plasmic-component data-plasmic-project? data-plasmic-name? data-props? style>` | an instance | component name (lowerCamel of the Studio name, e.g. `copyMainIntro`), imported project id for kit components, instance name, props JSON |
| `<slot name="x">…</slot>` | the fill given to a named slot of the enclosing instance | `name` |

Section = a direct child of the page root. Everything inside it belongs to that section.

## Quoting

The serializer emits well-formed HTML: `data-props` is single-quoted when the JSON has no
apostrophe and double-quoted with `&quot;` escapes when it does; text content escapes `&`, `<`.
Python's `html.parser` handles both; the script also falls back to a brace-balanced scan if a
`data-props` value fails `json.loads`. Never regex-match `data-props='([^']*)'` — the sibling
skill lost hours to exactly that on an older build.

## What the tree does **not** show

- A code-component prop that is **unset**. The instance has no `data-props`, or the key is absent,
  and the canvas renders the registered `defaultValue`. The registry read in Step 2 is the only
  way to tell "unset" from "set to the default text".
- Slot *default* content, screen-variant style overrides, interaction variants, dynamic `style`
  attributes, registered variants of code components. None are content; this skill ignores them.
- Components of imported projects: their names appear on instances (`data-plasmic-component`)
  but their own trees are not returned unless read by their uuid from the imported project.

## Field ids

| kind | id | written with |
|---|---|---|
| `text` | `<text tplUuid>/text` | `changeElement { tplUuid, text }` |
| `img-src` | `<img tplUuid>/attr.src` | `insertHtml { tplUuid, insertRelLoc: "replace", html: "<img … src=…>" }` — `src` is reserved for `changeElement.props`; the replacement has a new uuid |
| `code-prop` | `<instance tplUuid>/props.<name>` | `changeElement { tplUuid, props: { name: value } }` — arrays/objects as JSON values |
| `instance-prop` | same shape, on a kit instance (e.g. a marker's `title`) | same |

A text element's uuid is the **leaf** that holds the text (the `<div>` inside the `<slot>`), not
the instance. The importer sometimes splits styled text into a named container plus a `<span>`;
the span is the one with the text and the one that accepts `text`.

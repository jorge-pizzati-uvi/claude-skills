# Driving Studio through `window.PLASMIC_AI_TOOLS` from Chrome DevTools MCP

The subset of session mechanics this skill needs. Source: Plasmic's own `plasmic-designer` skill
(v1.3.3, `github.com/plasmicapp/plasmic/ai/skills/plasmic-designer`) and the field notes in the
sibling `create-plasmic-component` skill.

## Calling a tool

```js
async () => await window.PLASMIC_AI_TOOLS.changeElement({ componentUuid: "…", changes: [ … ] })
```

Every call resolves (never rejects) to `{ success: true, output: string }` or
`{ success: false, error: { message, type } }`. `output` is JSON (after `identify` with
`outputFormat: 'json'`); its `results[]` may contain `InvalidResource` rows for uuids that did not
resolve — a "successful" call can still have failed per element.

- `identify` once per page load, before anything else. After any navigation (including the tools'
  own `navigate`), re-identify — the symptom is an `EXECUTION_FAILED` whose message is the identify
  instructions.
- `_meta.<tool>.inputSchema` is the authority on field names. `bootstrap.js` returns the three this
  skill uses; check `insertHtml`'s before the first insert (target / location field names vary).
- `evaluate_script` with `waitForStableDom: false` for pure reads; `filePath` for anything over a
  few KB (the page tree is 50–150 KB). The returned value must be JSON-serialisable.

## Long calls

A single `evaluate_script` dies at the CDP timeout (~45 s). A full page read usually completes in
2–5 s; a project-wide read with tokens may not. For those, start into a global and poll:

```js
// start
(() => { window.__fill = { running: true, result: null };
  window.PLASMIC_AI_TOOLS.read({ components: ["<uuid>"] })
    .then(r => { window.__fill.result = r; })
    .catch(e => { window.__fill.result = { success: false, error: { message: String(e) } }; })
    .finally(() => { window.__fill.running = false; });
  return "started"; })()
```

```js
// poll (repeat while running), with filePath on the final call to save the result
async () => { for (let i = 0; i < 25 && window.__fill.running; i++) await new Promise(r => setTimeout(r, 1000));
  return window.__fill.running ? { running: true } : window.__fill.result; }
```

## Tabs

- One Studio tab, **foreground**. Studio renders inside the host iframe and a background tab is
  throttled until the handshake stalls (blank canvas, "host app is taking a while" toast, no tools).
- Prefer a fresh `new_page` over `navigate_page reload`.
- The host page (for the registry) can be opened in the background — it is a plain Next.js page.
- After switching branch in the URL, `document.title` must contain the branch name before the first
  read, or the tools serve the previous branch's model.
- Close what you opened when done (`list_pages` to find them).

## Reading what you wrote

`read` returns the stored value for text, `src`, and instance props — so read-back is a real check
for everything this skill writes. It does **not** return slot defaults, screen-variant overrides or
dynamic `style` attributes, none of which are content. The canvas can render stale after a model
edit; `take_snapshot` (a11y tree, sees into the iframe) after a fresh `navigate({ componentUuid })`
is the visual confirmation, and the only one that is cheap.

## Undo

One tool call is one Studio undo entry. Section-sized `changeElement` batches keep ⌘Z meaningful
and isolate a failing section from the rest. The run record keeps the `before` value of every
field; a rollback is one `changeElement` batch built from it.

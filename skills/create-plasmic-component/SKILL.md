---
name: create-plasmic-component
description: Replicate a Figma component or component set as a native Plasmic component — base markup, variant matrix and breakpoint overrides — built to stay editable by a designer, verified visually, and recorded in a run file that later runs update instead of rebuilding. Use when asked to turn a Figma design into a Plasmic component, to add a component to the design-system kit from a design file, or to rebuild an existing Plasmic component from an updated Figma node.
---

# Create Plasmic Component

Take a Figma component (or component set), build it as a **Plasmic-native** component in a Studio
project, and leave behind a run record mapping every Figma node to the Plasmic uuid it became.

Native components only. Never write React code, never register a code component, never edit a
repository beyond the run record. Never create design tokens, style presets or breakpoints — those
are owned elsewhere. Never publish the project or upgrade a consumer.

The output is judged by whether a designer can keep working on it in Studio, not by whether a
screenshot matches. `references/plasmic-rules.md` is that standard; read it before building.

## Inputs

Ask for whatever the request did not supply. A run does not start with a hole in it — one short
question, then continue.

- `FIGMA_LINK` — a `figma.com/design/...` link containing `node-id`, pointing at a Component or a
  Component Set. Anything else: say what the node actually is and ask for the right one.
- `PLASMIC_PROJECT` — the Studio project id (the segment after `/projects/` in a Studio URL). There
  is no way to list projects, so **ask** unless the request or the run records name one.
- `BRANCH` — the Studio branch to build on, which **must already exist**: the tools cannot create
  one (there is no branch, publish or merge tool), so a new branch is a user action in Studio's
  branch dropdown. Never assume `main`. A component built straight onto `main` is live to every
  consumer on the next publish, so if no branch is named, ask before touching `main` rather than
  defaulting to it.
- `COMPONENT_NAME` — the Plasmic name, with a forward slash for folders (`Cards / Destination Card`).
  Defaults to the Figma component's own name, normalized.
- `STYLE_SOURCE` — where tokens **and presets** come from: a separate project imported as a
  dependency, or the target project itself. Read the project first (Step 2) and ask when there are
  several candidates. This source is consumed, never written to.
- `INTENT` *(optional)* — one or two sentences on what the component is, does, and who fills it.
  Figma shows what a component looks like, never what it is for, and the variant/prop/slot decision
  depends on that. Absent, infer it from the Figma and layer names, **state the inference**, proceed.
- `INTERACTION_REF` *(optional)* — a URL or description of behaviour the Figma file cannot show:
  hover and press, what a tab switch does, enter/exit motion.
- `RECORD_PATH` — where the run record is written. Default `plasmic-docs/generated/<slug>.md` in the
  current repository, `<slug>` being `COMPONENT_NAME` kebab-cased (`Cards / Destination Card` →
  `cards-destination-card`). No repo, no `plasmic-docs/`: write it to the scratchpad and say so.

## Requirements

- Figma MCP: `get_metadata`, `get_design_context`, `get_screenshot`, `get_variable_defs`, and
  `get_motion_context` when the file has prototype interactions wired. These are usually deferred
  too — load them in the same batch as the browser tools. All of them take a `fileKey`: it is the
  segment after `/design/` in `FIGMA_LINK`, and `node-id=3-24212` becomes `nodeId: '3:24212'`.
  **`get_design_context` requires the figma-design-to-code guidance to be loaded first** — do that
  before Step 3, not during it.
- **Claude in Chrome** (`mcp__claude-in-chrome__*`). Everything in this skill happens through it —
  see Step 0. If those tools are deferred in your harness, load them (or invoke the `claude-in-chrome`
  skill) before Step 0, in one batch: `tabs_context_mcp`, `tabs_create_mcp`, `navigate`,
  `javascript_tool`, `computer`, `resize_window`, `tabs_close_mcp`. It attaches to the user's own Chrome, which is what carries the Plasmic session. Chrome
  DevTools MCP is not a substitute: it drives its own browser profile, which is signed out of
  Plasmic, and this skill never signs in.
- **The user's Chrome profile signed in to Plasmic.** The session lives in the profile's cookies,
  not in any particular tab, so you open your own tab and it inherits the session. Never sign in,
  never create an account, never ask for a password. If a Studio tab loads to a login screen, that is
  the prompt: ask the user to sign in, then re-check.
- A running **host app** is required only if the component will instance a **code** component (a
  React component registered by an app, not a native Plasmic one — Step 5a decides this). The canvas renders code components from the host, so a stale or
  missing host shows them as empty boxes and every screenshot then lies. Verify by opening the host
  URL and reading `window.__PlasmicComponentRegistry`. A component built purely from native elements
  does not need one.

**The run stops for the user by design — say so when you start, so nobody expects one unbroken
pass.** Always at the **gate** (Step 5a: the plan, before anything is built). Sometimes for the
preview URL in Step 8 (unless a previous run recorded it), and whenever the Studio tab is not
visible — the UI-only steps (colour bindings, variant-prop pass-through, external access,
transitions) are driven through the UI by the skill itself (`references/studio-ui-macros.md`) and
need a visible tab to do it. The gate is never skipped and never self-approved: an agent that cannot reach a
user returns the plan as its result and builds nothing.

**Every unmet precondition is a prompt, not an abort.** Say what is missing, say what the user should
do, wait, re-check, continue:

- No Studio tab or not signed in → ask them to open Studio and sign in.
- Host needed but unreachable or serving an old build → ask them to start or redeploy it, then
  re-check the registry.
- The branch in the URL is not `BRANCH`, or `BRANCH` does not exist → ask the user to create or
  switch to it in Studio's branch dropdown, then re-check. Never write to a branch whose name warns
  you off (`…-DO-NOT-EDIT`).
- `COMPONENT_NAME` already exists → ask: extend it via its run record, or pick a new name. Never let
  Studio uniquify a near-duplicate into existence.

## Step 0 — How to call the tools

Every Plasmic call is JavaScript evaluated in a Studio tab, through

```
mcp__claude-in-chrome__javascript_tool { action: 'javascript_exec', tabId, text: '<the code below>' }
```

`action` is required — omit it and the call fails validation, which looks like a tool bug and is not.
The tools live on `window.PLASMIC_AI_TOOLS` and each
returns a Promise resolving to `{ success: true, output: string }` or
`{ success: false, error: { message, type } }`. A call never rejects — always branch on `success`.

**The invocation pattern.** Nothing may block: a call over ~45s dies at the CDP timeout and looks
like a hang, and a shell `sleep` is not available. Start the work into a global, return immediately,
poll in a later call. Both snippets below are paste-ready as `text` exactly as written:

```js
// call 1 — start (an IIFE returning immediately)
(() => {
  window.__t = { running: true, result: null };
  window.PLASMIC_AI_TOOLS.read({ project: { tokens: true } })
    .then(r => { window.__t.result = r; })
    .catch(e => { window.__t.result = { success: false, error: { message: String(e) } }; })
    .finally(() => { window.__t.running = false; });
  return 'started';
})()
```

```js
// call 2 — poll (top-level await, short and non-blocking)
await (async () => {
  for (let i = 0; i < 25; i++) {
    if (!window.__t.running) { break; }
    await new Promise(r => setTimeout(r, 1000));
  }
  return { running: window.__t.running, success: window.__t.result?.success };
})()
```

A short call that cannot run long — a `_meta` dump, a small read of one element — can skip the split
and be awaited directly. Use one global name per concurrent job so two polls never collide, and if a
poll returns with `running` still true, poll again rather than assuming failure: the work continues
in the page.

**What comes back.** `output` is a string; with `outputFormat: 'json'` it is JSON. Extract in the
page and return only the fields you need — never dump a whole-project read. The worked extraction,
the field names, and the one escaping caveat that survives both formats are in
`references/studio-session.md`, *Reading the output*. Missing uuids come back as `InvalidResource`
rows inside `results`, not as errors.

Screenshots are `computer { action: 'screenshot', tabId }` — pass `scale: 0.5` for a sweep of many
variants, since full-scale images burn the budget fast. The same tool's `hover` action is the only
way to trigger an interaction variant. `resize_window { width, height, tabId }` — height is
required — changes the **window**, chrome included, so the viewport comes out narrower than the
number you pass and very small widths clamp at the OS minimum. Step 8 says how to handle that. Tabs
you open are yours to close (`tabs_close_mcp`) before you finish.

**The browser tool's output filter redacts things that look like secrets**, and Studio data trips it
constantly: any JSON key containing `token` ("Sensitive key"), any `a: b; c: d` style string
("Cookie/query string"), and 12-character mixed-case ids inside nested objects ("Base64"). Return
flat `name | uuid | value` strings, rename keys (`tkn`), and re-encode `:` and `;` in style dumps
before returning them. Run 2 lost more time to this than to any Plasmic behaviour.

**One Studio tab, switched in-page, and it must be visible.** Studio's UI renders inside the host
app's iframe, and Chrome throttles a background tab hard enough that the host-frame handshake can
stall indefinitely — the symptom is a blank page with only the "host app is taking a while" toast,
`document.visibilityState === 'hidden'`, and no `PLASMIC_AI_TOOLS`. Tabs in the Claude tab group
start in the background, so **ask the user to bring the tab to the front** before waiting on it,
and prefer one loaded tab switched with the tools' own `navigate({ componentUuid })` over opening
another. A page arena renders one artboard per
breakpoint, which covers responsive checks without a preview URL.

**Session start, in order:**

1. Get a tab and point it at Studio: `tabs_context_mcp` to see what you have, `tabs_create_mcp` for
   a new one (it takes no arguments — it cannot open a URL), then `navigate` it to
   `https://studio.plasmic.app/projects/<PLASMIC_PROJECT>/?branch=<BRANCH>`. Your tab inherits the
   profile's Plasmic session. Prefer a **fresh tab** over reloading one: reloads frequently hang on
   "Looks like the host app is taking a while to load". Note the `tabId`; every call needs it.
   **After any navigation to a different branch, wait until `document.title` contains `BRANCH`**
   before the first read — until then the tools serve the previous branch's model, and a component
   "missing" from the listing is the symptom.
2. Poll for the tools, in-page, up to 30 × 1s: `typeof window.PLASMIC_AI_TOOLS !== 'undefined'`.
3. Identify, **once per page load, before any other call**. A complete call:

   ```js
   await window.PLASMIC_AI_TOOLS.identify({
     model: 'claude-opus-5',          // the model you are
     client: 'claude-code',           // the CLI or client you run in
     skill: 'create-plasmic-component',
     outputFormat: 'json',            // 'json' or 'xml' — 'json' unless you prefer XML
   })
   ```

   All four fields are required; pass `'unknown'` for anything you genuinely cannot determine. Every
   navigation invalidates it, and the symptom is an `EXECUTION_FAILED` whose message is these very
   instructions — re-identify and retry rather than debugging the tool.
4. **Dump the schema before the first use of any tool** — `identify` being the one exception, since
   it must come first — and follow the schema over anything written here:

   ```js
   Object.keys(window.PLASMIC_AI_TOOLS._meta)                        // what exists
   JSON.stringify(window.PLASMIC_AI_TOOLS._meta.changeElement.inputSchema)   // how to call it
   ```

   Trust the `_meta` **keys**, not each entry's `toolName`. The ones this skill reaches for are
   `read`, `createComponent`, `insertHtml`, `changeElement`, `moveElement`, `createComponentProps`,
   `createComponentVariantGroups`, `addVariantsToComponentVariantGroup`, `upsertAnimations` and
   `deleteComponents`. That list is not exhaustive — `_meta` is the inventory, so check it whenever
   you need something not named here.

**Where uuids come from**, and a worked `changeElement`: `references/studio-session.md`,
*Identifiers and the workhorse call*. Read that section before Step 5b.

## Step 1 — Open the session and clear the preconditions

Run Step 0's session start. Then, before any write:

1. Confirm the branch in the URL is `BRANCH`.
2. **Read the records first.** `plasmic-docs/projects/<projectId>.md`, if present,
   replaces Step 2's harvesting and Step 2b for any family it already covers. If `RECORD_PATH`
   exists, this is a **re-run**: diff the new Figma inventory against the record's approved gate and
   node map, present only the differences at the gate, and change what moved with `changeElement` on
   the mapped uuids — `createComponent` only for genuinely new parts. Read both now, not later.
3. Prompt for anything else unmet, per **Requirements**, and re-check after the user fixes it.

## Step 2 — Read the project before reading the design

One call, run through Step 0's start-and-poll split — this is the largest read in the run and a bare
`await` will hit the timeout. Every flag is a boolean, so write them out:

```js
window.PLASMIC_AI_TOOLS.read({ project: {
  components: true, screenBreakpoints: true, globalVariants: true,
  tokens: true, mixins: true, themes: 'all',
} })
```

(`themes` wants `'active' | 'all'`, not a boolean.)

Plasmic stores **style presets as `mixins`**, so that flag is what returns the presets.

Record: existing component names (the collision check), each breakpoint's `uuid` and
`minWidth`/`maxWidth` plus the project's responsive strategy, the token table, and the presets.

Project-level assets are flattened across the project and its dependencies, and imported entries
carry `fromProject` — that tag is how you tell a `STYLE_SOURCE` token from a local stray, and
`STYLE_SOURCE` wins. Imported **components** are a different matter: the listing gives little more
than id and name, and code components never appear at all. To instance one (Step 7), take its name
from this listing and pass `data-plasmic-project`.

This read is load-bearing for Steps 4, 5 and 6. Skipping it silently discards responsive work later.

**Cache it.** On first contact with a project, after Step 2b, write
`plasmic-docs/projects/<projectId>.md` from `templates/project-cache.md`: `STYLE_SOURCE`,
the token table (name, uuid, value), presets (name, uuid), breakpoints (name, uuid, width, strategy),
the family conventions, and the preview host once known. **Later runs read the cache instead of
re-harvesting** (21 calls in run 1 for tokens identical across the kit); the one call that always
runs is `read({ project: { components: true } })`, for the collision check and fresh sibling uuids.
Refresh a section when a lookup misses, when `COMPONENT_NAME`'s family is not in the table, or when
the user asks.

## Step 2b — Read the family before reading the design

The project's existing components already answer most of Step 5a's questions, and **their
conventions outrank the Figma file's structure and this skill's own preferences.** From the Step 2
listing, `read({ components: [...uuids] })` — in one call — the siblings named in the brief, the two
or three nearest under the same top-level folder as `COMPONENT_NAME`, and, whenever the brief or the
Figma says "N-up", "columns", "groups of N" or shows a count axis, the nearest component that is a
**list of items** (its name usually says so: Columns, List, Grid, Slider).

Extract, into a short table for the record and the gate — describe what you find, do not assume it:

- content customization — slots or props, per element type (title, body, image, CTA, icon);
- the subcomponent convention — where sub-parts live (`…/_components/…` or otherwise) and what;
- the list pattern — there are two, and the gate offers both: (a) a **count variant** on the
  container hiding surplus default items, slots re-exposed as `item N - <slot>`; (b) a **free slot**
  of item instances the consumer adds to and removes from, with any size/density axis **passed
  through** to the items. Note which the family uses, how surplus is hidden, how separators are done;
- how colour variation is done — variant group, colour prop, or per instance;
- layer naming style.

Where the family has no precedent, fall back to the docs' decision tree. Run 1 read one sibling "for
conventions" and mirrored none of them; the result was a single card where the kit's own `Copy
Columns` pattern — and the brief — called for a list container with an item subcomponent.

## Step 3 — Inventory the Figma component

1. `get_metadata` on the node → each variant's node id and name. It returns names, ids, types and
   geometry only, so the **axes come from the variant names themselves**: Figma writes them as
   `Size=M, State=Default`, which parses into axis/value pairs. Confirm the axis names against
   `get_design_context` on the component set if the names are ambiguous.
2. `get_design_context` with `excludeScreenshot: true` → layout, text, styles. **One call on the
   component set first**, then per-variant calls only for variants whose geometry differs —
   colour-only variants share a read. On a large node it may silently fall back to metadata only; if
   the response has no styles, narrow the node and call again.
3. `get_screenshot` per variant, and per responsive frame when the design has them. **It returns a
   short-lived URL, not an image** — pass `enableBase64Response: true` to get the image inline, or
   fetch the URL with `curl` into the scratchpad. Note its `maxDimension` (1024 by default): that is
   the resolution you are comparing against in Step 8, so keep it consistent across variants. An
   image you never actually fetched is the one way Step 8 can report a verification that did not
   happen.
   Nested instance ids (`I…;…`) are rejected by `get_screenshot`, `get_variable_defs` and
   `get_motion_context` — they take plain `123:456` ids.
4. `get_variable_defs` on the node → the Figma variables behind its colours, spacing and type. This
   is the left-hand column of Step 4's mapping; without it there is nothing to map.
5. `get_motion_context` when the file has prototype interactions wired.

## Step 4 — Map tokens and presets, then stop if anything is unmatched

Match each Figma variable from Step 3 to a Plasmic token from Step 2 by comparing their paths —
Figma's `Color/Brand/Primary` against a token named `color/brand-primary` or `Color / Brand / Primary`,
whatever the project actually uses. **Then reference the token by copying its identifier verbatim
from the Step 2 read** — never by constructing one, which silently fails to resolve:

- name is plain (letters, digits, `-`, `_`) → `var(--token-<that exact name>)`
- name contains a space or a `/` folder separator — the common case, since Plasmic uses `/` for
  folders — → use the token's **uuid** from the Step 0 extraction: `var(--token-<uuid>)`. The
  importer resolves either form; only the uuid form is always valid CSS.

If the tokens read exposes no uuid field under that name, return one token object whole
(`JSON.stringify(project.tokens[0])`) and use whatever identifier it does carry.

A repeated combination of styles that already exists as a **preset** is applied as that preset rather
than re-declared as loose CSS. Tokens only exist for color, font size, line height, opacity, spacing
and font family, so **radii, shadows and borders belong in a preset**.

**Unmatched values that matter are a question for the user**, asked inside the gate (Step 5a). A
value matters when it is brand-significant or used repeatedly — a colour, a type size, a spacing step
that clearly belongs to the system: hardcode here, or wait for the token to be added to
`STYLE_SOURCE`? A genuinely incidental one-off is hardcoded and logged to the record's **Gaps**
section without asking. Many Figma files bind few variables, so also match by *value* against the Step 2
token table before declaring anything unmatched.

Never call `createStyleTokens`, `createMixins` or `overrideImportedStyleTokens` — a locally invented
token detaches from the source on the next dependency upgrade, silently.

## Step 5a — Propose the component, then stop at the gate

**Nothing is created in this step.** It ends with a plan message from `templates/plan-gate.md` and
the turn ends; the user approves or edits it, and Step 5b builds exactly that. Every judgment call
run 1 got wrong was made silently here — this gate is where it costs two minutes instead of a
rebuild.

The plan message carries five things:

1. **Shape.** Single component, or list container + item subcomponent, with the exact names —
   formed the way the mirrored sibling forms them (if the family writes `Copy/Copy Columns/Copy
   Columns` + `…/_components/Column Item`, follow that; do not impose a pattern the family lacks) —
   and the sibling it mirrors. A count axis in the brief or the Figma ("groups of 3 and 4") means the
   list pattern from Step 2b, not a `columns` variant on a single component.
2. **Variant axes, each with its provenance** — `Figma property`, `INTENT`, or `inferred`. Only the
   first two are proposed as decisions. **Inferred axes are listed as candidates and are not built
   unless approved.** The skill already refuses to invent motion; it refuses to invent variants the
   same way. A colour palette frame, an optional layer, a toggle you can imagine — candidates, all of
   them. Call out any variant that would be identical to base so the user can drop it.
3. **Customization surface.** One row per varying part: recommended verdict, the family convention it
   follows, and the alternative. The decision from `references/plasmic-rules.md`, judged against
   `INTENT` — static and predictable → variant; fixed structure, different content → prop; all three
   vary → slot — with two biases on top:
   - **Slot is the default for anything a human edits on canvas**: text, image, CTA, icon. A designer
     double-clicks a slot; a prop is a form field. A prop is proposed only for configuration — a
     colour choice, a count, a URL — or where the family does it that way.
   - Colour that must track a variant is styled on the **slot-target** per variant; that is how a
     sibling keeps slots and still flips text colour. "A slot would lose the colour" is not a reason
     to make it a prop.
4. **Placeholders and gaps** — images, icons, anything that will need a human swap — and the
   **unmatched-token table from Step 4**, with the hardcode-or-wait question, so it is answered in the
   same reply rather than costing its own round-trip.
5. **Breakpoints** to be authored, mapped to the project's screen variants.

6. **Colour that must follow a prop** (`background`, `textColor`): which regions, and the binding
   route from Step 5b — the project's colour primitive if one exists, a proposal to create it if not,
   or Studio UI steps. Say which, so the user knows what will need a human.

Also settle here, because they cannot be changed later: whether any part is an **existing kit
component** to instance rather than rebuild (and whether that makes the host app a precondition),
and the **prop and group names** — props, variant groups and layer names share one namespace, a
collision is silently uniquified, and a group cannot be renamed back. Pick them now; Step 5b names
the layers out of their way.

None of this retrofits cheaply: converting to a slot later loses overrides, and removing a variant
group after publishing destroys args in every consuming project. Record the gate message, and the
user's answer, in the run record verbatim.

## Step 5b — Build exactly what was approved

**Build order — this sequence avoids a root inside a root, which no tool can undo.** `createComponent`
takes the markup directly; `insertHtml` adds *into* an existing tree and cannot replace a root. So:

1. `createComponent({ name: COMPONENT_NAME, type: 'plain', html })` with the **whole** component and
   static placeholder text. Exactly one root element, a stack.
2. `createComponentProps` for the props decided above.
3. `changeElement` per bound element to swap its static text or attribute for `{{ $props.name }}`.
4. `insertHtml` only for anything added afterwards — it takes `componentUuid`, the `html` fragment,
   a target element and an `insertRelLoc` (`append`, `prepend`, `before`, `after`, `wrap`, `replace`).
   Check `_meta.insertHtml.inputSchema` for the exact field names before the first call, and note
   that a fragment inserted into a tree must **not** re-declare a root stack.

Creating a minimal root first and inserting the real markup into it is the one sequence to avoid: it
leaves a wrapper the tools cannot remove, which fails Step 8's checklist while every call reports
success.

Props, created at stage 2:

```js
await window.PLASMIC_AI_TOOLS.createComponentProps({ componentUuid, props: [
  { name: 'title', type: 'text', defaultValue: 'Destination name' },
] })
```

Check `_meta.createComponentProps.inputSchema` for the exact field names and the legal types (text,
number, boolean, choice, href, image url). Keep each description to one or two short sentences; the
Studio panel is narrow, and `references/studio-session.md` lists the prop shapes that fail silently.

**Bind with `{{ $props.name }}`** — static text is static, and `{{ }}` is what makes it dynamic.
Two mechanisms, because `changeElement` has no attribute field:

- **text** → `changeElement({ componentUuid, changes: [{ tplUuid, text: '{{ $props.title }}' }] })`
  — on the **`<span>`**: the importer splits a styled text div into a named container plus a span,
  and only the span accepts `text`.
- **an attribute** (`href`, `src`, `alt`) → re-emit that one element with `insertHtml` using
  `insertRelLoc: 'replace'` on it, the binding written into the attribute.
- **a prop on a `<plasmic-component>` instance** → `changes: [{ tplUuid, props: { x: '{{ … }}' } }]`,
  except on a variant-group prop, which the tools cannot write at all.

The root element is the exception: it cannot be replaced, so **never design a root that needs a
dynamic attribute**. A card that is itself a link gets a stack root with a link element inside it
carrying the `href` binding — which is better structure anyway, since it leaves the root free to be
styled and slotted.

Text and attribute bindings **do** read back, so verify them by reading the element. A dynamic value
on a **variant-group prop** is the exception twice over: the tools cannot write it at all, and `read`
shows it as empty even when the Studio panel shows the expression — never conclude from an empty read
that a variant binding failed.

**Read `references/html-rules.md` before writing the markup** — it is the accepted subset, what gets
silently dropped, and the `<plasmic-component>` / `<slot-target>` grammar. Flex only; Studio's Grid
cannot be authored this way, so a tile layout is a wrapping flex row. The decisions that belong here
rather than there:

- **One root, a stack**, with gap and padding; sizing chosen per axis. No free positioning except a
  genuinely floating child.
- **Author the `@media` blocks now**, in this same HTML, at the exact breakpoint widths from Step 2
  (Step 6 says why exactness matters) — **except the narrowest breakpoint**, whose block has imported
  without applying; author that one with `changeElement` against its screen-variant uuid right after
  the insert.
- **Collapse wrapper elements.** Figma import is the classic source of excessive HTML; one box ≈ one
  div. Drop frames that exist only because Figma had one.
- **Name every meaningful layer** (`data-plasmic-name`) so the outline reads like the design — and
  **out of the way of the prop and group names approved at the gate**: `Title Text` next to a prop
  `title`, never `Title`. A collision does not warn; it silently yields `title2`.
- **Slots** (`<slot-target>`) get realistic default content; several named slots beat one big one.

**Colour that must follow a prop.** The tools cannot bind a style to a prop: `{{ $props.x }}` in
`styles` is dropped as an invalid style (while the same call still says "styles changed
successfully"), `style` is a reserved attribute, and a CSS-variable declaration is dropped the same
way. What Studio actually stores for such a binding is a dynamic **`style` HTML attribute**
(`{{ ({ background: $props.background }) }}`), and the skill can create it itself by driving the
Studio UI — `references/studio-ui-macros.md`, **Macro 1**: Settings → HTML attributes → `+ style` →
Use dynamic value → Switch to Code → expression → Save. Verified end to end on a real component;
roughly ten clicks per element, verified on canvas since `read` cannot see it. **Do that for each
bound element rather than asking the user**, and fall back to the primitive pattern below only when
the Studio UI is not reachable (hidden tab, no screenshots).

The tools **can** write `{{ $props.x }}` to a **colour-typed prop on a component instance** —
through `data-props` at insert and through `changeElement({ props })` afterwards — while a static
colour on an instance is rejected. So the alternative, when the UI is unreachable or a project
prefers it, is **pass-through to a primitive that was bound once**:

- The project keeps one tiny native component, e.g. `Primitives/Color Surface`: a stack root, a
  `children` slot, colour props `background` and `color`, each bound to the root's style **once in
  the Studio UI** (right-click the style → Use dynamic value → `$props.background`). Record it in the
  project cache. (`Layout/Section` in a kit may already bind `background` and can serve for that.)
- A generated component wraps every region whose colour follows a prop in an instance of it:
  `<plasmic-component data-plasmic-component="primitivesColorSurface"
  data-props='{"background":"{{ $props.background }}","color":"{{ $props.textColor }}"}'>`. Text
  inside inherits `color` only if the text elements leave colour unset — verify on canvas, and if
  project default styles force a text colour, wrap the text group in its own instance.
- No primitive yet → propose creating it at the gate as a one-time setup: the tools create it, its
  two style bindings are the only Studio UI steps, and every later component reuses it. Declined →
  the per-element bindings go on the report as Studio UI steps, as before.

**Building the list pattern**, when the gate approved one:

1. The **item** first: `createComponent` at the family's subcomponent path, slots for every content
   part, no props unless the family uses them. Verify it, and note the exact name `createComponent`
   returned — that is the `data-plasmic-component` value below.
2. The **container**: `createComponent` whose html holds the **maximum** item count as instances.
   **Base shows every item**; each `itemCount` option hides the surplus. Inside each instance, every
   slot fill wraps a `slot-target` so the consumer edits item 1's title from the container:

   ```html
   <plasmic-component data-plasmic-component="<Item name as returned>" data-plasmic-name="Item 1">
     <slot name="title"><slot-target name="item 1 - title">Title</slot-target></slot>
     <slot name="body"><slot-target name="item 1 - body">Body copy</slot-target></slot>
   </plasmic-component>
   ```

   This is **not** the forbidden slot nesting — that rule is a `slot-target` inside a `slot-target`.
   A `slot-target` inside a `<slot>` fill is exactly how a nested slot is exposed upward.
3. After Step 6 has created the `itemCount` group and its variant uuids exist: for each option,
   `changeElement({ variantUuids: ['<option uuid>'], changes: [{ tplUuid: '<surplus item>', visibility: … }] })`
   using the `displayNone` form (shape from `_meta`), not "not rendered", so hidden items stay
   editable in the outline.
4. **Verify the re-exposure by hand**: `read` is blind to slot defaults and the QA page instances the
   container with its defaults, so a mis-wired `slot-target` shows nothing wrong anywhere. Open the
   container in Studio and confirm `item 1 - title` appears in the right panel's slot list, or ask the
   user to.

Shape (b), the free slot: the container's `cards` slot holds the default instances; a size axis on
the container passes through as `size="{{ $props.size }}"` on each default instance — a
**variant-group** binding the tools cannot write; do it with `references/studio-ui-macros.md`
Macro 2, or list it as a UI step if the UI is unreachable. Hiding a
default item under a variant works as **base visible + variant `notRendered`**; base `displayNone` +
variant `visible` does not render. A consumer who edits the slot owns copies of the defaults, so the
hide reaches only untouched instances — say so in the report.

## Step 6 — Variants and breakpoints

**Variant groups**: `createComponentVariantGroups` — name the **axis** (`size`, `state`), with
`singleChoice`, `multiChoice` or `standalone` — then `addVariantsToComponentVariantGroup`. Then
**re-read the component** to collect the variant uuids, and style each with
`changeElement({ componentUuid, variantUuids: ['<uuid>'], changes })`.

- Copy group and variant names **verbatim from that read** — an unknown group or prop key is accepted
  silently and stores nothing.
- Most styles stay on the **base** variant; a variant overrides only what genuinely differs, and the
  component must look right with no variant active.
- **Allow external access** on every group an instance must set, or the control never appears in the
  designer's Settings tab. Check `_meta.createComponentVariantGroups.inputSchema` for a field that
  sets it; if there is none, do it through the UI (`references/studio-ui-macros.md` Macro 3) and
  verify by screenshot — never assume it happened.

**Breakpoints already exist and cannot be created.** They are project-level global variants, and they
are **cumulative** — there is only ever a start to the range, never an end. Author overrides as a
cascade, not as bands. Two routes:

- A `@media` query in the inserted HTML (Step 5b), matched to a breakpoint by **exact numeric
  equality** against `max-width` (desktop-first project) or `min-width` (mobile-first). One pixel off
  and the whole ruleset is discarded with no error.
- Or `changeElement` with the breakpoint's uuid in `variantUuids`, for patches after the fact.

A component variant's style **outranks** a screen variant's: `size=small` → 4 columns beats
`Mobile` → 1 column. Where both apply, author the `[variant, breakpoint]` combination explicitly in
`variantUuids`.

**Change styles only** at a breakpoint — a text or image swap flashes the original content before JS
runs. Hide with `display:none`, not "not rendered". And check the design even needs a breakpoint:
stretch with min/max, or a wrapping stack, often removes it.

## Step 7 — Behaviour and motion

Sourced, in order, from `get_motion_context`, from `INTERACTION_REF` opened in Chrome, and from the
design's own state layers. **Measure the reference** — read the computed `transition`/`animation` off
the live element rather than guessing 300ms.

Reproduce in this order of preference:

1. An existing kit component that already has the behaviour, instanced via `<plasmic-component
   data-plasmic-component="…" data-plasmic-project="…">`. Never re-implement one in raw markup — the
   decision belongs in Step 5a, before the markup exists, and it is the case that needs the host app.
2. Plasmic interactions plus variants, for the genuinely simple cases. Hover, pressed, focused and
   disabled are **interaction variants**, not scripts.
3. Neither — record it as **needs a code component** and say so in the report. That is where this
   skill ends.

Motion rules that each cost a session to learn:

- A **transition lives on the base variant only.** A variant cannot turn one off, so an "enter"
  variant holding the from-state animates *towards* it instead of snapping. Mount/unmount motion may
  use a transition; a **swap in place must be a keyframe animation**, with the driving state held for
  the animation's full duration.
- **Transitions cannot be created through the tools.** Create the first one through the UI
  (`references/studio-ui-macros.md` Macro 4), then patch property and duration with `changeElement`.
  What stores and what silently does not: `references/studio-session.md`.
- `@keyframes` go through `upsertAnimations` and are matched **by name**; reusing a name overwrites
  the existing sequence. Apply as `animation: '<name> 300ms ease-in both'`, then set
  `animation-delay` in its own call — a `var()` delay inside the shorthand is discarded, and a
  shorthand naming a sequence that does not exist is dropped with no error.
- Code-component **registered variants** cannot be targeted by the tools and do not appear in `read`.
  Say so; do not try.

With no motion reference and no prototype, do not invent either. Build the static variants and say in
the report that behaviour was not specified.

## Step 8 — Verify

1. **Read back the exact value. Never trust `success`** — see the silent-write table in
   `references/studio-session.md`. Assert on the attribute, and check `results` for
   `InvalidResource` rows.
2. **Screenshot every variant and every breakpoint.** The tools cannot click a variant chip on the
   canvas, so build a throwaway QA page and shoot that instead:
   - `createComponent({ name: 'ZZ QA / <Component>', type: 'page', pageMeta: { path: '/zz-qa-<slug>' } })`
     — give it a path explicitly, or there is nothing to preview; confirm the `pageMeta` field names
     against `_meta.createComponent.inputSchema` — then `insertHtml` one
     `<plasmic-component>` instance per variant, each activated through `data-props`
     (`{"size":"m"}`, `{"disabled":true}`) and labelled by an adjacent text element.
   - Get the preview URL: the page's `path` from the call above, on the project's preview host. If
     that host is not already known, ask the user to hit Play once and paste the URL. Record it in
     the run record so a re-run skips this.
   - `tabs_create_mcp` then `navigate` to that URL, and `resize_window` toward each width you need — the breakpoint **edges**
     (for a single 768px breakpoint: 1920 / 769 / 768 / 360 desktop-first, or 1920 / 768 / 767 / 360
     mobile-first — the pair straddling the breakpoint is the point), then `computer` to screenshot
     each. **Confirm the viewport you actually got**: `resize_window` sizes the window including
     browser chrome, and small widths clamp at the OS minimum, so read `window.innerWidth` back in
     that tab and use *that* number. If you cannot land on both sides of a breakpoint, say so in the
     report rather than calling it verified.
   - Compare against Step 3's Figma screenshots. **Delete the QA page** with `deleteComponents` when
     finished, and say in the report if you could not.
   - The preview tab is not Studio and has no `PLASMIC_AI_TOOLS`. The Studio tab keeps its session
     while you work in another tab — re-`identify()` only if that tab itself reloaded or navigated.
   - **Hover, pressed and focused** cannot be reached by `data-props` and cannot be seen by `read`.
     Screenshot first to find the element, then `computer { action: 'hover', coordinate, tabId }`
     and screenshot again; where that is impractical, say in the report that those states need a
     human eye. Never report them as verified.
   - Close the tabs you opened when you are done.
   Step 5b's warning about inserting into a fresh root does not apply here: this page is scaffolding
   and gets deleted, so a wrapper in it costs nothing. Two things the QA page **cannot** show, because
   its instances carry copies of the component's default slot content: variant-scoped visibility of
   default items, and anything else that lives in a slot default. Check those in the **component
   arena** (one artboard per variant) via in-page `navigate({ componentUuid })`.

   This is not optional polish: `read` is blind to screen-variant overrides, interaction variants,
   slot defaults and dynamic bindings, so structural checks cannot see most of Step 6.
3. At most three correction rounds, then report what still differs.
4. **Run the editability checklist**: one stack root, no free-positioned boxes, no inline `style`
   attributes outside the instance exception, every meaningful layer named, every slot carrying
   default content, every prop actually bound (not orphaned), groups and props marked for external
   access, base variant correct with nothing active, no fixed width that can overflow a phone, styles
   living in tokens and presets rather than repeated literals. A component that matches the
   screenshot and fails this list is not done. For a list container, add: every `item N - <slot>`
   visible in the right panel — the QA page cannot prove this.

## Step 9 — Write the run record and report

Write `RECORD_PATH` from `templates/run-record.md`: Figma node, `INTENT` as given or inferred,
`STYLE_SOURCE`, `INTERACTION_REF`, the family conventions mirrored, the gate message as approved, the
variant matrix, the token and preset mapping, the gaps, the arena URL, and the fenced JSON block
mapping Figma node ids to Plasmic uuids. Update `plasmic-docs/projects/<projectId>.md` with anything learned about
the project itself (preview host, a convention, a trap). That map is what makes the next run an update instead of a rebuild.

**Write it even when the run stopped early** — after an unmatched token, a blocking UI step, or three
failed correction rounds. A partial record with the uuids so far is worth far more than none.

Then publish a **report card** — a one-screen page from `templates/report-card.md`, for the people
who did not sit through the run: what was built and where (arena links, preview if known), the
decisions as approved at the gate and what changed from the first proposal, placeholders and
Studio UI steps still needed, anything unverified, and **the cost** — wall-clock time, tool calls,
gate round-trips — so a slower run is visible as a regression. Publish it with the Artifact tool
(load the `artifact-design` skill first, as that tool requires); if no Artifact tool is available,
write it as `plasmic-docs/generated/<slug>.report.md`. Put the link in the chat report.

The chat report itself stays short: the link, the Studio UI steps, and the gaps.

## Notes

- Each prompt to the user ends the turn rather than pausing mid-run: finish everything that does not
  depend on the answer, write the record, say plainly what you need — then resume from the record
  when they reply.

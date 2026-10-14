# Studio UI macros — the steps the tools cannot write, done through the UI

The browser tool's `computer` action can drive Studio's own UI: `left_click`, `right_click`, `type`,
`key`, `scroll`, `zoom`, `screenshot`. Studio renders **inside the host-app iframe**, so `find` and
`read_page` see only the top frame — every click is by **coordinates taken from a fresh screenshot**.
Screenshot before each click that depends on layout; never reuse coordinates across a panel change.

Preconditions, or nothing below works:

- The tab must be **visible** (`document.visibilityState === 'visible'`). A tab in the Claude tab
  group may open in a tiny off-screen window (`outerWidth` ~450, `screenY` past the screen height):
  the UI never paints there. Ask the user to bring it to the front.
- The Studio shell must be loaded: the left outline, the canvas, and the right panel all visible.
- **Edits made while the UI frame was dead may not persist**, even when the tool reported success —
  a `deleteElement` run in a blank tab vanished on reload. After the last write, keep the tab open
  for a few seconds and re-read before closing it; never close a tab on the heels of a write.

## Macro 1 — bind a style to a prop (`background`, `color`, …)

What it creates: a dynamic **`style` HTML attribute** on the element, e.g.
`{{ ({ background: $props.background }) }}`. That is how `Layout/Section` binds its background, it
renders in canvas and codegen, and it is the one representation the tools cannot write (`style` is a
reserved attribute; `{{ }}` in `styles` is dropped). `read` cannot see it afterwards — verify on
canvas.

1. **Select the element.** This is the unreliable step; budget for it.
   - Top-level rows of the outline (direct children of the root) select on a plain click.
   - **Nested rows are unreliable** with synthetic clicks: the same hover-then-click sometimes
     selects the row, sometimes a different row, sometimes nothing. The outline also re-lays itself
     out after every selection, so coordinates go stale instantly — zoom the outline immediately
     before the click, with nothing in between.
   - Working keys: **`Shift+Enter` selects the parent** of the current selection. `Tab`, arrows and
     `Enter` do **not** navigate siblings/children; `Enter` on the canvas enters focus mode on an
     artboard and starts **recording into that variant** (red frame, variant name top-left) — check
     the top-left switcher reads `Base` before any edit, and escape focus mode if not.
   - A chevron click expands a row and sometimes selects it. The outline **search filter** shows
     matching rows but they cannot be selected by synthetic clicks. **Double-click** opens inline
     rename and leaves the UI dimmed until `Escape`.
   - **Most reliable for nested elements: click the element on the canvas**, then `Shift+Enter` up
     to the ancestor you want, checking the header each time. Needs the canvas zoomed so the element
     is bigger than the host chrome that may overlay the artboard's top edge.
   - If selection keeps failing, prefer binding on the nearest **top-level** ancestor that the
     design allows (e.g. `background` + `color` on the block rather than on each text element) or
     hand the one click to the user — never keep clicking blind.
   Confirm the right-panel header shows the element's name before going on; "Component data" alone
   means nothing is selected.
2. **Settings tab** (right panel, top left of the three tabs).
3. **HTML attributes → `+`** (the plus at the right end of the section header). A search field
   appears: type `style`, press Return. A `Style` row appears, value `unset`.
4. **Right-click the `Style` value** → menu: *Allow external access / Use data token / Use dynamic
   value* → click **Use dynamic value**. The "Select data" picker opens listing the component's props.
5. **Switch to Code** (top right of the picker). The editor opens **pre-filled with `undefined`**.
6. Click into the editor, **`cmd+a`**, type the expression, e.g. `({ background: $props.background })`
   or `({ color: $props.textColor })`. The editor auto-closes brackets, so **press `Delete` (forward
   delete) twice** to remove the surplus `})`, then `zoom` on the line to confirm it reads exactly
   right and the preview pane on the right shows the evaluated object, not `undefined`.
7. **Save** (bottom right of the editor). The `Style` row now shows the expression.
   To **edit** an existing binding later, left-click the `Style` value — the editor reopens
   pre-filled (the right-click menu only offers remove / external access / fallback).
8. **Verify on canvas**, not with `read`: component arenas are often height-cropped, so open a page
   arena (a throwaway page with one instance, deleted afterwards) and screenshot the block. Change the
   prop on the instance if you need to prove it follows.

One element per pass; several properties on one element go in one object
(`({ background: $props.background, color: $props.textColor })`).

## Macro 2 — bind a variant-group prop on an instance (`size="{{ $props.size }}"`)

Select the instance → Settings tab → the group's control under Props → right-click → **Use dynamic
value** → pick the prop or Switch to Code → Save. Same picker as Macro 1 from step 4.

## Macro 3 — Allow external access

Right-click the prop, state or variant-group row → **Allow external access** (it is the first item in
the same context menu as Macro 1 step 4). Note the sub-menu arrow: it offers read-only vs read-write
for states.

## Macro 4 — create a transition

Select the element → Design tab → scroll to **Transitions → `+`**. Defaults to `all / 1s / Ease`;
set the property and duration here, then patch `transition-delay`/`-timing-function` with the tools
if they need `var()` values (the UI's Delay field rejects `var(...)`).

## Habits that keep macros cheap

- **Never type blind.** Every `type` must follow a `zoom`/screenshot that shows the intended field
  focused (the attribute search box, the code editor). Unfocused keystrokes are Studio shortcuts:
  `style` typed into the canvas opened insert-free-box mode and the global search. If a batch
  contains a `type`, the click that focuses the field must have been verified in an earlier call.
- Selection is lost easily (a tool call, a canvas scroll). Re-confirm the right-panel header
  immediately before the `+` click, in the same batch only if nothing else intervened.

- Screenshot at `scale: 0.6`; `zoom` a region when reading small text or verifying a typed value.
- After a `navigate({ componentUuid })` wait ~3s and screenshot before clicking — the outline reflows.
- Right-panel section positions shift as sections expand; re-screenshot after expanding anything.
- Keep the Studio tab open and visible until the last verification is done.

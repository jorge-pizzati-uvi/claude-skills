# Failure modes — what fails silently, how it is caught, what to do

| Failure | Silent? | Caught by | Recovery |
|---|---|---|---|
| Studio tab shows login | no | `bootstrap.js` → `reason:'login'` | ask the user to sign in in the DevTools Chrome window; re-run bootstrap |
| Tab in background, tools never load | **yes** (looks like a hang) | `reason:'hidden'` / `'no-tools'` | ask to foreground; fresh tab, never reload |
| URL branch ≠ requested, or title lacks the branch (tools serve the old model) | **yes** | `reason:'branch'` | re-navigate with `?branch=`, wait, re-run |
| `main` with no branch named | — | Step 0 | ask; never default to `main` |
| Page uuid wrong (`arena` of a component, not a page) | no (`InvalidResource`) | `parse` exits | ask for a page URL |
| Long `read` dies at the ~45 s CDP timeout | no (error) | — | start-and-poll (`studio-session.md`) |
| Apostrophe / `&` inside `data-props` or text | **yes** if regexed | `html.parser` + brace-balanced fallback | — |
| Code-component default mistaken for content | **yes** | registry `defaultValue` comparison in `parse` | — |
| Registry empty (host down / other build) | **yes** | Step 2 poll → prompt | user starts/redeploys the host; cached `registry.json` from the project cache as a stopgap, flagged |
| Kit placeholder copy not in the list ("Lorem", project stand-ins) | **yes** | inventory review by eye | add to `placeholders.json`, note in project cache |
| Unknown prop key (Plasmic accepts, stores nothing) | **yes** | `plan` validation against registry | fix `fill.json` |
| Wrong value type / choice outside options | **yes** | `plan` validation | fix `fill.json` |
| Figma URL used as `src` | **yes** (works for 7 days, then 404 in production) | `plan` rejects | upload (Step 7) |
| `{{asset:…}}` unresolved | no | `payload` exits 2, names keys | upload again; field stays in gaps |
| Figma asset URL expired | no (403) | Step 5 download | re-call `get_design_context` for that frame only |
| Hidden Figma layers (accordion answers) | **yes** (absent, not empty) | `get_metadata` shows `hidden="true"`; field `missing-in-figma` | `COPY_SOURCE_URL` or user copy |
| Count mismatch (Figma 6 cards, Plasmic 3 slides) | **yes** | `plan` → `inserts` are `ask` by default | gate decision |
| Stale tpl uuid (page edited between gate and write) | partly (`InvalidResource` rows) | Step 8 re-read if >10 min; `InvalidResource` check | remap by label + component + ordinal; retry once; else gaps |
| `success:true`, nothing stored | **yes** | Step 9 `diff` + canvas snapshot sentinels | retry via alternate route (img → `insertHtml` replace; text → rich text), ≤3 rounds |
| Multi-paragraph text collapsed | **yes** | `diff` (whitespace-normalised compare still differs on lost `\n`) | `insertHtml` replace with `<p>` children |
| No Strapi admin session | no | Step 1b check (`/admin/users/me` ≠ 200) | prompt to sign in at `<origin>/admin` in the DevTools Chrome; re-check; never fall back to asking for URLs |
| Wrong Strapi origin (stage mismatch) | **yes** (uploads land on the wrong CDN) | origin from the repo env config for brand+stage, shown in the gate | user confirms at the gate |
| Folder path does not exist | no | Step 1b walk returns no leaf | gate row "will create folder …" |
| Strapi 401 mid-run (token rotated / expired), >20 MB file, duplicate names | no | owned by `figma-to-strapi` (per-file token, restartable loop, size check) | re-run Step 1b check, resume the loop |
| DevTools `evaluate_script` output too large | no (truncation) | always `filePath` for reads | — |
| A write to a section the user did not approve | — | `plan` only emits `action:'write'` for approved rows; `payload` only emits those | — |
| Human edited the page since the last run | **yes** | re-run three-way diff (`figma` / `recorded` / `current`) → `ask` | gate decision; rollback values are in the record |

| Video fill in a Figma cell | `get_design_context` emits an empty `<div>`; the cell reads as "empty" and the video is never placed | treat an asset-less image cell as a suspected video: screenshot, search Strapi videos, gate row |
| Kit placeholder images under real CDN URLs | Collage Hero ships numbered tiles with hash names; `filled` status, skipped | look at image fields marked `filled` in a contact sheet before the gate; project cache lists known cases |

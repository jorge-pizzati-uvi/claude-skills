# <Component Name>

| | |
| --- | --- |
| **Figma** | `<file key>` node `<node-id>` — <Component / Component Set>, <n> variants |
| **Plasmic** | project `<project id>` · branch `<branch>` · component `<uuid>` |
| **Studio URL** | <arena url> |
| **Style source** | <project id or "target project"> |
| **Built** | <YYYY-MM-DD> |
| **Last updated** | <YYYY-MM-DD> — <what changed> |

## Intent

<One or two sentences: what the component is, does, and who fills it. Mark it **inferred** when it
came from the Figma and layer names rather than from the caller.>

## Family conventions mirrored

<Which siblings were read and what was copied from them — slots vs props, `_components`, the list
pattern, colour handling. One line each. "No precedent" where the docs' decision tree decided.>

## Approved at gate

<The gate message as approved, with the user's edits applied. A re-run diffs against this.>

## Customization surface

Why each varying part became what it became.

| Part of the design | Verdict | Why |
| --- | --- | --- |
| <Heading> | prop `title` | Structure fixed, only the text differs. |
| <Body area> | slot `body` | Content, structure and styles all vary per use. |
| <Size> | variant group `size` | Fixed, author-controlled set. |

## Variant matrix

| Figma variant | Plasmic group / option | uuid |
| --- | --- | --- |
| `Size=M, State=Default` | `size` / `m` | `<variant uuid>` |

Groups marked for external access: <list>.

## Breakpoints

| Breakpoint | uuid | Overrides authored |
| --- | --- | --- |
| Mobile (max-width 768) | `<uuid>` | stack direction, padding, font size |

## Tokens and presets

| Figma variable / style | Plasmic | Note |
| --- | --- | --- |
| `Color/Brand/Primary` | token `color/brand-primary` | matched |
| `Shadow/Card` | preset `Card surface` | matched |
| `Color/Accent/Sand` | — | **no match** — asked, hardcoded `#E8DCC8` |

## Behaviour and motion

Source: <get_motion_context | INTERACTION_REF url | not specified>

- <What happens, and how it was reproduced: reused component / interaction + variant / deferred.>
- **Needs a code component:** <anything this skill could not express, or "none">.
- **Studio UI steps still required:** <e.g. create the base transition on `.card`, or "none">.

## Gaps

- <icon `arrow-right` → native icon placeholder, needs swapping>
- <image slots still on placehold.co>
- <anything unverified, and why>

## Divergences from the documented behaviour

<Where Plasmic's docs and the tools disagreed, and what was done. Delete if none.>

## Node map

Figma node id → Plasmic uuid. This is what makes the next run an update instead of a rebuild.

```json
{
  "<figma node id>": "<plasmic uuid>"
}
```

# Gate — <Component Name>

Read in a minute, answer in a line. Nothing below exists yet.

## 1. Shape

<single component | list container + item subcomponent>, mirroring `<sibling component>`.

| Plasmic name | role |
| --- | --- |
| `<Family>/<Name>/<Name>` | container — `itemCount` group (`_3`, `_4`), item slots exposed as `item N - <slot>` |
| `<Family>/<Name>/_components/<Item>` | the item — slots only |

## 2. Variant axes

| axis | options | provenance | proposed? |
| --- | --- | --- | --- |
| `itemCount` | `_3`, `_4` | Figma property `Columns` | yes |
| `color` | 9 options | **inferred** from the "Color List" frame | candidate — say yes to build |
| `showTag` | on/off | **inferred** from an optional layer | candidate — or a slot left empty |

Axes identical to base: <none | `_3` is the base; building it adds nothing>.

## 3. Customization surface

| part of the design | recommended | follows | alternative |
| --- | --- | --- | --- |
| title | **slot** (styled per colour on the slot-target) | `Card/Content B2` | prop `title` (text) |
| image | **slot** with an image element as default | family | prop `imageUrl` (img) |
| CTA | **slot**, default `CTAs/Link` instance | `Copy Columns` | — |
| bottom-block colour | prop `color` (colour) *or* variant group | `Copy Columns` uses a colour prop | — |

Prop and group names (fixed now; layers will be named out of their way): <list>.

## 4. Placeholders and gaps

- <images → placehold.co; icon → native icon component / named empty box; anything needing a swap>

## 5. Breakpoints

| Figma frame | screen variant | overrides |
| --- | --- | --- |
| 1920 | base | — |
| 768 | Tablet (max-width 991) | <stack direction, image size…> |

Reply with approvals or edits per section — e.g. "2: build `color`; 3: title as prop" — and I build
exactly that.

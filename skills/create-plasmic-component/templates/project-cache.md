# Project cache — <project name> (`<projectId>`)

Lives at `plasmic-docs/projects/<projectId>.md`, apart from the per-component records. Written on
first contact; later runs read this instead of re-harvesting. Refresh a section when a
lookup misses or the user asks. Updated: <YYYY-MM-DD>.

| | |
| --- | --- |
| **Style source** | `<projectId>` — <name> (<n> tokens, <n> presets) |
| **Responsive strategy** | desktop-first (`max-width`) / mobile-first (`min-width`) |
| **Preview host** | <url or "unknown — ask once"> |
| **Icon component** | <exact name or "none"> |
| **Colour primitive** | <component whose colour props are bound to its styles, e.g. `Primitives/Color Surface` — or "none; propose at gate"> |

## Breakpoints

| name | uuid | width |
| --- | --- | --- |
| Large Laptop | `…` | max-width 1919 |

## Tokens

| name | uuid | value |
| --- | --- | --- |

## Presets (mixins)

| name | uuid |
| --- | --- |

## Family conventions

Per top-level folder, what the siblings do:

| family | content | subcomponents | list pattern | colour | naming |
| --- | --- | --- | --- | --- | --- |
| *(example — replace)* `Copy/` | slots for title/body/icon/links | `<Name>/_components/<Item>` | container + `itemCount` (`_3`,`_5`,`_6`) via `displayNone`; `item N - <slot>` | separator colour prop bound `{{ $props.separatorColor }}` | `item`, `Column Item` |

## Project-specific traps

- <e.g. importer logs `Kept unresolved token reference` for every dependency token — noise, resolves at render>

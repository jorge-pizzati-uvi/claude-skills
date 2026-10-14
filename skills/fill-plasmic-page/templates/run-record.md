# Fill record — <page name>

| | |
|---|---|
| target | curacao |
| plasmicPageUrl | https://studio.plasmic.app/projects/<id>/-/<Page>?branch=<branch>&arena_type=page&arena=<uuid> |
| project | <project id> |
| branch | <branch> |
| pageUuid | <uuid> |
| figmaLink | https://www.figma.com/design/<fileKey>/<name>?node-id=<a>-<b> |
| figmaNode | <a>:<b> |
| strapiFolder | <origin> · <path> · id <NNNN> |
| copySourceUrl | <url or —> |
| built | YYYY-MM-DD |
| updated | YYYY-MM-DD — <what changed> |
| approvedGate | YYYY-MM-DD HH:MM — <row edits the user gave> |

## Result

- fields written: N
- verified ok / failed: N / N
- assets uploaded: N (skipped as already present: N)
- cost: <wall-clock>, <tool calls>, <gate round-trips>

## Gaps / needs a human

- [0] Collage Hero PLACEHOLDER: placeholder element with no component → build with create-plasmic-component
- [8] `TAp-nE9jy22Q/props.faqs`: answers missing-in-figma, taken from copy-source <url>
- …

## Approved at gate

<the gate table as approved, verbatim>

## Node map

```json
{
  "sections": [
    {
      "index": 8, "tplUuid": "XdhJ0uj3a2rT", "label": "FAQ & Closer Section", "component": "layoutSection",
      "figma": { "name": "Resort FAQs", "node": "7770:34016" },
      "fields": {
        "TAp-nE9jy22Q/props.title": { "tpl": "TAp-nE9jy22Q", "kind": "code-prop", "name": "title", "written": "Curaçao FAQs", "hash": "…", "before": null, "source": "figma:I7770:34016;1026:14784", "verified": true }
      },
      "unmapped": []
    }
  ],
  "assets": { "experiences/curacao-experiences-01.png": "https://cdn.sandals.com/libs/ui/brands/assets/uploads/curacao_experiences_01_abc123.png" }
}
```

Re-run rule: `figma ≠ recorded` and `current = recorded` → update; `current ≠ recorded` → ask
(someone edited Studio); both equal → skip. `before` values are the rollback.

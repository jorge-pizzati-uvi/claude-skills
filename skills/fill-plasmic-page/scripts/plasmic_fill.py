#!/usr/bin/env python3
"""fill-plasmic-page helper. stdlib only; run with `python3 -I`.

Subcommands
  parse    tree.json [--registry registry.json] [--placeholders placeholders.json] -o inventory.json [--md inventory.md]
  plan     inventory.json fill.json [--registry registry.json] [--record record.json] -o plan.json [--md gate.md]
  payload  plan.json [--cdn cdn-urls.json] -o writes.json
  diff     plan.json tree-after.json [--cdn cdn-urls.json] -o verify.json [--md verify.md]
  record   plan.json [--verify verify.json] [--cdn cdn-urls.json] [--meta meta.json] -o record.md

tree.json is the raw `evaluate_script` result of `PLASMIC_AI_TOOLS.read({components:[uuid]})`
(`{success, output}`) or the parsed output object. fill.json is model-authored (see SKILL.md).
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import unicodedata
from html.parser import HTMLParser

VOID_TAGS = {"img", "br", "hr", "input", "source", "track", "wbr", "meta", "link"}
TEXT_TAGS = {"div", "span", "p", "a", "h1", "h2", "h3", "h4", "h5", "h6", "li", "button", "label", "strong", "em"}
CONFIG_PROP_RE = re.compile(r"^(is|has|show|hide|enable|disable|initial|default|override|tab|active|orientation|position|background|variant|columns|width|height|size|align|rounded|vertical|horizontal|auto|drag|loop|speed|delay|resort|code|key|color|colour|id)", re.I)
TOKEN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{12}$")
DEFAULT_PLACEHOLDERS = {
    "text": ["title", "tag", "link", "enter some text", "body", "heading", "subtitle", "label", "button",
             "lorem ipsum", "placeholder", "text", "copy", "description"],
    "textPatterns": [r"^lorem ipsum", r"placeholder", r"^enter (some )?text"],
    "imagePatterns": [r"Component_Documentation_Image", r"placehold\.co", r"^$", r"^data:", r"figma\.com/api/mcp/asset"],
    "labelPatterns": [r"PLACEHOLDER"],
    "ignoreComponents": [],
}


# --------------------------------------------------------------------------- tree parsing
class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.parent = parent
        self.text = []

    @property
    def id(self):
        return self.attrs.get("id")

    @property
    def label(self):
        return self.attrs.get("data-plasmic-name") or self.attrs.get("label")

    @property
    def component(self):
        return self.attrs.get("data-plasmic-component")

    @property
    def project(self):
        return self.attrs.get("data-plasmic-project")

    def own_text(self):
        return "".join(self.text)

    def props(self):
        raw = self.attrs.get("data-props")
        if raw is None:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return _brace_balanced_json(raw)


def _brace_balanced_json(raw):
    """Fallback for a data-props value whose quoting got mangled: take the first balanced {...}."""
    start = raw.find("{")
    depth, i, in_str, esc = 0, start, False, False
    while i < len(raw) and start >= 0:
        c = raw[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start:i + 1])
                    except json.JSONDecodeError:
                        return {"__unparseable": raw[:200]}
        i += 1
    return {"__unparseable": raw[:200]}


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), self.cur)
        self.cur.children.append(node)
        if tag not in VOID_TAGS:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, dict(attrs), self.cur))

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.text.append(data)


def load_tree_input(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "output" in data:
        if not data.get("success", True):
            sys.exit(f"read failed: {data.get('error')}")
        data = json.loads(data["output"]) if isinstance(data["output"], str) else data["output"]
    results = data.get("results", [data])
    comp = next((r for r in results if r.get("__type") == "Component" or "baseVariantTplTree" in r), None)
    if comp is None or "baseVariantTplTree" not in comp:
        sys.exit("no component with baseVariantTplTree in input")
    return comp


def parse_tree(markup):
    p = TreeParser()
    p.feed(markup)
    p.close()
    top = [c for c in p.root.children if c.tag != "#root"]
    return top[0] if len(top) == 1 else p.root


# --------------------------------------------------------------------------- inventory
def norm_text(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_placeholders(path):
    ph = json.loads(json.dumps(DEFAULT_PLACEHOLDERS))
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        for k, v in user.items():
            ph[k] = sorted(set(ph.get(k, [])) | set(v))
    ph["_text"] = {t.lower() for t in ph["text"]}
    ph["_textRe"] = [re.compile(p, re.I) for p in ph["textPatterns"]]
    ph["_imgRe"] = [re.compile(p, re.I) for p in ph["imagePatterns"]]
    ph["_labelRe"] = [re.compile(p, re.I) for p in ph["labelPatterns"]]
    ph["_ignore"] = {c.lower() for c in ph.get("ignoreComponents", [])}
    return ph


def text_status(value, ph):
    v = norm_text(value)
    if v.startswith("{{"):
        return "bound"  # dynamic expression; not ours to touch
    if not v or v.lower() in ph["_text"] or any(r.search(v) for r in ph["_textRe"]):
        return "empty"
    return "filled"


def image_status(src, ph):
    s = (src or "").strip()
    if any(r.search(s) for r in ph["_imgRe"]):
        return "empty"
    return "filled"


def load_registry(path):
    """registry.json: list of {name, props:{propName:{type, defaultValue, itemType...}}} or the raw
    __PlasmicComponentRegistry dump ([{meta:{name, props}}])."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "components" in data:
        data = data["components"]
    out = {}
    for entry in data:
        meta = entry.get("meta", entry)
        name = meta.get("name")
        if name:
            out[name] = meta.get("props", {})
    return out


def registry_lookup(registry, comp_name):
    """Studio lower-camels registered names (FaqListing -> faqListing)."""
    if comp_name in registry:
        return registry[comp_name]
    for k, v in registry.items():
        if k[:1].lower() + k[1:] == comp_name or k.lower() == comp_name.lower():
            return v
    return None


def is_text_leaf(node):
    return node.tag in TEXT_TAGS and not any(c.tag != "br" for c in node.children) and norm_text(node.own_text()) != "" or (
        node.tag in TEXT_TAGS and not node.children and node.id)


def walk(node):
    yield node
    for c in node.children:
        yield from walk(c)


def path_for(node, stop):
    """Readable location: instance labels/components and slot names, minus layout noise."""
    parts = []
    n = node
    while n is not None and n is not stop:
        if n.tag == "plasmic-component":
            name = n.label or n.component or "?"
            if name not in ("layoutContainer", "layoutSection"):
                parts.append(name)
        elif n.tag == "slot":
            sn = n.attrs.get("name", "?")
            if sn != "children":
                parts.append("slot:" + sn)
        n = n.parent
    return "/".join(reversed(parts))


def is_config_prop(name, value):
    if not isinstance(value, str):
        return True
    if TOKEN_ID_RE.match(value) and " " not in value:
        return True
    return bool(CONFIG_PROP_RE.match(name))


def build_inventory(comp, registry, ph):
    root = parse_tree(comp["baseVariantTplTree"])
    inv = {
        "page": {"uuid": comp.get("uuid"), "name": comp.get("name"), "path": (comp.get("pageMeta") or {}).get("path")},
        "sections": [],
    }
    for idx, sec in enumerate(root.children):
        section = {
            "index": idx,
            "tplUuid": sec.id,
            "label": sec.label,
            "component": sec.component,
            "project": sec.project,
            "instances": [],
            "fields": [],
            "status": None,
        }
        if sec.label and any(r.search(sec.label) for r in ph["_labelRe"]) and not sec.children and not sec.component:
            section["status"] = "unfillable"
            section["note"] = "placeholder element with no component"
            inv["sections"].append(section)
            continue
        for n in walk(sec):
            if n.tag == "plasmic-component":
                inst = {"tplUuid": n.id, "component": n.component, "project": n.project, "label": n.label,
                        "path": path_for(n, sec), "props": n.props()}
                reg = registry_lookup(registry, n.component) if not n.project else None
                inst["kind"] = "code" if reg is not None else ("kit" if n.project else "local")
                section["instances"].append(inst)
                if (n.component or "").lower() in ph["_ignore"]:
                    inst["ignored"] = True
                    continue  # configured, not content (e.g. a booking widget)
                # props as fields (code components: full registry schema; kit instances: whatever is set)
                if reg is not None:
                    for pname, pmeta in reg.items():
                        if not isinstance(pmeta, dict):
                            continue
                        ptype = pmeta.get("type")
                        if ptype not in ("string", "richText", "imageUrl", "array", "object", "href", "dateString"):
                            continue  # choice/boolean/number/color/slot/handler = configuration, not content
                        if pmeta.get("advanced") or pmeta.get("hidden") is True or CONFIG_PROP_RE.match(pname):
                            continue
                        cur = inst["props"].get(pname)
                        default = pmeta.get("defaultValue")
                        if cur is None:
                            status, note = "empty", "unset (renders registered default)"
                        elif default is not None and cur == default:
                            status, note = "empty", "equals registered default"
                        else:
                            status, note = "filled", None
                        section["fields"].append({
                            "id": f"{n.id}/props.{pname}", "tplUuid": n.id, "kind": "code-prop", "name": pname,
                            "propType": ptype, "path": inst["path"], "current": cur, "default": default,
                            "status": status, "note": note})
                else:
                    for pname, cur in inst["props"].items():
                        if is_config_prop(pname, cur):
                            continue  # layout/config, not content
                        if isinstance(cur, str) and cur.strip() == "":
                            status = "optional-empty"  # e.g. an unset linkHref on a marker
                        elif re.match(r"^https?://", cur) or re.search(r"image|img|src|icon|url|video", pname, re.I):
                            status = image_status(cur, ph)
                        else:
                            status = text_status(cur, ph)
                        section["fields"].append({
                            "id": f"{n.id}/props.{pname}", "tplUuid": n.id, "kind": "instance-prop", "name": pname,
                            "path": inst["path"], "current": cur, "status": status})
            elif n.tag == "img":
                src = n.attrs.get("src", "")
                section["fields"].append({
                    "id": f"{n.id}/attr.src", "tplUuid": n.id, "kind": "img-src", "name": "src",
                    "path": path_for(n, sec), "label": n.label, "current": src, "alt": n.attrs.get("alt"),
                    "style": n.attrs.get("style"), "status": image_status(src, ph)})
            elif n.tag in TEXT_TAGS and n.id and not any(c.tag not in ("br",) for c in n.children):
                txt = n.own_text()
                in_slot = n.parent is not None and n.parent.tag == "slot"
                if in_slot or norm_text(txt):
                    section["fields"].append({
                        "id": f"{n.id}/text", "tplUuid": n.id, "kind": "text", "name": "text",
                        "path": path_for(n, sec), "label": n.label, "tag": n.tag, "current": txt,
                        "status": text_status(txt, ph)})
        sts = {f["status"] for f in section["fields"] if f["status"] not in ("optional-empty", "bound")}
        if not section["fields"]:
            section["status"] = "no-fields"
        elif sts == {"empty"}:
            section["status"] = "empty"
        elif "empty" in sts:
            section["status"] = "partial"
        else:
            section["status"] = "filled"
        inv["sections"].append(section)
    return inv


def inventory_md(inv):
    out = [f"# Inventory — {inv['page']['name']} ({inv['page']['uuid']}) path {inv['page']['path']}", ""]
    for s in inv["sections"]:
        head = f"## [{s['index']}] {s['label'] or s['component'] or s['tplUuid']} — {s['status']}  `{s['tplUuid']}`"
        out.append(head)
        if s.get("note"):
            out.append(f"_{s['note']}_")
        for f in s["fields"]:
            cur = f["current"]
            if isinstance(cur, (dict, list)):
                cur = json.dumps(cur, ensure_ascii=False)
            cur = norm_text(cur)
            if len(cur) > 90:
                cur = cur[:87] + "…"
            out.append(f"- `{f['id']}` {f['kind']} [{f['status']}] {f['path']}: {cur!r}" + (f" ({f['note']})" if f.get("note") else ""))
        out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------- plan
def validate_prop_value(pmeta, value, where, problems):
    """Recursively check object/array prop values against the registry schema (unknown keys are
    accepted silently by Plasmic, so they must be caught here)."""
    if not isinstance(pmeta, dict):
        return
    ptype = pmeta.get("type")
    if ptype == "array":
        if not isinstance(value, list):
            problems.append(f"{where}: expected array, got {type(value).__name__}")
            return
        item = pmeta.get("itemType") or {}
        for i, v in enumerate(value):
            validate_prop_value(item, v, f"{where}[{i}]", problems)
    elif ptype == "object":
        if not isinstance(value, dict):
            problems.append(f"{where}: expected object, got {type(value).__name__}")
            return
        fields = pmeta.get("fields") or {}
        if fields:
            for k, v in value.items():
                if k not in fields:
                    problems.append(f"{where}.{k}: unknown key (allowed: {', '.join(fields)})")
                else:
                    validate_prop_value(fields[k], v, f"{where}.{k}", problems)
    elif ptype == "choice":
        opts = pmeta.get("options") or []
        vals = [o.get("value") if isinstance(o, dict) else o for o in opts]
        if vals and value not in vals and not (isinstance(value, str) and value.startswith("{{")):
            problems.append(f"{where}: {value!r} not in choices {vals}")
    elif ptype == "boolean" and not isinstance(value, bool):
        problems.append(f"{where}: expected boolean")
    elif ptype == "number" and not isinstance(value, (int, float)):
        problems.append(f"{where}: expected number")
    elif ptype in ("imageUrl",) and isinstance(value, str) and "figma.com/api/mcp/asset" in value:
        problems.append(f"{where}: Figma temp asset URL used as runtime src")


def build_plan(inv, fill, registry, record):
    fields = {}
    for s in inv["sections"]:
        for f in s["fields"]:
            fields[f["id"]] = (s, f)
    sections_by_uuid = {s["tplUuid"]: s for s in inv["sections"]}
    recorded = {}
    if record:
        for sec in record.get("sections", []):
            for fid, fr in (sec.get("fields") or {}).items():
                recorded[fid] = fr
    plan = {"page": inv["page"], "sections": [], "rejected": [], "assets": fill.get("assets", {}),
            "notes": fill.get("notes", [])}
    per_section = {}
    for w in fill.get("writes", []):
        fid = w.get("field")
        if fid not in fields:
            plan["rejected"].append({"field": fid, "reason": "unknown field id (re-run parse; uuids may be stale)"})
            continue
        s, f = fields[fid]
        value = w.get("value")
        problems = []
        if f["kind"] == "code-prop":
            inst = next((i for i in s["instances"] if i["tplUuid"] == f["tplUuid"]), None)
            reg = registry_lookup(registry, inst["component"]) if inst else None
            pmeta = (reg or {}).get(f["name"])
            if pmeta is None:
                problems.append("prop not in registry")
            else:
                validate_prop_value(pmeta, value, f["name"], problems)
        elif f["kind"] == "text" and not isinstance(value, str):
            problems.append("text value must be a string")
        elif f["kind"] == "img-src" and isinstance(value, str) and "figma.com/api/mcp/asset" in value:
            problems.append("Figma temp asset URL used as runtime src")
        if problems:
            plan["rejected"].append({"field": fid, "reason": "; ".join(problems)})
            continue
        # decision
        cur_norm = _norm_value(f["current"])
        new_norm = _norm_value(value)
        rec = recorded.get(fid)
        if new_norm == cur_norm:
            action, reason = "skip", "already matches"
        elif f["status"] == "bound":
            action, reason = "ask", "bound to a dynamic expression"
        elif f["status"] == "empty":
            action, reason = "write", "empty"
        elif rec and _norm_value(rec.get("written")) == cur_norm:
            action, reason = "write", "update: source changed since last run"
        elif rec and _norm_value(rec.get("written")) != cur_norm and w.get("overwrite"):
            action, reason = "write", "overwrite human edit (explicit)"
        elif rec and _norm_value(rec.get("written")) != cur_norm:
            action, reason = "ask", "conflict: edited in Studio since last run"
        elif w.get("overwrite"):
            action, reason = "write", "overwrite (explicit)"
        else:
            action, reason = "ask", "filled-differs: has content that differs from source"
        entry = {"field": fid, "tplUuid": f["tplUuid"], "kind": f["kind"], "name": f["name"], "path": f["path"],
                 "before": f["current"], "value": value, "source": w.get("source"), "action": action,
                 "reason": reason, "status": f["status"]}
        if f["kind"] == "img-src":
            entry["alt"] = w.get("alt") or f.get("alt")
            entry["style"] = f.get("style")
            entry["label"] = f.get("label")
        per_section.setdefault(s["tplUuid"], []).append(entry)
    inserts_by_section = {}
    for ins in fill.get("inserts", []):
        sec = sections_by_uuid.get(ins.get("section"))
        if sec is None:
            plan["rejected"].append({"field": f"insert@{ins.get('section')}", "reason": "unknown section uuid"})
            continue
        known = {sec["tplUuid"]} | {i["tplUuid"] for i in sec["instances"]} | {f["tplUuid"] for f in sec["fields"]}
        if ins.get("target") not in known:
            plan["rejected"].append({"field": f"insert@{ins.get('target')}", "reason": "target uuid not in that section"})
            continue
        if not ins.get("html") or "figma.com/api/mcp/asset" in ins["html"]:
            plan["rejected"].append({"field": f"insert@{ins.get('target')}", "reason": "html missing or carries a Figma temp URL"})
            continue
        before = sum(1 for i in sec["instances"] if i["component"] == ins.get("component")) if ins.get("component") else None
        inserts_by_section.setdefault(sec["tplUuid"], []).append({
            "target": ins["target"], "insertRelLoc": ins.get("insertRelLoc", "append"), "html": ins["html"],
            "component": ins.get("component"), "countBefore": before, "expectAdded": ins.get("count", 1),
            "source": ins.get("source"), "action": "ask" if not ins.get("approved") else "write",
            "reason": "structure change: adds instances to a slot list" if not ins.get("approved") else "approved"})
    for s in inv["sections"]:
        writes = per_section.get(s["tplUuid"], [])
        plan["sections"].append({
            "index": s["index"], "tplUuid": s["tplUuid"], "label": s["label"], "component": s["component"],
            "status": s["status"], "note": s.get("note"), "figma": (fill.get("sections") or {}).get(s["tplUuid"]),
            "writes": writes,
            "inserts": inserts_by_section.get(s["tplUuid"], []),
            "unmapped": [f["id"] for f in s["fields"] if f["status"] == "empty" and f["id"] not in {w["field"] for w in writes}],
        })
    return plan


def _norm_value(v):
    if isinstance(v, str):
        return norm_text(v)
    if isinstance(v, (dict, list)):
        return json.dumps(_norm_deep(v), sort_keys=True, ensure_ascii=False)
    return v


def _norm_deep(v):
    if isinstance(v, str):
        return norm_text(v)
    if isinstance(v, dict):
        return {k: _norm_deep(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm_deep(x) for x in v]
    return v


def gate_md(plan):
    rows = ["| # | Plasmic section | status | Figma source | writes (text/props/img) | assets | issues | action |",
            "|---|---|---|---|---|---|---|---|"]
    appendix = []
    for s in plan["sections"]:
        w = s["writes"]
        nt = sum(1 for x in w if x["kind"] == "text" and x["action"] == "write")
        npr = sum(1 for x in w if x["kind"] in ("code-prop", "instance-prop") and x["action"] == "write")
        ni = sum(1 for x in w if x["kind"] == "img-src" and x["action"] == "write")
        asks = [x for x in w if x["action"] == "ask"]
        for ins in s.get("inserts", []):
            tag = "ask" if ins["action"] == "ask" else "write"
            issues_ins = f"insert +{ins['expectAdded']} {ins.get('component') or 'element(s)'} ({tag})"
            s.setdefault("_issues", []).append(issues_ins)
        assets = sorted({m.group(1) for x in w for m in re.finditer(r"\{\{asset:([^}]+)\}\}", json.dumps(x["value"]))})
        issues = list(s.get("_issues", []))
        if s["status"] == "unfillable":
            issues.append("unfillable: " + (s.get("note") or ""))
        if s["unmapped"]:
            issues.append(f"{len(s['unmapped'])} empty field(s) without source")
        for a in asks:
            issues.append(f"ask `{a['field']}`: {a['reason']}")
            appendix.append(f"- `{a['field']}`\n  - before: {json.dumps(a['before'], ensure_ascii=False)[:300]}\n  - after: {json.dumps(a['value'], ensure_ascii=False)[:300]}")
        fig = s.get("figma") or {}
        figtxt = f"{fig.get('name','')} `{fig.get('node','')}`".strip() if fig else "—"
        pending_ins = [i for i in s.get("inserts", []) if i["action"] == "ask"]
        action = "skip" if (not w or all(x["action"] == "skip" for x in w)) and not s.get("inserts") else ("ask" if asks or pending_ins else "write")
        if s["status"] == "unfillable":
            action = "report"
        name = s["label"] or s["component"] or s["tplUuid"]
        rows.append(f"| {s['index']} | {name} `{s['tplUuid'][:6]}` | {s['status']} | {figtxt} | {nt}/{npr}/{ni} | {len(assets)} | {'; '.join(issues) or '—'} | {action} |")
    out = ["# Gate — " + (plan["page"].get("name") or ""), "", *rows, ""]
    if plan["rejected"]:
        out += ["## Rejected writes (fix fill.json)", *[f"- `{r['field']}`: {r['reason']}" for r in plan["rejected"]], ""]
    if appendix:
        out += ["## Conflicts (before → after)", *appendix, ""]
    out += ["Reply with row edits, e.g. `3: skip`, `5: overwrite`, `7: use live URL`. Nothing is written before approval."]
    return "\n".join(out)


# --------------------------------------------------------------------------- payload
def substitute_assets(value, cdn, missing):
    def sub(s):
        def rep(m):
            key = m.group(1)
            url = cdn.get(key)
            if not url:
                missing.add(key)
                return m.group(0)
            return url
        return re.sub(r"\{\{asset:([^}]+)\}\}", rep, s)
    if isinstance(value, str):
        return sub(value)
    if isinstance(value, list):
        return [substitute_assets(v, cdn, missing) for v in value]
    if isinstance(value, dict):
        return {k: substitute_assets(v, cdn, missing) for k, v in value.items()}
    return value


def load_cdn(path):
    """Accepts cdn-urls.json from figma-to-strapi ({files:{...}}) or a flat {key:url} map.
    Keys are matched by exact name, then by basename without extension."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    files = data.get("files", data) if isinstance(data, dict) else {}
    out = dict(files)
    for k, v in list(files.items()):
        base = os.path.splitext(os.path.basename(k))[0]
        out.setdefault(base, v)
        out.setdefault(os.path.basename(k), v)
    return out


def resolve_assets(plan, cdn):
    """{{asset:key}} → plan.assets[key] (local file) → cdn-urls.json entry (by path, basename, or key)."""
    resolved = dict(cdn)
    for key, local in (plan.get("assets") or {}).items():
        if not isinstance(local, str):
            continue
        for cand in (local, local.split("assets/")[-1], os.path.basename(local), os.path.splitext(os.path.basename(local))[0]):
            if cand in cdn:
                resolved[key] = cdn[cand]
                break
        if local.startswith("http"):
            resolved.setdefault(key, local)  # an asset that already lives on the CDN (record re-use)
    return resolved


def build_payload(plan, cdn):
    cdn = resolve_assets(plan, cdn)
    writes, missing = [], set()
    for s in plan["sections"]:
        for ins in s.get("inserts", []):
            if ins["action"] != "write":
                continue
            html_s = substitute_assets(ins["html"], cdn, missing)
            writes.append({"section": s["index"], "label": s["label"], "tool": "insertHtml",
                           "input": {"componentUuid": plan["page"]["uuid"], "tplUuid": ins["target"],
                                     "insertRelLoc": ins["insertRelLoc"], "html": html_s},
                           "note": "insertHtml schema: componentUuid, tplUuid, insertRelLoc, html"})
        changes = []
        for w in s["writes"]:
            if w["action"] != "write":
                continue
            value = substitute_assets(w["value"], cdn, missing)
            if "{{asset:" in json.dumps(value):
                w["action"] = "unresolved-asset"  # left unwritten; reported by payload's exit code
                continue
            if w["kind"] == "text":
                changes.append({"tplUuid": w["tplUuid"], "text": value})
            elif w["kind"] == "img-src":
                # `src` is a reserved attribute: changeElement.props ignores it. Re-emit the element.
                alt = w.get("alt") or w.get("before_alt")
                style = w.get("style") or ""
                attrs = [f'style="{html.escape(style, quote=True)}"' if style else "", 'loading="lazy"',
                         f'alt="{html.escape(alt, quote=True)}"' if alt else "", f'src="{html.escape(value, quote=True)}"']
                writes.append({"section": s["index"], "label": s["label"], "tool": "insertHtml", "field": w["field"],
                               "input": {"componentUuid": plan["page"]["uuid"], "tplUuid": w["tplUuid"], "insertRelLoc": "replace",
                                         "html": "<img " + " ".join(a for a in attrs if a) + ">"},
                               "note": "replace mints a new tpl uuid; verify locates the image by path"})
            else:
                # merge several props on one instance into one change
                existing = next((c for c in changes if c["tplUuid"] == w["tplUuid"] and "props" in c and "text" not in c), None)
                if existing is None:
                    existing = {"tplUuid": w["tplUuid"], "props": {}}
                    changes.append(existing)
                existing["props"][w["name"]] = value
        if changes:
            writes.append({"section": s["index"], "label": s["label"], "tool": "changeElement",
                           "input": {"componentUuid": plan["page"]["uuid"], "changes": changes}})
    skipped = [w["field"] for s in plan["sections"] for w in s["writes"] if w["action"] == "unresolved-asset"]
    return {"writes": writes, "missingAssets": sorted(missing), "unwrittenFields": skipped}


# --------------------------------------------------------------------------- diff
def build_verify(plan, comp_after, cdn, registry, ph):
    cdn = resolve_assets(plan, cdn)
    inv2 = build_inventory(comp_after, registry, ph)
    actual = {f["id"]: f for s in inv2["sections"] for f in s["fields"]}
    results, ok, fail = [], 0, 0
    sec_after = {s["tplUuid"]: s for s in inv2["sections"]}
    for s in plan["sections"]:
        for ins in s.get("inserts", []):
            if ins["action"] != "write" or not ins.get("component"):
                continue
            after = sec_after.get(s["tplUuid"])
            n_after = sum(1 for i in after["instances"] if i["component"] == ins["component"]) if after else 0
            want = (ins["countBefore"] or 0) + ins["expectAdded"]
            same = n_after >= want
            results.append({"field": f"insert@{ins['target']}", "ok": same, "expected": want, "actual": n_after,
                            "kind": "insert", "name": ins["component"], "tplUuid": ins["target"],
                            "reason": None if same else "instance count did not grow as planned"})
            ok += same
            fail += (not same)
        for w in s["writes"]:
            if w["action"] != "write":
                continue
            expected = substitute_assets(w["value"], cdn, set())
            if "{{asset:" in json.dumps(expected):
                continue  # never written (unresolved asset); reported in gaps, not as a failure
            got = actual.get(w["field"])
            if got is None:
                after = sec_after.get(s["tplUuid"])
                cands = [f for f in (after["fields"] if after else []) if f["kind"] == w["kind"] and f["path"] == w["path"]]
                got = cands[0] if len(cands) == 1 else None
                if got is None:
                    results.append({"field": w["field"], "ok": False, "reason": "field not found after write (uuid changed and path not unique)"})
                    fail += 1
                    continue
                w["tplUuidAfter"] = got["tplUuid"]
            same = _norm_value(got["current"]) == _norm_value(expected)
            results.append({"field": w["field"], "ok": same, "expected": expected, "actual": got["current"],
                            "tplUuid": got["tplUuid"], "kind": w["kind"], "name": w["name"]})
            ok += same
            fail += (not same)
    return {"ok": ok, "failed": fail, "results": results}


def verify_md(v):
    out = [f"# Verify — {v['ok']} ok, {v['failed']} failed", ""]
    for r in v["results"]:
        if r["ok"]:
            out.append(f"- ✅ `{r['field']}`")
        else:
            out.append(f"- ❌ `{r['field']}` — {r.get('reason','mismatch')}\n  - expected: {json.dumps(r.get('expected'), ensure_ascii=False)[:300]}\n  - actual: {json.dumps(r.get('actual'), ensure_ascii=False)[:300]}")
    return "\n".join(out)


# --------------------------------------------------------------------------- record
def build_record(plan, verify, cdn, meta):
    cdn = resolve_assets(plan, cdn)
    vmap = {r["field"]: r for r in (verify or {}).get("results", [])}
    rec = {"sections": [], "assets": {}, "meta": meta or {}}
    for s in plan["sections"]:
        fields = {}
        for w in s["writes"]:
            if w["action"] != "write":
                continue
            value = substitute_assets(w["value"], cdn, set())
            vr = vmap.get(w["field"])
            fields[w["field"]] = {"tpl": (vr or {}).get("tplUuid") or w["tplUuid"], "kind": w["kind"], "name": w["name"], "written": value,
                                  "hash": hashlib.sha1(json.dumps(_norm_deep(value), sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12],
                                  "before": w["before"], "source": w.get("source"),
                                  "verified": (vr or {}).get("ok")}
        rec["sections"].append({"index": s["index"], "tplUuid": s["tplUuid"], "label": s["label"],
                                "component": s["component"], "status": s["status"],
                                "figma": s.get("figma"), "fields": fields,
                                "unmapped": s["unmapped"], "note": s.get("note")})
    for k, v in (cdn or {}).items():
        if "/" in k or "." in k:
            rec["assets"][k] = v
    return rec


def record_md(rec, plan, verify):
    m = rec["meta"]
    lines = ["# Fill record — " + (plan["page"].get("name") or ""), "",
             "| | |", "|---|---|"]
    for k in ("target", "plasmicPageUrl", "project", "branch", "pageUuid", "figmaLink", "figmaNode",
              "strapiFolder", "copySourceUrl", "built", "updated", "approvedGate"):
        if m.get(k):
            lines.append(f"| {k} | {m[k]} |")
    lines += ["", "## Result", "",
              f"- fields written: {sum(len(s['fields']) for s in rec['sections'])}",
              f"- verified ok / failed: {(verify or {}).get('ok', '?')} / {(verify or {}).get('failed', '?')}", ""]
    gaps = []
    for s in rec["sections"]:
        if s["status"] == "unfillable":
            gaps.append(f"- [{s['index']}] {s['label'] or s['component']}: {s.get('note')}")
        for fid in s["unmapped"]:
            gaps.append(f"- [{s['index']}] `{fid}`: empty, no source")
    for s in plan["sections"]:
        for w in s["writes"]:
            if w["action"] == "ask":
                gaps.append(f"- [{s['index']}] `{w['field']}`: {w['reason']} (not written)")
    if plan.get("rejected"):
        gaps += [f"- rejected `{r['field']}`: {r['reason']}" for r in plan["rejected"]]
    lines += ["## Gaps / needs a human", "", *(gaps or ["- none"]), ""]
    if m.get("approvedGateText"):
        lines += ["## Approved at gate", "", m["approvedGateText"], ""]
    lines += ["## Node map", "", "```json", json.dumps({k: v for k, v in rec.items() if k != "meta"}, indent=1, ensure_ascii=False), "```", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- cli
def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _dump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def _write(text, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse")
    p.add_argument("tree")
    p.add_argument("--registry")
    p.add_argument("--placeholders")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--md")

    p = sub.add_parser("plan")
    p.add_argument("inventory")
    p.add_argument("fill")
    p.add_argument("--registry")
    p.add_argument("--record")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--md")

    p = sub.add_parser("payload")
    p.add_argument("plan")
    p.add_argument("--cdn")
    p.add_argument("-o", "--out", required=True)

    p = sub.add_parser("diff")
    p.add_argument("plan")
    p.add_argument("tree_after")
    p.add_argument("--cdn")
    p.add_argument("--registry")
    p.add_argument("--placeholders")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--md")

    p = sub.add_parser("record")
    p.add_argument("plan")
    p.add_argument("--verify")
    p.add_argument("--cdn")
    p.add_argument("--meta")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--json")

    a = ap.parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    default_ph = os.path.join(here, "..", "references", "placeholders.json")

    if a.cmd == "parse":
        ph = load_placeholders(a.placeholders or default_ph)
        inv = build_inventory(load_tree_input(a.tree), load_registry(a.registry), ph)
        _dump(inv, a.out)
        if a.md:
            _write(inventory_md(inv), a.md)
        print(f"sections={len(inv['sections'])} fields={sum(len(s['fields']) for s in inv['sections'])}")
    elif a.cmd == "plan":
        record = None
        if a.record and os.path.exists(a.record):
            record = _load(a.record)
        plan = build_plan(_load(a.inventory), _load(a.fill), load_registry(a.registry), record)
        _dump(plan, a.out)
        if a.md:
            _write(gate_md(plan), a.md)
        n = sum(1 for s in plan["sections"] for w in s["writes"] if w["action"] == "write")
        k = sum(1 for s in plan["sections"] for w in s["writes"] if w["action"] == "ask")
        print(f"writes={n} ask={k} rejected={len(plan['rejected'])}")
    elif a.cmd == "payload":
        out = build_payload(_load(a.plan), load_cdn(a.cdn))
        _dump(out, a.out)
        print(f"calls={len(out['writes'])} missingAssets={out['missingAssets']}")
        if out["missingAssets"]:
            sys.exit(2)
    elif a.cmd == "diff":
        ph = load_placeholders(a.placeholders or default_ph)
        v = build_verify(_load(a.plan), load_tree_input(a.tree_after), load_cdn(a.cdn), load_registry(a.registry), ph)
        _dump(v, a.out)
        if a.md:
            _write(verify_md(v), a.md)
        print(f"ok={v['ok']} failed={v['failed']}")
        if v["failed"]:
            sys.exit(1)
    elif a.cmd == "record":
        plan = _load(a.plan)
        verify = _load(a.verify) if a.verify and os.path.exists(a.verify) else None
        meta = _load(a.meta) if a.meta and os.path.exists(a.meta) else {}
        rec = build_record(plan, verify, load_cdn(a.cdn), meta)
        _write(record_md(rec, plan, verify), a.out)
        if a.json:
            _dump(rec, a.json)
        print(f"record written: {a.out}")


if __name__ == "__main__":
    main()

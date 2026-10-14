# Strapi: detect the session, resolve the folder

Assets reach Plasmic as CDN URLs minted by Strapi's upload provider. The skill never asks the user
for those URLs; it asks for a **sign-in** when there is none and for a **folder** when there is one.
Everything below runs in the Chrome DevTools profile, which must therefore hold the admin session.

## 1. Which Strapi

The admin origin depends on brand and stage. Resolve in this order and cache the answer in
`plasmic-docs/projects/<projectId>.md` (`strapiAdminOrigin`):

1. The project cache, if it already names one.
2. The repository's environment config: the CMS public URL for the brand and the stage whose CDN
   the page is meant to use (the production stage for a page that will go live; the development
   stage for throwaway content). Read `environment.config.js` for the defaults and `.env*` for
   overrides (`NEXT_PUBLIC_CMS_URL`). Strip the path; the admin is `<origin>/admin`.
3. Ask once: "Which Strapi admin should receive the images? (origin, e.g. https://api.<brand>.com)".

Say the origin in the gate table header so a stage mismatch is visible before anything uploads.

## 2. Is the user signed in?

Open (or reuse, via `list_pages`) `<origin>/admin` — background is fine, it is a plain SPA — and
run with `waitForStableDom: false`:

```js
async () => {
  const pick = () => {
    for (const store of [localStorage, sessionStorage]) {
      const v = store.getItem("jwtToken");
      if (v) { try { return JSON.parse(v); } catch { return v; } }
    }
    const m = document.cookie.match(/(?:^|; )jwtToken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  };
  const token = pick();
  if (!token) return { signedIn: false, reason: "no token in storage or cookie", origin: location.origin };
  const r = await fetch("/admin/users/me", { headers: { Authorization: "Bearer " + token } });
  if (r.status !== 200) return { signedIn: false, reason: "token rejected (" + r.status + ")", origin: location.origin };
  const me = await r.json();
  return { signedIn: true, user: (me.data || me).email || (me.data || me).username, origin: location.origin };
};
```

Never return, print or store the token itself. `signedIn:false` → one prompt: *"Sign in to Strapi at
`<origin>/admin` in the DevTools Chrome window, then say go."* End the turn; re-run on resume.
Strapi admin tokens rotate during long runs — `figma-to-strapi` re-reads per file; if its loop
reports repeated 401s, re-run this check (the session has expired, not rotated) and prompt again.

## 3. From folder path to folder id

`STRAPI_FOLDER` may be a link (`…/admin/plugins/upload?…&folder=NNNN` → id is `NNNN`, done) or a
path (`Destinations/Curacao`). Resolve a path in the admin tab:

```js
async (path) => {
  const token = (() => { for (const s of [localStorage, sessionStorage]) { const v = s.getItem("jwtToken"); if (v) { try { return JSON.parse(v); } catch { return v; } } } const m = document.cookie.match(/(?:^|; )jwtToken=([^;]+)/); return m ? decodeURIComponent(m[1]) : null; })();
  const H = { Authorization: "Bearer " + token };
  const list = async (parentId) => {
    const q = parentId == null ? "filters[$and][0][parent][id][$null]=true" : "filters[$and][0][parent][id]=" + parentId;
    const r = await fetch("/upload/folders?" + q + "&pagination[pageSize]=100", { headers: H });
    const j = await r.json();
    return j.data || j.results || [];
  };
  let parent = null, trail = [];
  for (const seg of path.split("/").map(s => s.trim()).filter(Boolean)) {
    const kids = await list(parent);
    const hit = kids.find(f => f.name.toLowerCase() === seg.toLowerCase());
    if (!hit) return { ok: false, resolved: trail, missing: seg, parentId: parent };
    trail.push({ name: hit.name, id: hit.id });
    parent = hit.id;
  }
  return { ok: true, id: parent, trail };
};
```

Pass `path` through `evaluate_script`'s `args` or inline it. `ok:false` → the gate gets a row
"will create folder `<missing>` under `<resolved path>`"; the folder is created only after approval
(`POST /upload/folders { name, parent }`, or let `figma-to-strapi` create the section subfolders
under it). Folder names match case-insensitively; never create a near-duplicate.

The folder link to hand `figma-to-strapi` is `<origin>/admin/plugins/upload?folder=<id>`.

## 4. What this skill does not do

- Sign in, create accounts, or ask for passwords.
- Upload through Studio's own image picker (bypasses CDN optimisation).
- Accept image URLs typed by the user as a substitute for the upload: a URL that is not on the
  brand CDN is outside cache rules and invalidation.

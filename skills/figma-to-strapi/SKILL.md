---
name: figma-to-strapi
description: Export images from a Figma frame and upload them into a Strapi Media Library folder, returning a cdn-urls.json that maps each local file to its final CDN URL. Use when asked to get design assets out of Figma and into Strapi, to refresh a page's imagery from a design file, or to replace placeholder images with real uploaded ones.
---

# Figma to Strapi

Export every image used in a Figma frame, organised one subfolder per design section, upload them to a
Strapi Media Library folder replicating that structure, and produce `cdn-urls.json` mapping each local
file to its final CDN URL.

Images only. Never modify a Plasmic project, a code repository, or Strapi content types as part of
this skill.

## Inputs

Ask for whatever the request did not supply:

- `FIGMA_LINK` — a `figma.com/design/...` link to the frame or page to export. Must contain `node-id`.
- `STRAPI_FOLDER_LINK` — the Media Library folder that receives the images, e.g.
  `https://<strapi-host>/admin/plugins/upload?...&folder=NNNN`. The `folder=NNNN` query parameter is
  the parent folder id; the API base is that link's own origin. Never hardcode a host or a folder id.
- `SET_NAME` — short kebab-case name for the set, e.g. `bahamas`.
- `OUTPUT_DIR` — defaults to `~/Downloads/<SET_NAME>-images/`. Create it.

## Requirements

- Figma MCP tools: `get_metadata`, `get_design_context`, `get_screenshot`.
- Chrome with the Strapi admin **already open and signed in**. Use that tab. Never sign in, never
  create an account, never ask for a password. If no authenticated tab exists, stop and say so.
- Shell access for `curl`, `file`, and `magick` (ImageMagick).
- TLS certs for `localhost`. Reuse the project's `localhost.pem` / `localhost-key.pem` if present,
  otherwise run `mkcert localhost`.

**Credential rule:** the admin session token is the `jwtToken` cookie, read inside the page and used as
`Authorization: Bearer <token>`. Never print it, log it, echo it into a shell command, or write it to
any file.

## Step 1 — Inventory the design

1. `get_metadata` on the `FIGMA_LINK` node to list the top-level section frames and their names.
2. For each section frame, `get_design_context` with `excludeScreenshot: true`. Collect every image
   asset URL (Figma serves them from `figma.com/api/mcp/asset/...`, valid about 7 days) together with
   the element it belongs to: layer name, card or slide index.
3. Derive a section slug from each frame name, e.g. `hero`, `map`, `experiences`, `content-cards`,
   `rooms`, `collage`, `weddings`. Decide it yourself; ask only when a frame name is genuinely
   ambiguous.

## Step 2 — Download and name

1. Save each asset to `OUTPUT_DIR/<section>/<SET_NAME>-<section>-<nn>.<ext>`, where `nn` is a 2-digit
   index within the section, ordered top-to-bottom and left-to-right as in Figma. Use `curl -L`.
2. Figma asset URLs carry no extension. After download, run `file --mime-type` and rename to the real
   extension: `png`, `jpg`, `svg`, `webp`.
3. Download a repeated asset once and record every place it is used.
4. Strapi rejects uploads over about 20MB. Convert anything larger with
   `magick in.png -quality 90 out.jpg`, delete the original, and update the manifest.
5. Write `OUTPUT_DIR/manifest.json`, one entry per file: the Figma asset id, the layer name, and a
   short description of what the image is for.

## Step 3 — Create the folder structure

API base is the admin origin. Endpoints:

- `GET /upload/folders?filters[$and][0][parent][id]=<parentId>&pagination[pageSize]=100` — list children
- `POST /upload/folders` with `{ "name": "<Name>", "parent": <parentId> }` — create
- `POST /upload` multipart, field `files` plus field `fileInfo` set to the JSON string
  `{ "name": "<file name>", "folder": <folderId> }` — upload one file
- `GET /upload/files?filters[$and][0][folder][id]=<folderId>&pagination[pageSize]=100` — verify

Create one Title Case subfolder per section under the parent id. If a folder with that name already
exists, reuse it rather than creating a duplicate.

## Step 4 — Upload

The admin page cannot read local files and its CSP blocks plain http:// origins, so serve the files
over local HTTPS and let the page fetch them.

1. Start the server in the background:
   `scripts/serve-https.py --root <OUTPUT_DIR> --cert <localhost.pem> --key <localhost-key.pem>`
2. Open `https://localhost:8766/` once in a normal tab so Chrome trusts the certificate.
3. In the Strapi admin tab, for each file: `fetch` it from the local server as a Blob, build the
   multipart `FormData`, and `POST /upload` into the right section folder.
4. Run the loop **asynchronously**, storing progress in `window.__uploads`, and poll it. A single
   blocking script times out at about 45 seconds and will appear to hang.
5. **Re-read the token inside the loop, per file, never once up front.** The admin session rotates
   during a long run and every later upload then returns 401. Read it fresh each time, retry a failed
   file two or three times with a short pause, and record the failures rather than aborting.
6. **Make the loop restartable.** Before uploading, `GET /upload/files` for the target folder and skip
   any name already there. A rotation then costs a retry instead of a gap or a duplicate.
7. If the session has actually expired rather than rotated, every retry returns 401 and the page may
   stop responding. Reload the admin tab, confirm a `GET /upload/files` succeeds, and start the loop
   again; step 6 makes that safe.
8. Stop the server when finished.

## Step 5 — Verify and report

1. `GET /upload/files` per folder, compare counts against the local folders, re-upload anything missing.
2. Write `OUTPUT_DIR/cdn-urls.json`:
   `{ "folders": { "<Section>": <id> }, "files": { "<section>/<file>": "<absolute CDN url>" } }`,
   using the absolute `url` Strapi returns.
3. Report files per section, any conversions, skipped duplicates, and the path to `cdn-urls.json`.

## Notes

- Figma asset URLs expire after roughly a week. Re-run step 1 rather than reusing an old list.
- Strapi rewrites file names to snake_case and appends a hash, so the final CDN name will not match
  the local name. `cdn-urls.json` is the mapping; do not reconstruct URLs by hand.

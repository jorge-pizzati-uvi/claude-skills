// Session bootstrap for a Studio tab. Paste as the `function` of mcp__chrome-devtools__evaluate_script
// with waitForStableDom:false. Edit MODEL / CLIENT / BRANCH before running.
// Returns { ok, reason?, branch, title, visibility, hostUrl, tools, schemas } — never throws.
async () => {
  const MODEL = "<model id>";          // e.g. "claude-fable-5-1"
  const CLIENT = "claude-code";
  const BRANCH = "<branch name>";      // decoded, e.g. "feat/destinations-coded-components"
  const SCHEMA_TOOLS = ["read", "changeElement", "insertHtml"];
  const out = { ok: false, url: location.href, title: document.title, visibility: document.visibilityState };

  if (/\/login|\/signup|\/auth/i.test(location.pathname) || document.querySelector('input[type="password"]')) {
    return { ...out, reason: "login" };
  }
  if (document.visibilityState === "hidden") {
    return { ...out, reason: "hidden" };
  }

  for (let i = 0; i < 45 && !window.PLASMIC_AI_TOOLS; i++) {
    await new Promise(r => setTimeout(r, 1000));
  }
  if (!window.PLASMIC_AI_TOOLS) {
    return { ...out, reason: "no-tools", hint: "open a fresh tab (reloads hang); if the host-app toast is up, the tab may be throttled" };
  }

  // Branch: the URL param is what we asked for; the title is what Studio actually serves.
  const urlBranch = decodeURIComponent(new URLSearchParams(location.search).get("branch") || "main");
  for (let i = 0; i < 20 && !document.title.includes(urlBranch === "main" ? "" : urlBranch); i++) {
    await new Promise(r => setTimeout(r, 1000));
  }
  out.branch = urlBranch;
  out.title = document.title;
  if (urlBranch !== BRANCH || (BRANCH !== "main" && !document.title.includes(BRANCH))) {
    return { ...out, reason: "branch", expected: BRANCH };
  }

  const id = await window.PLASMIC_AI_TOOLS.identify({ model: MODEL, client: CLIENT, outputFormat: "json" });
  if (!id || !id.success) {
    return { ...out, reason: "identify", error: id && id.error };
  }

  const iframe = [...document.querySelectorAll("iframe")].map(f => f.src).find(s => /plasmic-host/.test(s)) || "";
  out.hostUrl = iframe.split("#")[0];
  out.tools = Object.keys(window.PLASMIC_AI_TOOLS._meta);
  out.schemas = Object.fromEntries(SCHEMA_TOOLS.filter(t => window.PLASMIC_AI_TOOLS._meta[t]).map(t => [t, window.PLASMIC_AI_TOOLS._meta[t].inputSchema]));
  out.ok = true;
  return out;
};

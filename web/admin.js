function wireRawForm(formId, outputId, buildPath) {
  const form = document.getElementById(formId);
  const output = document.getElementById(outputId);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    output.className = "";
    output.textContent = "Loading...";

    const path = buildPath();
    const { ok, status, body, error, elapsedMs, url } = await rviFetch(path);

    const header = error
      ? `Request failed: ${error} (${url})`
      : `HTTP ${status} — ${elapsedMs.toFixed(1)}ms — ${url}`;
    output.className = ok ? "" : "error";
    output.textContent = `${header}\n\n${JSON.stringify(body, null, 2)}`;
  });
}

wireRawForm("search-form", "search-output", () => {
  const q = document.getElementById("search-q").value;
  const limit = document.getElementById("search-limit").value;
  return `/public/v1/search?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`;
});

wireRawForm("resolve-form", "resolve-output", () => {
  const ns = document.getElementById("resolve-ns").value;
  const identifier = document.getElementById("resolve-identifier").value;
  return `/public/v1/resolve?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(identifier)}`;
});

wireRawForm("replacements-form", "replacements-output", () => {
  const ns = document.getElementById("replacements-ns").value;
  const identifier = document.getElementById("replacements-identifier").value;
  return `/public/v1/replacements?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(identifier)}`;
});

async function loadLogs() {
  const output = document.getElementById("logs-output");
  output.className = "";
  output.textContent = "Loading...";

  const { ok, status, body, error } = await rviFetch("/debug/v1/logs?lines=100");

  if (!ok) {
    output.className = "error";
    output.textContent = error ? `Request failed: ${error}` : `HTTP ${status}`;
    return;
  }

  output.textContent = body.lines.length > 0 ? body.lines.join("\n") : "(no log lines yet)";
}

document.getElementById("logs-refresh").addEventListener("click", loadLogs);
loadLogs();

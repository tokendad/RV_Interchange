const form = document.getElementById("search-form");
const input = document.getElementById("search-input");
const statusEl = document.getElementById("search-status");
const resultsEl = document.getElementById("search-results");
const detailEl = document.getElementById("detail-view");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = input.value.trim();
  detailEl.innerHTML = "";
  resultsEl.innerHTML = "";

  if (!query) {
    statusEl.textContent = "";
    return;
  }

  statusEl.className = "";
  statusEl.textContent = "Searching...";

  const { ok, status, body, error } = await rviFetch(
    `/public/v1/search?q=${encodeURIComponent(query)}&limit=20`);

  if (!ok) {
    statusEl.className = "error";
    statusEl.textContent = error
      ? `Request failed: ${error}`
      : `HTTP ${status}: ${body && body.detail ? body.detail : "search failed"}`;
    return;
  }

  if (body.results.length === 0) {
    statusEl.className = "";
    statusEl.textContent = `No matches found for "${body.query}".`;
    return;
  }

  statusEl.className = "";
  statusEl.textContent =
    `${body.results.length} match${body.results.length === 1 ? "" : "es"} for "${body.query}"`;
  renderResults(body.results);
});

function renderResults(results) {
  resultsEl.innerHTML = "";
  for (const result of results) {
    const li = document.createElement("li");
    li.className = "result-card";

    const label = document.createElement("div");
    label.className = "result-label";
    label.textContent = result.label;
    li.appendChild(label);

    const idList = document.createElement("div");
    idList.className = "identifier-pills";
    for (const identifier of result.identifiers) {
      const pill = document.createElement("span");
      pill.className = "pill";
      pill.textContent = `${identifier.ns}: ${identifier.value}`;
      idList.appendChild(pill);
    }
    li.appendChild(idList);

    li.addEventListener("click", () => showDetail(result));
    resultsEl.appendChild(li);
  }
}

async function showDetail(result) {
  detailEl.innerHTML = "<p>Loading replacements...</p>";

  // Use the specific identifier that matched the search (result.label holds the
  // matched value — see api/services.py SearchService.search), not an arbitrary
  // identifier off the component.
  const matched = result.identifiers.find((i) => i.value === result.label)
    || result.identifiers[0];

  const { ok, status, body, error } = await rviFetch(
    `/public/v1/replacements?ns=${encodeURIComponent(matched.ns)}` +
    `&identifier=${encodeURIComponent(matched.value)}`);

  if (!ok) {
    detailEl.innerHTML = "";
    const errEl = document.createElement("p");
    errEl.className = "error";
    errEl.textContent = error
      ? `Request failed: ${error}`
      : `HTTP ${status}: ${body && body.detail ? body.detail : "lookup failed"}`;
    detailEl.appendChild(errEl);
    return;
  }

  renderDetail(body);
}

function renderDetail(data) {
  detailEl.innerHTML = "";

  const heading = document.createElement("h2");
  heading.textContent = `Replacements for ${data.source}`;
  detailEl.appendChild(heading);

  const tierOrder = ["Exact Match", "Direct Fit", "Fits With Modification"];
  const byTier = {};
  for (const item of data.replacements) {
    if (!byTier[item.fit]) byTier[item.fit] = [];
    byTier[item.fit].push(item);
  }

  for (const tier of tierOrder) {
    const items = byTier[tier];
    if (!items || items.length === 0) continue;

    const section = document.createElement("section");
    section.className = "tier-section";

    const tierHeading = document.createElement("h3");
    tierHeading.textContent = tier;
    section.appendChild(tierHeading);

    const list = document.createElement("ul");
    for (const item of items) {
      const li = document.createElement("li");
      li.textContent = item.summary ? `${item.part} — ${item.summary}` : item.part;
      list.appendChild(li);
    }
    section.appendChild(list);
    detailEl.appendChild(section);
  }

  if (data.supersessions && data.supersessions.length > 0) {
    const section = document.createElement("section");
    section.className = "supersession-section";

    const heading2 = document.createElement("h3");
    heading2.textContent = "Superseded by";
    section.appendChild(heading2);

    const list = document.createElement("ul");
    for (const item of data.supersessions) {
      const li = document.createElement("li");
      li.textContent = item.note ? `${item.part} — ${item.note}` : item.part;
      list.appendChild(li);
    }
    section.appendChild(list);
    detailEl.appendChild(section);
  }
}

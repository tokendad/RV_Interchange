const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchButton = searchForm.querySelector('button[type="submit"]');
const statusEl = document.getElementById("search-status");
const contentEl = document.getElementById("content");
const homeContentHTML = contentEl.innerHTML;

let lastSearchResponse = null;
let currentQuery = null;

document.getElementById("header-slot").replaceWith(renderHeader("lookup"));
document.getElementById("footer-slot").replaceWith(renderFooter());

document.querySelectorAll(".example-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    searchInput.value = chip.dataset.example;
    searchForm.requestSubmit();
  });
});

searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = searchInput.value.trim();
  if (!query) return;
  runSearch(query, { pushUrl: true });
});

window.addEventListener("popstate", () => {
  const state = parseUrlState();
  if (!state.q) {
    showHome();
    return;
  }
  searchInput.value = state.q;
  runSearch(state.q, { pushUrl: false, thenOpenPart: state.part });
});

async function runSearch(query, { pushUrl, thenOpenPart }) {
  statusEl.className = "";
  statusEl.textContent = "Searching RV Interchange…";
  searchButton.disabled = true;

  const { ok, status, body, error } = await rviFetch(
    `/public/v1/search?q=${encodeURIComponent(query)}&limit=20`);

  searchButton.disabled = false;
  currentQuery = query;

  if (!ok) {
    statusEl.className = "error";
    statusEl.textContent = "The lookup service is temporarily unavailable.";
    const detail = error
      ? `Request failed: ${error}`
      : `HTTP ${status}: ${body && body.detail ? body.detail : "search failed"}`;
    contentEl.innerHTML = "";
    contentEl.appendChild(renderErrorState(
      "The lookup service is temporarily unavailable. Please try the search again.", detail));
    if (pushUrl) pushUrlState({ q: query, part: null });
    return;
  }

  lastSearchResponse = body;

  if (body.results.length === 0) {
    statusEl.className = "";
    statusEl.textContent = "";
    contentEl.innerHTML = "";
    contentEl.appendChild(renderNoResultsState(query));
    if (pushUrl) pushUrlState({ q: query, part: null });
    return;
  }

  statusEl.className = "";
  statusEl.textContent =
    `${body.results.length} match${body.results.length === 1 ? "" : "es"} for "${body.query}"`;
  showResultsView();
  if (pushUrl) pushUrlState({ q: query, part: null });

  if (thenOpenPart) {
    const matched = body.results
      .flatMap((r) => r.identifiers.map((i) => ({ i })))
      .find(({ i }) => i.ns === thenOpenPart.ns && i.value === thenOpenPart.value);
    if (matched) {
      await openDetail(thenOpenPart.ns, thenOpenPart.value, { pushUrl: false });
    }
  }
}

function showHome() {
  contentEl.innerHTML = homeContentHTML;
  statusEl.textContent = "";
  statusEl.className = "";
  searchInput.value = "";
  lastSearchResponse = null;
}

function showResultsView() {
  if (!lastSearchResponse) {
    showHome();
    return;
  }
  contentEl.innerHTML = "";
  contentEl.appendChild(renderResultsView(lastSearchResponse, { onSelectResult: handleSelectResult }));
}

function handleSelectResult(result) {
  const matched = result.identifiers.find((i) => i.value === result.label) || result.identifiers[0];
  openDetail(matched.ns, matched.value, { pushUrl: true });
}

async function openDetail(ns, value, { pushUrl }) {
  contentEl.innerHTML = "<p>Loading part details…</p>";

  const [resolveResult, replacementsResult] = await Promise.all([
    rviFetch(`/public/v1/resolve?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(value)}`),
    rviFetch(`/public/v1/replacements?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(value)}`),
  ]);

  if (!resolveResult.ok || !replacementsResult.ok) {
    contentEl.innerHTML = "";
    const detail = resolveResult.error || replacementsResult.error || "lookup failed";
    contentEl.appendChild(renderErrorState(
      "The lookup service is temporarily unavailable. Please try the search again.", detail));
    return;
  }

  contentEl.innerHTML = "";
  contentEl.appendChild(renderDetailView(
    { resolveData: resolveResult.body, replacementsData: replacementsResult.body, ns },
    {
      onBack: () => {
        showResultsView();
        pushUrlState({ q: currentQuery, part: null });
      },
      onCopyLink: () => {
        navigator.clipboard.writeText(window.location.href);
      },
      onChainNodeClick: (nextValue) => openDetail(ns, nextValue, { pushUrl: true }),
    },
  ));

  if (pushUrl) pushUrlState({ q: currentQuery, part: { ns, value } });
}

(function init() {
  const state = parseUrlState();
  if (state.q) {
    searchInput.value = state.q;
    runSearch(state.q, { pushUrl: false, thenOpenPart: state.part });
  }
})();

function highlightMatch(label, query) {
  const wrapper = document.createElement("span");

  if (!query) {
    wrapper.textContent = label;
    return wrapper;
  }

  const idx = label.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) {
    wrapper.textContent = label;
    return wrapper;
  }

  const before = label.slice(0, idx);
  const match = label.slice(idx, idx + query.length);
  const after = label.slice(idx + query.length);

  if (before) wrapper.appendChild(document.createTextNode(before));
  const mark = document.createElement("mark");
  mark.textContent = match;
  wrapper.appendChild(mark);
  if (after) wrapper.appendChild(document.createTextNode(after));

  return wrapper;
}

function renderResultsView(searchResponse, { onSelectResult }) {
  const container = document.createElement("div");

  const summary = document.createElement("p");
  summary.className = "results-summary";
  const count = searchResponse.results.length;
  summary.textContent = `${count} match${count === 1 ? "" : "es"} for "${searchResponse.query}"`;
  container.appendChild(summary);

  const list = document.createElement("div");
  list.className = "result-list";

  for (const result of searchResponse.results) {
    list.appendChild(renderResultCard(result, searchResponse.query, onSelectResult));
  }

  container.appendChild(list);
  return container;
}

function renderResultCard(result, query, onSelectResult) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "result-card";

  if (result.manufacturer || result.part_type) {
    const meta = document.createElement("div");
    meta.className = "result-label-meta";
    meta.textContent = [result.manufacturer, result.part_type].filter(Boolean).join(" · ");
    card.appendChild(meta);
  }

  const title = document.createElement("div");
  title.className = "result-title";
  title.appendChild(highlightMatch(result.label, query));
  card.appendChild(title);

  const others = result.identifiers.map((i) => i.value).filter((v) => v !== result.label);
  if (others.length > 0) {
    const alt = document.createElement("div");
    alt.className = "result-alt";
    alt.textContent = `Also known as: ${others.join(" · ")}`;
    card.appendChild(alt);
  }

  const chevron = document.createElement("span");
  chevron.className = "result-chevron";
  chevron.setAttribute("aria-hidden", "true");
  chevron.textContent = "→";
  card.appendChild(chevron);

  card.addEventListener("click", () => onSelectResult(result));
  return card;
}

function renderNoResultsState(query) {
  const container = document.createElement("div");
  container.className = "no-results";

  const heading = document.createElement("p");
  heading.className = "no-results-heading";
  heading.textContent = "We couldn't find that number yet.";
  container.appendChild(heading);

  const sub = document.createElement("p");
  sub.textContent = `No match found for "${query}"`;
  container.appendChild(sub);

  const tryHeading = document.createElement("p");
  tryHeading.textContent = "Try:";
  container.appendChild(tryHeading);

  const list = document.createElement("ul");
  const suggestions = [
    "The number without spaces",
    "The number without hyphens",
    "Another number printed on the label",
    "Reviewing supported manufacturers",
  ];
  for (const s of suggestions) {
    const li = document.createElement("li");
    li.textContent = s;
    list.appendChild(li);
  }
  container.appendChild(list);

  const reportLink = document.createElement("a");
  reportLink.href = "https://github.com/tokendad/RV_Interchange/issues/new";
  reportLink.textContent = "Report a missing part";
  container.appendChild(reportLink);

  return container;
}

function renderErrorState(message, technicalDetail) {
  const container = document.createElement("div");
  container.className = "error-state";

  const msg = document.createElement("p");
  msg.className = "error-message";
  msg.textContent = message;
  container.appendChild(msg);

  if (technicalDetail) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Technical details";
    details.appendChild(summary);
    const pre = document.createElement("pre");
    pre.textContent = technicalDetail;
    details.appendChild(pre);
    container.appendChild(details);
  }

  return container;
}

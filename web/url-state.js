function parseUrlState() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get("q");
  const partParam = params.get("part");

  let part = null;
  if (partParam && partParam.includes(":")) {
    const idx = partParam.indexOf(":");
    part = { ns: partParam.slice(0, idx), value: partParam.slice(idx + 1) };
  }

  return { q: q || null, part };
}

function buildQueryString({ q, part }) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (part) params.set("part", `${part.ns}:${part.value}`);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function pushUrlState(state) {
  const qs = buildQueryString(state);
  const url = `${window.location.pathname}${qs}`;
  history.pushState(null, "", url);
}

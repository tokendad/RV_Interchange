document.getElementById("header-slot").replaceWith(renderHeader("coverage"));
document.getElementById("footer-slot").replaceWith(renderFooter());

const statusEl = document.getElementById("coverage-status");
const tableWrapEl = document.getElementById("coverage-table-wrap");

const COLUMNS = [
  { key: "components", label: "Components Tracked" },
  { key: "fits_edges", label: "Fit Relationships" },
  { key: "substitutes_edges", label: "Substitute Relationships" },
  { key: "supersedes_edges", label: "Supersessions" },
];

function renderCoverageTable(body) {
  const table = document.createElement("table");
  table.className = "coverage-table";

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headerRow.appendChild(document.createElement("th")).textContent = "Manufacturer";
  for (const column of COLUMNS) {
    headerRow.appendChild(document.createElement("th")).textContent = column.label;
  }
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const row of body.manufacturers) {
    const tr = document.createElement("tr");
    tr.appendChild(document.createElement("th")).textContent = row.manufacturer;
    for (const column of COLUMNS) {
      const td = document.createElement("td");
      td.textContent = row[column.key];
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);

  const tfoot = document.createElement("tfoot");
  const totalsRow = document.createElement("tr");
  totalsRow.appendChild(document.createElement("th")).textContent = "Total";
  for (const column of COLUMNS) {
    const td = document.createElement("td");
    td.textContent = body.totals[column.key];
    totalsRow.appendChild(td);
  }
  tfoot.appendChild(totalsRow);
  table.appendChild(tfoot);

  return table;
}

async function loadCoverage() {
  const { ok, status, body, error } = await rviFetch("/public/v1/coverage");

  if (!ok) {
    statusEl.className = "error";
    statusEl.textContent = "Coverage data is temporarily unavailable.";
    const detail = error
      ? `Request failed: ${error}`
      : `HTTP ${status}: ${body && body.detail ? body.detail : "request failed"}`;
    console.error(detail);
    return;
  }

  statusEl.remove();
  tableWrapEl.appendChild(renderCoverageTable(body));
}

loadCoverage();

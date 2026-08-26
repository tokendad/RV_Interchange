const queue = document.getElementById("queue");
const detail = document.getElementById("detail");
const badge = document.getElementById("reviewer-badge");
let reviewer = { roles: [] };

async function request(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
  return body;
}

function el(tag, className, content) { const node = document.createElement(tag); if (className) node.className = className; if (content !== undefined) node.append(document.createTextNode(content)); return node; }

async function loadSession() {
  reviewer = await request("/review/v1/session");
  badge.textContent = `${reviewer.email} · ${reviewer.roles.join(", ") || "no role"}`;
}

async function loadQueue() {
  queue.replaceChildren(el("p", "muted", "Loading queue…"));
  try {
    const status = document.getElementById("status-filter").value;
    const page = await request(`/review/v1/queue${status ? `?status=${encodeURIComponent(status)}` : ""}`);
    queue.replaceChildren(...(page.items.length ? page.items.map(queueCard) : [el("p", "muted", "No submissions match this filter.")]));
  } catch (error) { queue.replaceChildren(el("p", "error", error.message)); }
}

function queueCard(item) {
  const button = el("button", "queue-card"); button.type = "button"; button.dataset.submissionId = item.id;
  button.append(el("span", `priority priority-${item.priority}`, item.priority)); button.append(el("strong", "queue-summary", item.summary));
  button.append(el("span", "queue-meta", `${item.intent.replaceAll("_", " ")} · ${item.pending_claim_count} pending claim${item.pending_claim_count === 1 ? "" : "s"}`));
  button.addEventListener("click", () => loadDetail(item.id)); return button;
}

async function loadDetail(id) { detail.replaceChildren(el("p", "muted", "Loading submission…")); try { renderDetail(await request(`/review/v1/submissions/${encodeURIComponent(id)}`)); } catch (error) { detail.replaceChildren(el("p", "error", error.message)); } }

function renderDetail(data) {
  const submission = data.submission; const header = el("div", "detail-header");
  header.append(el("span", `priority priority-${submission.priority}`, submission.priority), el("h2", null, submission.summary), el("p", "detail-meta", `${submission.intent.replaceAll("_", " ")} · ${submission.status}`));
  const claims = el("section", "claims"); claims.append(el("h3", null, "Claims")); for (const claim of data.claims) claims.append(claimCard(submission.id, claim));
  const states = el("div", "state-strip"); states.append(state("Acceptance", submission.status), state("Promotion", submission.evidence_state), state("Integration", submission.integration_state)); detail.replaceChildren(header, states, claims);
}

function state(label, value) { const node = el("div", "state"); node.append(el("span", "state-label", label), el("strong", null, value)); return node; }
function claimCard(submissionId, claim) {
  const card = el("article", "claim-card"); const body = el("div"); body.append(el("span", "claim-type", claim.claim_type.replaceAll("_", " ")), el("p", "claim-value", JSON.stringify(claim.proposed_json)), el("span", `claim-status claim-${claim.status}`, claim.status)); card.append(body);
  if (reviewer.roles.includes("admin") && claim.status === "pending") { const actions = el("div", "claim-actions"); for (const action of ["accepted", "rejected", "duplicate"]) { const button = el("button", "action-button", action); button.type = "button"; button.addEventListener("click", () => decide(submissionId, claim.id, action)); actions.append(button); } card.append(actions); }
  if (reviewer.roles.includes("trusted") || reviewer.roles.includes("admin")) { const button = el("button", "advisory-button", "Add advisory assessment"); button.type = "button"; button.addEventListener("click", () => assess(submissionId, claim.id)); card.append(button); } return card;
}

async function decide(submissionId, claimId, action) { const reason = window.prompt("Reason code (required):", "source_verified"); if (!reason) return; try { await request(`/review/v1/submissions/${submissionId}/claims/${claimId}/decision`, { method: "POST", body: JSON.stringify({ action, reason_code: reason, idempotency_key: crypto.randomUUID() }) }); await loadDetail(submissionId); await loadQueue(); } catch (error) { window.alert(error.message); } }
async function assess(submissionId, claimId) { const reason = window.prompt("Assessment reason (required):", "additional corroboration"); if (!reason) return; try { await request(`/review/v1/submissions/${submissionId}/claims/${claimId}/assessment`, { method: "POST", body: JSON.stringify({ assessment: "endorse", reason, idempotency_key: crypto.randomUUID() }) }); window.alert("Advisory assessment recorded."); } catch (error) { window.alert(error.message); } }

document.getElementById("status-filter").addEventListener("change", loadQueue);
Promise.all([loadSession(), loadQueue()]).catch((error) => { badge.textContent = "Access required"; queue.replaceChildren(el("p", "error", error.message)); });

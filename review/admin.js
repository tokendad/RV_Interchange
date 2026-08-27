const queue = document.getElementById("queue");
const detail = document.getElementById("detail");
const badge = document.getElementById("reviewer-badge");
let reviewer = { roles: [], capabilities: [] };

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
  return body;
}

function el(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.append(document.createTextNode(content));
  return node;
}

function canDecide() {
  return reviewer.roles.includes("admin") || reviewer.capabilities.includes("publisher");
}

function canAdvise() {
  return canDecide() || reviewer.roles.includes("trusted");
}

async function loadSession() {
  reviewer = await request("/review/v1/session");
  const authority = [...reviewer.roles, ...reviewer.capabilities].join(", ");
  badge.textContent = `${reviewer.email} · ${authority}`;
}

async function loadQueue() {
  queue.replaceChildren(el("p", "muted", "Loading queue…"));
  try {
    const params = new URLSearchParams();
    const status = document.getElementById("status-filter").value;
    const priority = document.getElementById("priority-filter").value;
    if (status) params.set("status", status);
    if (priority) params.set("priority", priority);
    const suffix = params.size ? `?${params.toString()}` : "";
    const page = await request(`/review/v1/queue${suffix}`);
    queue.replaceChildren(
      ...(page.items.length
        ? page.items.map(queueCard)
        : [el("p", "muted", "No submissions match these filters.")]),
    );
  } catch (error) {
    queue.replaceChildren(el("p", "error", error.message));
  }
}

function queueCard(item) {
  const button = el("button", "queue-card");
  button.type = "button";
  button.dataset.submissionId = item.id;
  button.append(
    el("span", `priority priority-${item.priority}`, item.priority),
    el("strong", "queue-summary", item.summary),
    el(
      "span",
      "queue-meta",
      `${item.intent.replaceAll("_", " ")} · ${item.pending_claim_count} pending claim${item.pending_claim_count === 1 ? "" : "s"}`,
    ),
  );
  button.addEventListener("click", () => loadDetail(item.id));
  return button;
}

async function loadDetail(id) {
  detail.replaceChildren(el("p", "muted", "Loading submission…"));
  try {
    renderDetail(await request(`/review/v1/submissions/${encodeURIComponent(id)}`));
  } catch (error) {
    detail.replaceChildren(el("p", "error", error.message));
  }
}

function renderDetail(data) {
  const submission = data.submission;
  const header = el("div", "detail-header");
  header.append(
    el("span", `priority priority-${submission.priority}`, submission.priority),
    el("h2", null, submission.summary),
    el("p", "detail-meta", `${submission.intent.replaceAll("_", " ")} · ${submission.status}`),
  );

  const states = el("div", "state-strip");
  states.append(
    state("Acceptance", submission.status),
    state("Promotion", submission.evidence_state),
    state("Integration", submission.integration_state),
  );

  const target = el("section", "target-context");
  target.append(el("h3", null, "Target context"));
  target.append(
    el(
      "pre",
      null,
      JSON.stringify(
        {
          component_id: submission.target_component_id,
          edge: submission.target_edge_key_json,
          namespace: submission.target_namespace,
          identifier: submission.target_identifier,
        },
        null,
        2,
      ),
    ),
  );

  const submissionActions = el("div", "submission-actions");
  if (canDecide() && ["received", "held", "under_review"].includes(submission.status)) {
    submissionActions.append(actionButton("Request information", () => requestInformation(submission.id)));
  }
  if (canAdvise()) {
    submissionActions.append(actionButton("Flag as spam", () => flagSpam(submission.id), "advisory-button"));
  }

  const claims = el("section", "claims");
  claims.append(el("h3", null, "Claims"));
  for (const claim of data.claims) claims.append(claimCard(submission.id, claim));

  const artifacts = el("section", "artifact-list");
  artifacts.append(el("h3", null, "Artifacts"));
  if (!data.artifacts.length) {
    artifacts.append(el("p", "muted", "No sanitized artifacts attached."));
  } else {
    for (const artifact of data.artifacts) {
      artifacts.append(
        el(
          "div",
          "artifact-card",
          `${artifact.original_name} · ${artifact.detected_media_type} · ${artifact.size_bytes} bytes · ${artifact.scan_status}`,
        ),
      );
    }
  }

  const audit = el("section", "audit-list");
  audit.append(el("h3", null, "Review audit"));
  if (!data.audit.length) audit.append(el("p", "muted", "No review activity yet."));
  for (const entry of data.audit) {
    const label = entry.type === "assessment"
      ? `${entry.assessment} · claim ${entry.claim_id || "submission"} · ${entry.reason}`
      : `${entry.action} · ${entry.reason_code} · ${entry.resulting_status}`;
    audit.append(el("div", "audit-card", `${label} · ${entry.created_at}`));
  }

  detail.replaceChildren(header, states, target, submissionActions, claims, artifacts, audit);
}

function state(label, value) {
  const node = el("div", "state");
  node.append(el("span", "state-label", label), el("strong", null, value));
  return node;
}

function actionButton(label, handler, className = "action-button") {
  const button = el("button", className, label);
  button.type = "button";
  button.addEventListener("click", handler);
  return button;
}

function claimCard(submissionId, claim) {
  const card = el("article", "claim-card");
  const body = el("div");
  body.append(
    el("span", "claim-type", claim.claim_type.replaceAll("_", " ")),
    el("p", "claim-value", JSON.stringify(claim.proposed_json)),
    el("span", `claim-status claim-${claim.status}`, claim.status),
  );
  card.append(body);

  if (canDecide() && claim.status === "pending") {
    const actions = el("div", "claim-actions");
    for (const action of ["accepted", "rejected", "duplicate"]) {
      actions.append(actionButton(action, () => decide(submissionId, claim.id, action)));
    }
    card.append(actions);
  }
  if (canAdvise()) {
    const actions = el("div", "claim-actions");
    for (const assessment of ["endorse", "dispute"]) {
      actions.append(
        actionButton(
          assessment,
          () => assess(submissionId, claim.id, assessment),
          "advisory-button",
        ),
      );
    }
    card.append(actions);
  }
  return card;
}

async function decide(submissionId, claimId, action) {
  const reason = window.prompt("Reason code (required):", "source_verified");
  if (!reason) return;
  await mutate(
    `/review/v1/submissions/${submissionId}/claims/${claimId}/decision`,
    { action, reason_code: reason, idempotency_key: crypto.randomUUID() },
    submissionId,
  );
}

async function assess(submissionId, claimId, assessment) {
  const reason = window.prompt(`${assessment} reason (required):`);
  if (!reason) return;
  await mutate(
    `/review/v1/submissions/${submissionId}/claims/${claimId}/assessment`,
    { assessment, reason, idempotency_key: crypto.randomUUID() },
    submissionId,
  );
}

async function requestInformation(submissionId) {
  const reason = window.prompt("Public information request (required):");
  if (!reason) return;
  await mutate(
    `/review/v1/submissions/${submissionId}/request-information`,
    { reason, idempotency_key: crypto.randomUUID() },
    submissionId,
  );
}

async function flagSpam(submissionId) {
  const reason = window.prompt("Spam assessment reason (required):");
  if (!reason) return;
  await mutate(
    `/review/v1/submissions/${submissionId}/spam`,
    { assessment: "spam", reason, idempotency_key: crypto.randomUUID() },
    submissionId,
  );
}

async function mutate(path, body, submissionId) {
  try {
    await request(path, { method: "POST", body: JSON.stringify(body) });
    await loadDetail(submissionId);
    await loadQueue();
  } catch (error) {
    window.alert(error.message);
  }
}

document.getElementById("status-filter").addEventListener("change", loadQueue);
document.getElementById("priority-filter").addEventListener("change", loadQueue);
Promise.all([loadSession(), loadQueue()]).catch((error) => {
  badge.textContent = "Access required";
  queue.replaceChildren(el("p", "error", error.message));
});

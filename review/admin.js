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
  return canPromote();
}

function canAdminister() {
  return reviewer.roles.includes("admin");
}

function canPromote() {
  return reviewer.roles.includes("admin") &&
    reviewer.capabilities.includes("publisher");
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

  const workflow = renderEvidenceWorkflow(data);
  detail.replaceChildren(header, states, target, submissionActions, claims, artifacts, workflow, audit);
}

function labeledControl(label, control) {
  const wrapper = el("label", "field");
  wrapper.append(el("span", "field-label", label), control);
  return wrapper;
}

function inputControl(id, type = "text") {
  const control = document.createElement("input");
  control.id = id;
  control.name = id;
  control.type = type;
  return control;
}

function renderEvidenceWorkflow(data) {
  const workflow = el("section", "evidence-workflow");
  workflow.id = "evidence-workflow";
  workflow.setAttribute("aria-labelledby", "evidence-workflow-title");
  const title = el("h3", null, "Evidence workflow");
  title.id = "evidence-workflow-title";
  const live = el("div", "workflow-message");
  live.id = "workflow-message";
  live.setAttribute("aria-live", "polite");
  workflow.append(title, live);

  if (canAdminister() && data.submission.status !== "withdrawn") {
    workflow.append(renderDraftEditor(data, live));
  }
  if (canAdminister()) {
    for (const draft of data.drafts || []) {
      workflow.append(renderPromotionPanel(data, draft, live));
    }
  }
  if (data.submission.integration_state === "pending" || (data.drafts || []).some((draft) => draft.state === "promoted")) {
    live.append(el("p", "integration-note", "Integration pending — public lookup has not changed."));
  }
  return workflow;
}

function renderDraftEditor(data, live) {
  const form = document.createElement("form");
  form.className = "draft-editor";
  form.setAttribute("aria-labelledby", "draft-editor-title");
  const title = el("h4", null, "Create private observation draft");
  title.id = "draft-editor-title";
  const sourceType = document.createElement("select");
  sourceType.id = "source-type";
  sourceType.name = "source_type";
  ["manufacturer_pdf", "manufacturer_page", "dataplate_photo", "manual_measurement", "dealer_call", "field_report", "other"].forEach((value) => {
    const option = el("option", null, value.replaceAll("_", " "));
    option.value = value;
    sourceType.append(option);
  });
  const sourceName = inputControl("source-name");
  const sourceUrl = inputControl("source-url", "url");
  const raw = document.createElement("textarea"); raw.id = "raw-description"; raw.name = "raw_content";
  const extracted = document.createElement("textarea"); extracted.id = "extracted-json"; extracted.name = "extracted"; extracted.value = "{}";
  const claims = document.createElement("fieldset"); claims.className = "selection-group";
  claims.append(el("legend", null, "Accepted claims"));
  data.claims.filter((claim) => claim.status === "accepted").forEach((claim) => {
    const checkbox = inputControl(`accepted-claim-${claim.id}`, "checkbox"); checkbox.value = claim.id; checkbox.name = "claim_ids"; checkbox.checked = true;
    claims.append(labeledControl(JSON.stringify(claim.proposed_json), checkbox));
  });
  const artifacts = document.createElement("fieldset"); artifacts.className = "selection-group";
  artifacts.append(el("legend", null, "Clean artifacts"));
  data.artifacts.filter((artifact) => artifact.scan_status === "clean").forEach((artifact) => {
    const checkbox = inputControl(`clean-artifact-${artifact.id}`, "checkbox"); checkbox.value = artifact.id; checkbox.name = "artifact_ids";
    artifacts.append(labeledControl(`${artifact.original_name} (${artifact.detected_media_type})`, checkbox));
  });
  const submit = actionButton("Save private draft");
  submit.type = "submit";
  form.addEventListener("submit", (event) => { event.preventDefault(); createDraft(data, form, live); });
  form.append(title, labeledControl("Source type", sourceType), labeledControl("Source name", sourceName), labeledControl("URL", sourceUrl), labeledControl("Raw description", raw), labeledControl("Extracted JSON", extracted), claims, artifacts, submit);
  return form;
}

function serializeDraft(form, submissionId) {
  const values = new FormData(form);
  let extracted;
  try { extracted = JSON.parse(values.get("extracted") || "{}"); } catch { throw new Error("Extracted JSON must be valid JSON."); }
  return { source_type: values.get("source_type"), source_name: values.get("source_name"), source_url: values.get("source_url") || null, raw_content: values.get("raw_content"), extracted, claim_ids: values.getAll("claim_ids"), artifact_ids: values.getAll("artifact_ids"), idempotency_key: crypto.randomUUID(), submission_id: submissionId };
}

async function createDraft(data, form, live) {
  try {
    const payload = serializeDraft(form, data.submission.id);
    delete payload.submission_id;
    await request(`/review/v1/submissions/${encodeURIComponent(data.submission.id)}/observation-drafts`, { method: "POST", body: JSON.stringify(payload) });
    await loadDetail(data.submission.id);
    await loadQueue();
  } catch (error) { showWorkflowError(live, error); }
}

function renderPromotionPanel(data, draft, live) {
  const panel = el("article", "promotion-panel");
  panel.append(el("h4", null, `Private draft · ${draft.source_name} · ${draft.state}`));
  if (draft.state === "draft" && canAdminister()) {
    panel.append(actionButton("Mark draft ready", async () => {
      try {
        await request(`/review/v1/observation-drafts/${encodeURIComponent(draft.id)}/ready`, { method: "POST", body: JSON.stringify({ expected_version: draft.version }) });
        await loadDetail(data.submission.id); await loadQueue();
      } catch (error) { showWorkflowError(live, error); }
    }));
  }
  if (draft.state !== "ready" || !canPromote()) return panel;
  const tier = inputControl(`final-tier-${draft.id}`, "number"); tier.min = draft.default_source_tier; tier.max = 9; tier.value = draft.default_source_tier;
  const confirm = inputControl(`publisher-confirm-${draft.id}`, "checkbox");
  const preview = actionButton("Preview canonical observation", async () => {
    try {
      const result = await request(`/review/v1/observation-drafts/${encodeURIComponent(draft.id)}/canonical-preview?final_source_tier=${encodeURIComponent(tier.value)}`);
      panel.dataset.payloadHash = result.canonical_payload_sha256;
      panel.dataset.previewVersion = draft.version;
      panel.dataset.previewTier = tier.value;
      panel.querySelector(".preview-output").textContent = JSON.stringify(result, null, 2);
      showWorkflowMessage(live, "Preview ready for publisher confirmation.");
    } catch (error) { showWorkflowError(live, error); }
  });
  const promote = actionButton("Confirm and promote", () => promoteDraft(data, draft, tier, confirm, panel, live));
  panel.append(labeledControl("Final source tier", tier), labeledControl("Publisher confirmation", confirm), preview, promote, el("pre", "preview-output"));
  return panel;
}

async function promoteDraft(data, draft, tier, confirm, panel, live) {
  if (!confirm.checked) { showWorkflowMessage(live, "Publisher confirmation is required."); return; }
  if (!panel.dataset.payloadHash) { showWorkflowMessage(live, "Preview the canonical observation before promoting."); return; }
  try {
    await request(`/review/v1/observation-drafts/${encodeURIComponent(draft.id)}/promotions`, { method: "POST", body: JSON.stringify({ expected_version: draft.version, canonical_payload_sha256: panel.dataset.payloadHash, idempotency_key: crypto.randomUUID(), final_source_tier: Number(tier.value) }) });
    await loadDetail(data.submission.id); await loadQueue();
  } catch (error) { showWorkflowError(live, error); }
}

function showWorkflowMessage(live, message) { live.replaceChildren(el("p", "workflow-ok", message)); }
function showWorkflowError(live, error) { live.replaceChildren(el("p", "error", error.message)); }

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

const API = "/api/v1";
const DEMO_IDS = ["email_001", "email_003", "email_016", "email_038", "email_059"];

const state = {
  view: "inbox",
  page: 1,
  pageSize: 10,
  total: 0,
  items: [],
  selectedId: null,
  selectedEmail: null,
  comparison: null,
  summary: null,
  loading: false,
  drawerOpen: false,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "Not processed";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function prettyCategory(category) {
  return (category || "Not processed").replaceAll("_", " ");
}

function statusMeta(status) {
  if (status === "OK") return { label: "OK", className: "ok" };
  if (status === "MISMATCH") return { label: "Confirmed mismatch", className: "mismatch" };
  if (status === "NEEDS_REVIEW") return { label: "Needs review", className: "review" };
  return { label: "Not processed", className: "pending" };
}

function confidenceMeta(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) return { label: "—", className: "low" };
  if (value >= 0.85) return { label: `${Math.round(value * 100)}% · high`, className: "high" };
  if (value >= 0.6) return { label: `${Math.round(value * 100)}% · medium`, className: "medium" };
  return { label: `${Math.round(value * 100)}% · low`, className: "low" };
}

function showToast(message, type = "success") {
  const toast = $("#toast");
  toast.textContent = message;
  toast.className = `toast show${type === "error" ? " error" : ""}`;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => { toast.className = "toast"; }, 3500);
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.error?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

function setView(view) {
  state.view = view;
  $$(".view").forEach((panel) => panel.classList.toggle("active", panel.dataset.viewPanel === view));
  $$(".nav-item[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  const labels = { inbox: "Inbox", comparison: "Comparison", review: "Review queue", reports: "Reports" };
  $("#breadcrumb-current").textContent = labels[view] || "Inbox";
  if (view === "review") renderReview();
  if (view === "reports") loadReports();
}

async function refreshInbox() {
  const params = new URLSearchParams({ page: String(state.page), page_size: String(state.pageSize) });
  const search = $("#search-input").value.trim();
  const category = $("#category-filter").value;
  const status = $("#status-filter").value;
  const needsReview = $("#review-filter").value;
  if (search) params.set("search", search);
  if (category) params.set("category", category);
  if (status) params.set("status", status);
  if (needsReview) params.set("needs_review", needsReview);
  const data = await api(`/emails?${params.toString()}`);
  state.items = data.items || [];
  state.total = data.total || 0;
  renderInboxTable();
  updateInboxMetrics(data.total);
  $("#last-sync").textContent = `Synced ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function updateInboxMetrics(total) {
  $("#metric-total").textContent = total ?? "—";
  const documentChecks = state.items.filter((item) => item.category === "BL_COMPARISON").length;
  const reviews = state.items.filter((item) => item.status === "NEEDS_REVIEW" || item.needs_review).length;
  const mismatches = state.items.filter((item) => item.status === "MISMATCH").length;
  $("#metric-document").textContent = documentChecks || (state.summary?.by_category?.BL_COMPARISON ?? "0");
  $("#metric-review").textContent = reviews || (state.summary?.by_status?.NEEDS_REVIEW ?? "0");
  $("#metric-mismatch").textContent = mismatches || (state.summary?.by_status?.MISMATCH ?? "0");
  $("#nav-inbox-count").textContent = total ?? "0";
  $("#nav-review-count").textContent = state.summary?.by_status?.NEEDS_REVIEW ?? reviews ?? "0";
  $("#inbox-caption").textContent = `${total ?? 0} messages · Select a row to inspect the decision`;
}

function renderInboxTable() {
  const body = $("#inbox-table-body");
  if (!state.items.length) {
    body.innerHTML = `<tr><td colspan="7"><div class="empty-card"><div class="empty-icon">⌁</div><h2>No cases match these filters</h2><p>Try clearing a filter or prepare the demo cases to create processed results.</p><button class="button secondary" id="clear-filters">Clear filters</button></div></td></tr>`;
    $("#clear-filters")?.addEventListener("click", clearFilters);
  } else {
    body.innerHTML = state.items.map((item) => {
      const status = statusMeta(item.status);
      const attachmentLabel = item.status ? "Checked" : "Waiting";
      return `<tr class="data-row${state.selectedId === item.id ? " selected" : ""}" data-email-id="${escapeHtml(item.id)}">
        <td><span class="email-id">${escapeHtml(item.source_email_id)}</span><span class="sender-cell">${escapeHtml(item.sender || "Unknown sender")}</span></td>
        <td class="subject-cell" title="${escapeHtml(item.subject)}">${escapeHtml(item.subject || "No subject")}</td>
        <td><span class="category-pill">${escapeHtml(prettyCategory(item.category))}</span></td>
        <td><span class="status-pill ${status.className}">${escapeHtml(status.label)}</span></td>
        <td><span class="attachment-count">${attachmentLabel}</span></td>
        <td class="updated-cell">${escapeHtml(formatDate(item.updated_at))}</td>
        <td><button class="row-action" data-open-id="${escapeHtml(item.id)}">Open →</button></td>
      </tr>`;
    }).join("");
    $$(".data-row").forEach((row) => row.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      openCase(row.dataset.emailId);
    }));
    $$("[data-open-id]").forEach((button) => button.addEventListener("click", () => openCase(button.dataset.openId)));
  }
  const start = state.total ? ((state.page - 1) * state.pageSize) + 1 : 0;
  const end = Math.min(state.page * state.pageSize, state.total);
  $("#pagination-label").textContent = state.total ? `Showing ${start}–${end} of ${state.total}` : "No results";
  $("#prev-page").disabled = state.page <= 1;
  $("#next-page").disabled = end >= state.total;
  $("#selection-label").textContent = state.selectedId ? `${state.selectedId} selected` : "No case selected";
}

function clearFilters() {
  $("#search-input").value = "";
  $("#category-filter").value = "";
  $("#status-filter").value = "";
  $("#review-filter").value = "";
  state.page = 1;
  refreshInbox().catch(showError);
}

async function openCase(emailId) {
  state.selectedId = emailId;
  $("#process-selected-top").disabled = false;
  setView("comparison");
  $("#comparison-content").innerHTML = `<div class="loading-state"><span class="spinner"></span> Reading case evidence…</div>`;
  try {
    state.selectedEmail = await api(`/emails/${encodeURIComponent(emailId)}`);
    try { state.comparison = await api(`/emails/${encodeURIComponent(emailId)}/comparison`); }
    catch { state.comparison = null; }
    renderComparison();
    renderInboxTable();
  } catch (error) {
    showError(error);
  }
}

function renderComparison() {
  const email = state.selectedEmail;
  if (!email) return;
  const status = statusMeta(email.status);
  const comparison = state.comparison;
  $("#comparison-title").textContent = email.source_email_id;
  $("#comparison-subtitle").textContent = email.subject || "No subject";
  $("#comparison-actions").innerHTML = `<button class="button secondary" id="comparison-process">${comparison ? "Reprocess" : "Process case"}</button><button class="button secondary" id="comparison-process-ai">AI assist</button><button class="button primary" id="open-review-button">${email.status === "NEEDS_REVIEW" ? "Review case" : "Open review"}</button>`;
  $("#comparison-process").addEventListener("click", () => processSelected(false));
  $("#comparison-process-ai").addEventListener("click", () => processSelected(true));
  $("#open-review-button").addEventListener("click", () => { setView("review"); renderReview(); });

  const summaryText = comparison?.review_reason ? `Escalated because ${comparison.review_reason.replaceAll("_", " ")}.` : comparison?.machine_status === "MISMATCH" ? `Confirmed differences were found in ${(comparison.defect_fields || []).join(", ") || "the comparison"}.` : comparison ? "The normalized document values agree across the checked fields." : "This case has not been processed through the backend yet.";
  const attachments = (email.attachments || []).map((attachment) => `<div class="attachment-item"><span class="attachment-name" title="${escapeHtml(attachment.filename)}">▧ ${escapeHtml(attachment.filename)}</span><button class="button ghost attachment-preview" data-attachment-id="${escapeHtml(attachment.id)}">View evidence</button></div>`).join("");
  const header = `<div class="case-header"><article class="case-summary ${status.className === "review" ? "review-state" : status.className === "mismatch" ? "mismatch-state" : ""}"><p class="eyebrow">${escapeHtml(prettyCategory(email.category))}</p><h2>${escapeHtml(email.subject || "No subject")}</h2><p>${escapeHtml(summaryText)}</p><div class="summary-pills"><span class="status-pill ${status.className}">${escapeHtml(status.label)}</span>${email.needs_review ? "<span class=\"confidence-pill medium\">Reviewer attention</span>" : ""}<span class="category-pill">${escapeHtml(email.sender || "Unknown sender")}</span></div></article><article class="case-side-card"><h3>Case details</h3><div class="meta-list"><div class="meta-row"><span>Source email</span><strong>${escapeHtml(email.source_email_id)}</strong></div><div class="meta-row"><span>Last updated</span><strong>${escapeHtml(formatDate(email.updated_at))}</strong></div><div class="meta-row"><span>Machine result</span><strong>${escapeHtml(status.label)}</strong></div></div><div class="attachment-list">${attachments || "<span class=\"value-empty\">No attachments found</span>"}</div></article></div>`;
  if (!comparison) {
    $("#comparison-content").innerHTML = `${header}<div class="empty-card"><div class="empty-icon">↗</div><h2>Processing required</h2><p>Run the case through the backend to populate the seven-field comparison and source evidence.</p><button class="button primary" id="empty-process-button">Process this case</button></div>`;
    $("#empty-process-button").addEventListener("click", () => processSelected(false));
  } else if (!comparison.fields) {
    $("#comparison-content").innerHTML = `${header}<div class="empty-card"><div class="empty-icon">✓</div><h2>No document comparison</h2><p>This message was routed to <strong>${escapeHtml(prettyCategory(email.category))}</strong>, so no SI/BL comparison is expected.</p></div>`;
  } else {
    const rows = comparison.fields.map((field) => {
      const fieldStatus = statusMeta(field.result === "MATCH" ? "OK" : field.result === "MISMATCH" ? "MISMATCH" : "NEEDS_REVIEW");
      const confidence = confidenceMeta(field.confidence);
      return `<tr><td>${escapeHtml(field.field_name.replaceAll("_", " "))}</td><td>${renderValue(field.si)} </td><td>${renderValue(field.bl)} </td><td><div class="result-cell"><span class="status-pill ${fieldStatus.className}">${escapeHtml(field.result)}</span><span class="confidence-pill ${confidence.className}">${escapeHtml(confidence.label)}</span><p class="explanation">${escapeHtml(field.explanation)}</p></div></td><td><button class="table-action" data-field-name="${escapeHtml(field.field_name)}">View evidence</button></td></tr>`;
    }).join("");
    $("#comparison-content").innerHTML = `${header}<article class="comparison-panel"><div class="comparison-heading"><div><h2>Seven-field comparison</h2><p>Rule-based normalization remains the final decision authority.</p></div><span class="status-pill ${status.className}">${escapeHtml(comparison.defect_fields?.length ? `${comparison.defect_fields.length} field${comparison.defect_fields.length === 1 ? "" : "s"} to inspect` : "All fields checked")}</span></div><div class="table-scroll"><table class="comparison-table"><thead><tr><th scope="col">Field</th><th scope="col">SI reference</th><th scope="col">BL value</th><th scope="col">Result / confidence</th><th scope="col">Evidence</th></tr></thead><tbody>${rows}</tbody></table></div></article>`;
    $$(`[data-field-name]`).forEach((button) => button.addEventListener("click", () => openEvidence(button.dataset.fieldName)));
  }
  $$(".attachment-preview").forEach((button) => button.addEventListener("click", () => openAttachmentPreview(button.dataset.attachmentId)));
}

function renderValue(value) {
  if (!value || (!value.raw_value && !value.normalized_value)) return `<span class="value-empty">Not available</span>`;
  return `<div class="value-raw">${escapeHtml(value.raw_value || "Not available")}</div><div class="value-normalized">${escapeHtml(value.normalized_value || "No normalized value")}</div>`;
}

function renderReview() {
  const root = $("#review-content");
  if (!state.selectedEmail) {
    root.innerHTML = `<div class="empty-card"><div class="empty-icon">◈</div><h2>No case selected</h2><p>Open a case from the inbox to review its reason, evidence, and machine result.</p><button class="button primary" id="open-first-review">Find a review case</button></div>`;
    $("#open-first-review").addEventListener("click", findFirstReview);
    return;
  }
  const email = state.selectedEmail;
  const comparison = state.comparison;
  const reason = comparison?.review_reason || (email.status === "NEEDS_REVIEW" ? "The comparison needs operator attention before release." : "This case has a machine result available for human confirmation.");
  const fields = comparison?.fields || [];
  const evidence = fields.filter((field) => field.result !== "MATCH").slice(0, 3).map((field) => `<div class="machine-note"><strong>${escapeHtml(field.field_name.replaceAll("_", " "))}</strong><br>${escapeHtml(field.explanation || "Review the source evidence for this field.")}<br><button class="button ghost" data-review-field="${escapeHtml(field.field_name)}">View field evidence →</button></div>`).join("") || `<div class="machine-note">No field-level discrepancy is currently recorded. Confirm the machine result if the source documents support it.</div>`;
  root.innerHTML = `<div class="review-panel"><div><div class="review-reason"><h3>Why this case is here</h3><p>${escapeHtml(reason.replaceAll("_", " "))}</p></div><div class="review-evidence"><h2>Evidence before action</h2><p class="lede">The original machine output remains preserved. Inspect the relevant excerpts before choosing a final status.</p><div class="form-stack">${evidence}</div></div></div><div><div class="form-stack"><label class="form-label">Decision<select id="review-decision"><option value="CONFIRMED">Confirm machine result</option><option value="OVERRIDDEN">Override result</option><option value="UNRESOLVED">Leave unresolved</option></select></label><label class="form-label">Final status<select id="review-status"><option value="OK">OK</option><option value="MISMATCH">MISMATCH</option><option value="NEEDS_REVIEW">NEEDS_REVIEW</option></select></label><label class="form-label">Reason<textarea id="review-reason" placeholder="Explain what you confirmed or changed…"></textarea></label><div class="review-actions"><button class="button primary" id="save-review">Save review decision</button><button class="button secondary" id="review-retry">Retry processing</button></div><p class="machine-note">Reviewer decisions are appended to the case history. They do not overwrite the original machine result.</p></div></div></div>`;
  $("#review-status").value = email.status === "MISMATCH" ? "MISMATCH" : email.status === "OK" ? "OK" : "NEEDS_REVIEW";
  $$(`[data-review-field]`).forEach((button) => button.addEventListener("click", () => openEvidence(button.dataset.reviewField)));
  $("#save-review").addEventListener("click", saveReview);
  $("#review-retry").addEventListener("click", () => processSelected(false));
}

async function saveReview() {
  const reason = $("#review-reason").value.trim();
  if (!reason) { showToast("Add a short reason before saving the review.", "error"); $("#review-reason").focus(); return; }
  try {
    await api(`/emails/${encodeURIComponent(state.selectedId)}/review`, { method: "POST", body: JSON.stringify({ decision: $("#review-decision").value, corrected_status: $("#review-status").value, corrected_fields: [], reason }) });
    showToast("Review decision saved.");
    await openCase(state.selectedId);
    setView("review");
    renderReview();
    await refreshInbox();
  } catch (error) { showError(error); }
}

async function processSelected(useAi = false) {
  if (!state.selectedId) return;
  const button = $("#comparison-process") || $("#process-selected-top");
  if (button) { button.disabled = true; button.innerHTML = `<span class="spinner"></span> Processing`; }
  try {
    const response = await api(`/emails/${encodeURIComponent(state.selectedId)}/process`, { method: "POST", body: JSON.stringify({ force: true, use_ai: useAi }) });
    const job = await waitForJob(response.job_id);
    if (job.status === "FAILED") throw new Error(job.error_message || "Processing failed");
    showToast("Case processed. The comparison is ready.");
    await openCase(state.selectedId);
    await refreshInbox();
    await loadReports();
  } catch (error) { showError(error); }
  finally { if (button) { button.disabled = false; button.textContent = "Reprocess"; } }
}

async function waitForJob(jobId) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const job = await api(`/jobs/${encodeURIComponent(jobId)}`);
    if (job.status === "SUCCEEDED" || job.status === "FAILED") return job;
    await new Promise((resolve) => setTimeout(resolve, 180));
  }
  throw new Error("The processing job is taking longer than expected. Refresh the case to check progress.");
}

async function prepareDemo() {
  const button = $("#prepare-demo-button");
  button.disabled = true;
  button.innerHTML = `<span class="spinner"></span> Preparing cases`;
  try {
    for (const emailId of DEMO_IDS) {
      const response = await api(`/emails/${emailId}/process`, { method: "POST", body: JSON.stringify({ force: true, use_ai: false }) });
      const job = await waitForJob(response.job_id);
      if (job.status === "FAILED") throw new Error(`${emailId}: ${job.error_message || "processing failed"}`);
    }
    showToast("Five demo cases are ready: match, mismatch, review, and non-document routes.");
    await refreshInbox();
    await loadReports();
  } catch (error) { showError(error); }
  finally { button.disabled = false; button.textContent = "Prepare demo cases"; }
}

async function findFirstReview() {
  try {
    const data = await api(`/emails?needs_review=true&page_size=1`);
    if (!data.items?.length) { showToast("No processed review case is available yet. Prepare the demo cases first.", "error"); return; }
    await openCase(data.items[0].id);
    setView("review");
    renderReview();
  } catch (error) { showError(error); }
}

async function loadReports() {
  try {
    state.summary = await api("/reports/summary");
    renderReports();
  } catch (error) { showError(error); }
}

function renderReports() {
  const summary = state.summary || {};
  const status = summary.by_status || {};
  const categories = summary.by_category || {};
  const reasons = summary.by_review_reason || {};
  const total = Math.max(summary.processed_emails || 0, 1);
  const breakdown = (data, tone = "") => Object.entries(data).sort((a, b) => b[1] - a[1]).map(([key, value]) => `<div class="breakdown-row"><span>${escapeHtml(key.replaceAll("_", " "))}</span><span class="bar-track"><span class="bar-fill ${tone}" style="width:${Math.max(4, Math.round((value / total) * 100))}%"></span></span><span class="bar-number">${value}</span></div>`).join("") || `<p>No processed results yet.</p>`;
  $("#reports-content").innerHTML = `<div class="report-grid"><article class="report-card"><h3>Messages processed</h3><strong class="report-big">${summary.processed_emails ?? 0}</strong><p>of ${summary.total_emails ?? 0} loaded emails</p></article><article class="report-card"><h3>Processing health</h3><strong class="report-big">${summary.processing?.failed ?? 0}</strong><p>failed jobs · ${summary.processing?.succeeded ?? 0} succeeded</p></article><article class="report-card"><h3>Review actions</h3><strong class="report-big">${summary.reviews_recorded ?? 0}</strong><p>human decisions recorded</p></article></div><div class="report-columns"><article class="report-card"><h2>Routing distribution</h2><p>How the inbox is being classified.</p><div class="breakdown">${breakdown(categories, "")}</div></article><article class="report-card"><h2>Outcome distribution</h2><p>What requires an operational response.</p><div class="breakdown">${breakdown(status, "teal")}</div></article></div><article class="report-card" style="margin-top:15px"><h2>Review reasons</h2><p>Why the engine chose not to guess.</p><div class="breakdown">${breakdown(reasons, "amber")}</div></article>`;
}

async function exportReport() {
  try {
    const data = await api("/reports/export?format=json");
    const blob = new Blob([JSON.stringify(data.items, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "cargoclarity-evaluation.json";
    link.click();
    URL.revokeObjectURL(url);
    showToast("Evaluation JSON downloaded.");
  } catch (error) { showError(error); }
}

async function openEvidence(fieldName) {
  const field = (state.comparison?.fields || []).find((candidate) => candidate.field_name === fieldName);
  if (!field) return;
  $("#drawer-title").textContent = field.field_name.replaceAll("_", " ");
  $("#drawer-content").innerHTML = `<div class="drawer-meta"><span>Result <strong>${escapeHtml(field.result)}</strong></span><span>Method <strong>${escapeHtml(field.comparison_method || "Rule comparison")}</strong></span><span>Confidence <strong>${escapeHtml(confidenceMeta(field.confidence).label)}</strong></span></div><div class="evidence-block"><h3>Why this result</h3><p>${escapeHtml(field.explanation || "No explanation was recorded.")}</p></div>${renderEvidenceBlock("Shipping Instructions (SI)", field.si)}${renderEvidenceBlock("Bill of Lading (BL)", field.bl)}`;
  openDrawer();
}

function renderEvidenceBlock(label, value) {
  if (!value) return `<div class="evidence-block"><h3>${escapeHtml(label)}</h3><p class="value-empty">No extracted value available.</p></div>`;
  return `<div class="evidence-block"><h3>${escapeHtml(label)}</h3><p class="evidence-quote">${escapeHtml(value.evidence_excerpt || "No source excerpt recorded.")}</p><div class="drawer-meta"><span>Raw value <strong>${escapeHtml(value.raw_value || "—")}</strong></span><span>Normalized <strong>${escapeHtml(value.normalized_value || "—")}</strong></span><span>Method <strong>${escapeHtml(value.extraction_method || "RULE")}</strong></span></div></div>`;
}

async function openAttachmentPreview(attachmentId) {
  try {
    const data = await api(`/emails/${encodeURIComponent(state.selectedId)}/attachments/${encodeURIComponent(attachmentId)}/preview`);
    $("#drawer-title").textContent = data.filename || "Attachment evidence";
    $("#drawer-content").innerHTML = `<div class="drawer-meta"><span>Parser <strong>${escapeHtml(data.parser_name || "—")}</strong></span><span>Readability <strong>${escapeHtml(data.readability_status || "—")}</strong></span></div><div class="evidence-block"><h3>Source excerpt</h3><p class="evidence-quote">${escapeHtml(data.text_excerpt || "No readable text was found.")}</p></div>`;
    openDrawer();
  } catch (error) { showError(error); }
}

function openDrawer() {
  const drawer = $("#evidence-drawer");
  $("#drawer-backdrop").hidden = false;
  requestAnimationFrame(() => $("#drawer-backdrop").classList.add("visible"));
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  state.drawerOpen = true;
}

function closeDrawer() {
  const drawer = $("#evidence-drawer");
  $("#drawer-backdrop").classList.remove("visible");
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  window.setTimeout(() => { $("#drawer-backdrop").hidden = true; }, 220);
  state.drawerOpen = false;
}

function showError(error) {
  console.error(error);
  showToast(error.message || "Something went wrong. Try again.", "error");
}

async function boot() {
  $$("[data-view]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  ["#search-input", "#category-filter", "#status-filter", "#review-filter"].forEach((selector) => $(selector).addEventListener("change", () => { state.page = 1; refreshInbox().catch(showError); }));
  $("#search-input").addEventListener("input", () => { window.clearTimeout(boot.searchTimer); boot.searchTimer = window.setTimeout(() => { state.page = 1; refreshInbox().catch(showError); }, 260); });
  $("#prev-page").addEventListener("click", () => { if (state.page > 1) { state.page -= 1; refreshInbox().catch(showError); } });
  $("#next-page").addEventListener("click", () => { if (state.page * state.pageSize < state.total) { state.page += 1; refreshInbox().catch(showError); } });
  $("#refresh-button").addEventListener("click", () => { refreshInbox().catch(showError); loadReports().catch(showError); });
  $("#prepare-demo-button").addEventListener("click", prepareDemo);
  $("#process-selected-top").addEventListener("click", () => processSelected(false));
  $("#review-refresh").addEventListener("click", findFirstReview);
  $("#export-button").addEventListener("click", exportReport);
  $("#close-drawer").addEventListener("click", closeDrawer);
  $("#drawer-backdrop").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && state.drawerOpen) closeDrawer(); });
  try {
    await api("/health");
    $("#sidebar-health").textContent = "API connected";
    await refreshInbox();
    await loadReports();
  } catch (error) {
    $("#sidebar-health").textContent = "API unavailable";
    $("#inbox-table-body").innerHTML = `<tr><td colspan="7"><div class="error-card"><h2>Backend unavailable</h2><p>Start <code>cargoclarity-api</code> in Terminal, then refresh this page.</p></div></td></tr>`;
    showError(error);
  }
}

document.addEventListener("DOMContentLoaded", boot);

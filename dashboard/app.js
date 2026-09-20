const API = "/api/v1";

const state = {
  view: "inbox",
  page: 1,
  pageSize: 15,
  total: 0,
  items: [],
  summary: null,
  selectedId: null,
  email: null,
  comparison: null,
  reviewQueue: [],
  audit: [],
  batchTimer: null,
  drawerOpen: false,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function label(value, fallback = "Not processed") {
  return value ? String(value).replaceAll("_", " ") : fallback;
}

function shortDate(value) {
  if (!value) return "Not processed";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function statusMeta(value) {
  if (value === "OK" || value === "MATCH") return { css: "ok", text: value === "MATCH" ? "Match" : "OK" };
  if (value === "MISMATCH") return { css: "mismatch", text: "Mismatch" };
  if (value === "NEEDS_REVIEW" || value === "UNCERTAIN") return { css: "review", text: value === "UNCERTAIN" ? "Uncertain" : "Needs review" };
  return { css: "pending", text: "Not processed" };
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.message || `Request failed (${response.status})`);
  return payload;
}

function toast(message, type = "success") {
  const element = $("#toast");
  element.textContent = message;
  element.className = `toast show${type === "error" ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { element.className = "toast"; }, 3600);
}

function showError(error) {
  console.error(error);
  toast(error?.message || "The operation could not be completed.", "error");
}

function setView(view) {
  state.view = view;
  $$("[data-screen]").forEach((screen) => screen.classList.toggle("active", screen.dataset.screen === view));
  $$(".nav-link[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  const names = { inbox: "Verification inbox", comparison: "Decision record", review: "Review queue", audit: "Audit trail", reports: "Operations report" };
  $("#header-context").textContent = names[view] || names.inbox;
  if (view === "review") loadReviewQueue();
  if (view === "audit") loadAudit();
  if (view === "reports") loadReports();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadHealth() {
  const health = await api("/health");
  const ai = health.dependencies?.ai || "degraded";
  $("#system-state").className = `system-state ${health.status === "ok" ? "ok" : "degraded"}`;
  $("#system-state span").textContent = health.status === "ok" ? "System ready" : "System degraded";
  $("#ai-mode").textContent = ai === "configured" ? "Available" : "Degraded";
  return health;
}

function inboxParams() {
  const params = new URLSearchParams({ page: String(state.page), page_size: String(state.pageSize) });
  const search = $("#search-input").value.trim();
  const category = $("#category-filter").value;
  const outcome = $("#status-filter").value;
  const review = $("#review-filter").value;
  if (search) params.set("search", search);
  if (category) params.set("category", category);
  if (outcome) params.set("status", outcome);
  if (review) params.set("needs_review", review);
  return params;
}

async function loadInbox() {
  const data = await api(`/emails?${inboxParams().toString()}`);
  state.items = data.items || [];
  state.total = data.total || 0;
  renderInbox();
}

async function loadSummary() {
  state.summary = await api("/reports/summary");
  renderSummary();
}

function renderSummary() {
  const summary = state.summary || {};
  const total = summary.total_emails || 0;
  const processed = summary.processed_emails || 0;
  const reviews = summary.by_status?.NEEDS_REVIEW || 0;
  const defects = summary.by_status?.MISMATCH || 0;
  $("#stat-total").textContent = total.toLocaleString();
  $("#stat-processed").textContent = processed.toLocaleString();
  $("#stat-processed-note").textContent = total ? `${Math.round((processed / total) * 100)}% coverage` : "waiting for data";
  $("#stat-review").textContent = reviews.toLocaleString();
  $("#stat-defects").textContent = defects.toLocaleString();
  $("#nav-inbox-count").textContent = total.toLocaleString();
  $("#nav-review-count").textContent = reviews.toLocaleString();
}

function renderInbox() {
  const body = $("#inbox-body");
  if (!state.items.length) {
    body.innerHTML = `<tr><td colspan="6"><div class="blank-state"><span>NO RESULTS</span><h2>No messages match the current filters.</h2><button class="btn secondary" id="clear-filters" type="button">Clear filters</button></div></td></tr>`;
    $("#clear-filters")?.addEventListener("click", clearFilters);
  } else {
    body.innerHTML = state.items.map((item) => {
      const status = statusMeta(item.status);
      return `<tr data-email-id="${escapeHtml(item.id)}" class="${state.selectedId === item.id ? "selected" : ""}">
        <td class="email-cell"><strong>${escapeHtml(item.source_email_id)}</strong><span>${escapeHtml(item.sender || "Unknown sender")}</span></td>
        <td class="message-cell"><strong title="${escapeHtml(item.subject)}">${escapeHtml(item.subject || "No subject")}</strong><span>${item.review_count ? `${item.review_count} review decision${item.review_count === 1 ? "" : "s"}` : "No human decision"}</span></td>
        <td><span class="route-label">${escapeHtml(label(item.category))}</span></td>
        <td><span class="outcome ${status.css}">${escapeHtml(status.text)}</span></td>
        <td><span class="audit-muted">${escapeHtml(shortDate(item.updated_at))}</span></td>
        <td><button class="open-case" type="button" data-open="${escapeHtml(item.id)}">Inspect →</button></td>
      </tr>`;
    }).join("");
    $$("#inbox-body tr[data-email-id]").forEach((row) => row.addEventListener("click", (event) => {
      if (!event.target.closest("button")) openCase(row.dataset.emailId);
    }));
    $$("[data-open]").forEach((button) => button.addEventListener("click", () => openCase(button.dataset.open)));
  }
  const start = state.total ? ((state.page - 1) * state.pageSize) + 1 : 0;
  const end = Math.min(state.page * state.pageSize, state.total);
  $("#inbox-range").textContent = state.total ? `${start}–${end} of ${state.total}` : "No results";
  $("#prev-page").disabled = state.page === 1;
  $("#next-page").disabled = end >= state.total;
}

function clearFilters() {
  $("#search-input").value = "";
  $("#category-filter").value = "";
  $("#status-filter").value = "";
  $("#review-filter").value = "";
  state.page = 1;
  loadInbox().catch(showError);
}

async function openCase(emailId, targetView = "comparison") {
  state.selectedId = emailId;
  $("#process-selected").disabled = false;
  setView(targetView);
  if (targetView === "comparison") $("#case-content").innerHTML = `<div class="loading-row"><i></i>Loading decision record</div>`;
  try {
    state.email = await api(`/emails/${encodeURIComponent(emailId)}`);
    try { state.comparison = await api(`/emails/${encodeURIComponent(emailId)}/comparison`); }
    catch { state.comparison = null; }
    if (targetView === "comparison") renderCase();
    if (targetView === "review") renderReviewDetail();
    renderInbox();
  } catch (error) { showError(error); }
}

function verdictMessage(email, comparison) {
  if (!comparison) return "Processing is required before a decision can be issued.";
  if (comparison.comparison === null) return `This message was routed to ${label(email.category)}; no document comparison is required.`;
  if (comparison.status === "MISMATCH") return `A confirmed variance was found in ${(comparison.defect_fields || []).map(label).join(", ") || "the document pair"}.`;
  if (comparison.status === "NEEDS_REVIEW") return `The engine stopped safely because ${label(comparison.review_reason, "the evidence was not dependable").toLowerCase()}.`;
  return "No mismatch detected across the seven verified shipment fields.";
}

function renderCase() {
  const email = state.email;
  if (!email) return;
  const comparison = state.comparison;
  const status = statusMeta(email.effective_status || email.status);
  $("#case-kicker").textContent = `${label(email.category)} / ${email.source_email_id}`;
  $("#case-title").textContent = email.subject || "No subject";
  $("#case-subtitle").textContent = `${email.sender || "Unknown sender"} · ${email.attachments?.length || 0} attachment${email.attachments?.length === 1 ? "" : "s"}`;
  $("#case-actions").innerHTML = `<button class="btn secondary" id="run-rules" type="button">${comparison ? "Run rules again" : "Run verification"}</button><button class="btn secondary" id="run-ai" type="button">Use AI assist</button>${email.status === "NEEDS_REVIEW" ? '<button class="btn primary" id="go-review" type="button">Review case</button>' : ""}`;
  $("#run-rules").addEventListener("click", () => processCase(false));
  $("#run-ai").addEventListener("click", () => processCase(true));
  $("#go-review")?.addEventListener("click", () => openCase(email.id, "review"));

  const machineStatus = statusMeta(email.machine_status);
  const attachments = (email.attachments || []).map((file) => `<div class="attachment-row"><span title="${escapeHtml(file.filename)}">${escapeHtml(file.filename)}</span><button class="evidence-link" type="button" data-attachment="${escapeHtml(file.id)}">Preview</button></div>`).join("") || `<span class="value-empty">No attachments</span>`;
  const verdict = `<div class="verdict-band ${status.css}"><div class="verdict-signal"></div><div class="verdict-copy"><p class="kicker">EFFECTIVE DECISION</p><h2>${escapeHtml(status.text)}</h2><p>${escapeHtml(verdictMessage(email, comparison))}</p></div><div class="verdict-meta"><div class="meta-line"><span>Machine result</span><strong>${escapeHtml(machineStatus.text)}</strong></div><div class="meta-line"><span>Effective result</span><strong>${escapeHtml(status.text)}</strong></div><div class="meta-line"><span>Human decisions</span><strong>${email.review_count || 0}</strong></div><div class="meta-line"><span>Completed</span><strong>${escapeHtml(shortDate(email.updated_at))}</strong></div></div></div>`;

  let main;
  if (!comparison) {
    main = `<div class="blank-state"><span>NOT PROCESSED</span><h2>Run verification to classify this message and inspect the source documents.</h2><button class="btn primary" id="blank-process" type="button">Run verification</button></div>`;
  } else if (comparison.comparison === null || !comparison.fields) {
    main = `<div class="blank-state"><span>${escapeHtml(label(email.category))}</span><h2>This message was routed successfully. Document comparison is not required.</h2><button class="btn secondary" type="button" data-view="inbox">Return to inbox</button></div>`;
  } else {
    const rows = comparison.fields.map((field) => {
      const result = statusMeta(field.result);
      const confidence = Number.isFinite(Number(field.confidence)) ? `${Math.round(Number(field.confidence) * 100)}%` : "—";
      return `<tr><td><span class="field-name">${escapeHtml(label(field.field_name))}</span></td><td>${renderValue(field.si)}</td><td>${renderValue(field.bl)}</td><td><div class="result-stack"><span class="outcome ${result.css}">${escapeHtml(result.text)}</span><small>${confidence} confidence<br>${escapeHtml(field.explanation || "")}</small></div></td><td><button class="evidence-link" type="button" data-field="${escapeHtml(field.field_name)}">Open evidence</button></td></tr>`;
    }).join("");
    main = `<section class="comparison-surface"><div class="surface-title"><div><h3>Field assurance record</h3><p>Shipping Instructions are the reference. Formatting-only differences are normalized before comparison.</p></div><span class="outcome ${status.css}">${(comparison.defect_fields || []).length} defects</span></div><div class="table-frame"><table class="comparison-table"><thead><tr><th>Field</th><th>Shipping Instructions</th><th>Draft Bill of Lading</th><th>Decision</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
  }

  $("#case-content").innerHTML = `${verdict}<div class="case-grid"><div>${main}</div><aside class="case-aside"><section class="aside-section"><h3>Decision provenance</h3><div class="machine-human"><div class="state-row"><span>Category</span><strong>${escapeHtml(label(email.category))}</strong></div><div class="state-row"><span>Run ID</span><strong>${escapeHtml(email.latest_run?.id?.slice(0, 8) || "—")}</strong></div><div class="state-row"><span>AI provider</span><strong>${escapeHtml(email.latest_run?.provider || "Rules only")}</strong></div><div class="state-row"><span>Review status</span><strong>${email.review ? escapeHtml(label(email.review.decision)) : "Unreviewed"}</strong></div></div></section><section class="aside-section"><h3>Source documents</h3>${attachments}</section><section class="aside-section"><h3>Assurance principle</h3><p class="audit-muted">Missing or unreliable evidence is escalated. It is never converted into a false mismatch.</p></section></aside></div>`;
  $("#blank-process")?.addEventListener("click", () => processCase(false));
  $$(`[data-view]`, $("#case-content")).forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $$(`[data-field]`).forEach((button) => button.addEventListener("click", () => openFieldEvidence(button.dataset.field)));
  $$(`[data-attachment]`).forEach((button) => button.addEventListener("click", () => openAttachment(button.dataset.attachment)));
}

function renderValue(value) {
  if (!value || (!value.raw_value && !value.normalized_value)) return `<span class="value-empty">Not available</span>`;
  return `<div class="value-main">${escapeHtml(value.raw_value || "Not available")}</div><div class="value-normal">${escapeHtml(value.normalized_value || "No normalized value")}</div>`;
}

async function processCase(useAi) {
  if (!state.selectedId) return;
  const buttons = [$("#run-rules"), $("#run-ai"), $("#process-selected")].filter(Boolean);
  buttons.forEach((button) => { button.disabled = true; });
  try {
    const accepted = await api(`/emails/${encodeURIComponent(state.selectedId)}/process`, { method: "POST", body: JSON.stringify({ force: true, use_ai: useAi }) });
    const job = await waitForJob(accepted.job_id);
    if (job.status === "FAILED") throw new Error(job.error_message || "Processing failed");
    toast(useAi ? "AI assistance completed with deterministic safeguards." : "Verification completed.");
    await Promise.all([openCase(state.selectedId), loadSummary()]);
  } catch (error) { showError(error); }
  finally { buttons.forEach((button) => { button.disabled = false; }); }
}

async function waitForJob(jobId) {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    const job = await api(`/jobs/${encodeURIComponent(jobId)}`);
    if (["SUCCEEDED", "FAILED"].includes(job.status)) return job;
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error("Processing is still running. Refresh the decision record in a moment.");
}

async function verifyInbox() {
  const button = $("#run-inbox");
  button.disabled = true;
  try {
    const accepted = await api("/batches/process", { method: "POST", body: JSON.stringify({ force: false, use_ai: false }) });
    if (!accepted.total) {
      toast("The entire inbox is already verified.");
      return;
    }
    showBatch({ status: "QUEUED", total: accepted.total, processed: 0, progress: 0 });
    clearInterval(state.batchTimer);
    state.batchTimer = setInterval(async () => {
      try {
        const batch = await api(`/batches/${encodeURIComponent(accepted.batch_id)}`);
        showBatch(batch);
        if (["SUCCEEDED", "COMPLETED_WITH_ERRORS"].includes(batch.status)) {
          clearInterval(state.batchTimer);
          state.batchTimer = null;
          button.disabled = false;
          toast(batch.failed ? `Inbox verified with ${batch.failed} failures.` : "The complete inbox is verified.", batch.failed ? "error" : "success");
          await Promise.all([loadInbox(), loadSummary(), loadAudit()]);
          setTimeout(() => { $("#batch-banner").hidden = true; }, 2400);
        }
      } catch (error) {
        clearInterval(state.batchTimer);
        state.batchTimer = null;
        button.disabled = false;
        showError(error);
      }
    }, 500);
  } catch (error) {
    button.disabled = false;
    showError(error);
  }
}

function showBatch(batch) {
  const banner = $("#batch-banner");
  banner.hidden = false;
  $("#batch-title").textContent = batch.status === "QUEUED" ? "Verification queued" : "Verifying inbox";
  $("#batch-detail").textContent = `${batch.processed || 0} of ${batch.total || 0} messages · ${batch.failed || 0} failures`;
  $("#batch-progress-bar").style.width = `${batch.progress || 0}%`;
  $("#batch-percentage").textContent = `${batch.progress || 0}%`;
}

async function loadReviewQueue() {
  try {
    const firstPage = await api("/emails?needs_review=true&page=1&page_size=100");
    const pages = Math.ceil((firstPage.total || 0) / 100);
    const remaining = pages > 1
      ? await Promise.all(Array.from({ length: pages - 1 }, (_, index) => api(`/emails?needs_review=true&page=${index + 2}&page_size=100`)))
      : [];
    state.reviewQueue = [firstPage, ...remaining].flatMap((page) => page.items || []);
    renderReviewList();
    if (!state.email || state.email.status !== "NEEDS_REVIEW") {
      if (state.reviewQueue.length) await openCase(state.reviewQueue[0].id, "review");
      else renderReviewDetail();
    } else {
      renderReviewDetail();
    }
  } catch (error) { showError(error); }
}

function renderReviewList() {
  $("#review-list-count").textContent = state.reviewQueue.length;
  const root = $("#review-list-body");
  if (!state.reviewQueue.length) {
    root.innerHTML = `<div class="blank-state"><span>CLEAR</span><h2>No cases are awaiting review.</h2></div>`;
    return;
  }
  root.innerHTML = state.reviewQueue.map((item) => `<button class="review-case ${state.selectedId === item.id ? "active" : ""}" type="button" data-review-id="${escapeHtml(item.id)}"><strong>${escapeHtml(item.source_email_id)}</strong><span>${escapeHtml(item.subject || "No subject")}</span><small>${escapeHtml(label(item.category))}</small></button>`).join("");
  $$("[data-review-id]").forEach((button) => button.addEventListener("click", () => openCase(button.dataset.reviewId, "review")));
}

async function renderReviewDetail() {
  const root = $("#review-detail");
  if (!state.email || !state.selectedId) {
    root.innerHTML = `<div class="blank-state"><span>REVIEW</span><h2>Select a case to read the reason and evidence.</h2></div>`;
    return;
  }
  const email = state.email;
  const comparison = state.comparison;
  const reason = comparison?.review_reason || "Manual assurance check requested";
  const fields = (comparison?.fields || []).filter((field) => field.result !== "MATCH");
  let history = [];
  try { history = (await api(`/emails/${encodeURIComponent(email.id)}/reviews`)).items || []; }
  catch { history = []; }
  const evidence = fields.map((field) => `<div class="evidence-callout"><strong>${escapeHtml(label(field.field_name))} · ${escapeHtml(label(field.result))}</strong><p>${escapeHtml(field.explanation || "Inspect the source excerpt before deciding.")}</p><button class="evidence-link" type="button" data-review-field="${escapeHtml(field.field_name)}">Read source evidence</button></div>`).join("") || `<div class="evidence-callout"><strong>Case-level evidence</strong><p>The case requires a human decision. Read the attachment previews before recording an outcome.</p>${(email.attachments || []).map((file) => `<button class="evidence-link" type="button" data-review-attachment="${escapeHtml(file.id)}">Preview ${escapeHtml(file.filename)}</button>`).join("<br>")}</div>`;
  const timeline = history.length ? `<ul class="timeline">${history.map((item) => `<li><strong>${escapeHtml(label(item.decision))}: ${escapeHtml(label(item.old_effective_status))} → ${escapeHtml(label(item.new_effective_status))}</strong><span>${escapeHtml(item.reviewer_name)} · ${escapeHtml(shortDate(item.created_at))}</span><span>${escapeHtml(item.reason)}</span></li>`).join("")}</ul>` : `<p class="audit-muted">No human decision has been recorded.</p>`;
  root.innerHTML = `<div class="review-layout"><div><div class="review-reason"><span>WHY THE ENGINE STOPPED</span><h2>${escapeHtml(label(reason))}</h2><p>Review the evidence below. CargoClarity does not infer missing values or convert parser uncertainty into a defect.</p></div><h3>Evidence requiring judgement</h3>${evidence}<section class="audit-preview"><h3>Human decision history</h3>${timeline}</section></div><form class="review-form" id="review-form"><label>Reviewer<input id="reviewer-name" type="text" value="Demo Reviewer" maxlength="120" required /></label><label>Decision<select id="review-decision"><option value="UNRESOLVED">Leave unresolved</option><option value="CONFIRMED">Confirm machine result</option><option value="OVERRIDDEN">Override machine result</option></select></label><label>Effective outcome<select id="review-status"><option value="NEEDS_REVIEW">Needs review</option><option value="OK">OK</option><option value="MISMATCH">Mismatch</option></select></label><label>Decision rationale<textarea id="review-reason-input" maxlength="2000" placeholder="State what the evidence supports and why…" required></textarea></label><button class="btn primary" type="submit">Record decision</button><button class="btn secondary" id="retry-review" type="button">Retry document processing</button></form></div>`;
  $("#review-decision").addEventListener("change", syncReviewStatus);
  $("#review-form").addEventListener("submit", saveReview);
  $("#retry-review").addEventListener("click", () => processCase(false));
  $$(`[data-review-field]`).forEach((button) => button.addEventListener("click", () => openFieldEvidence(button.dataset.reviewField)));
  $$(`[data-review-attachment]`).forEach((button) => button.addEventListener("click", () => openAttachment(button.dataset.reviewAttachment)));
  syncReviewStatus();
  renderReviewList();
}

function syncReviewStatus() {
  const decision = $("#review-decision")?.value;
  const select = $("#review-status");
  if (!select) return;
  if (decision === "CONFIRMED") {
    select.value = state.email?.machine_status || "NEEDS_REVIEW";
    select.disabled = true;
  } else if (decision === "UNRESOLVED") {
    select.value = "NEEDS_REVIEW";
    select.disabled = true;
  } else {
    select.disabled = false;
  }
}

async function saveReview(event) {
  event.preventDefault();
  const decision = $("#review-decision").value;
  const reason = $("#review-reason-input").value.trim();
  if (decision === "OVERRIDDEN" && reason.length < 12) {
    toast("An override needs a specific reason of at least 12 characters.", "error");
    $("#review-reason-input").focus();
    return;
  }
  if (!reason) {
    toast("Record the evidence behind this decision.", "error");
    $("#review-reason-input").focus();
    return;
  }
  try {
    await api(`/emails/${encodeURIComponent(state.selectedId)}/review`, { method: "POST", body: JSON.stringify({ decision, corrected_status: $("#review-status").value, corrected_fields: [], reason, reviewer_name: $("#reviewer-name").value.trim() }) });
    toast("Decision recorded. The machine result remains unchanged in the audit trail.");
    await Promise.all([openCase(state.selectedId, "review"), loadReviewQueue(), loadSummary(), loadAudit()]);
  } catch (error) { showError(error); }
}

async function loadAudit() {
  try {
    state.audit = (await api("/audit?limit=200")).items || [];
    renderAudit();
  } catch (error) { showError(error); }
}

function renderAudit() {
  const root = $("#audit-body");
  if (!state.audit.length) {
    root.innerHTML = `<div class="blank-state"><span>NO EVENTS</span><h2>Process a case to begin the assurance record.</h2></div>`;
    return;
  }
  root.innerHTML = state.audit.map((event) => {
    const prior = event.prior_state?.status || "—";
    const next = event.new_state?.status || event.new_state?.processed || "—";
    return `<div class="audit-row"><span class="audit-event">${escapeHtml(label(event.event_type))}</span><span>${escapeHtml(event.actor_name || event.actor_type || "System")}</span><button class="text-link" type="button" ${event.email_id ? `data-audit-email="${escapeHtml(event.email_id)}"` : "disabled"}>${escapeHtml(event.email_id || event.batch_id?.slice(0, 8) || "—")}</button><span class="audit-state">${escapeHtml(String(prior))} → ${escapeHtml(String(next))}${event.reason ? `<br>${escapeHtml(event.reason)}` : ""}</span><span class="audit-muted">${escapeHtml(shortDate(event.created_at))}</span></div>`;
  }).join("");
  $$(`[data-audit-email]`).forEach((button) => button.addEventListener("click", () => openCase(button.dataset.auditEmail)));
}

async function loadReports() {
  try {
    await loadSummary();
    renderReports();
  } catch (error) { showError(error); }
}

function renderReports() {
  const summary = state.summary || {};
  const total = Math.max(summary.processed_emails || 0, 1);
  const bars = (values, tone = "") => Object.entries(values || {}).sort((a, b) => b[1] - a[1]).map(([name, count]) => `<div class="breakdown-row"><span>${escapeHtml(label(name))}</span><span class="meter ${tone}"><i style="width:${Math.max(2, Math.round(count / total * 100))}%"></i></span><b>${count}</b></div>`).join("") || `<p class="audit-muted">No processed records yet.</p>`;
  $("#reports-content").innerHTML = `<div class="report-summary"><div><span>Coverage</span><strong>${summary.processed_emails || 0}/${summary.total_emails || 0}</strong><small>messages with a decision</small></div><div><span>Successful jobs</span><strong>${summary.processing?.succeeded || 0}</strong><small>${summary.processing?.failed || 0} failures</small></div><div><span>Human decisions</span><strong>${summary.reviews_recorded || 0}</strong><small>append-only reviews</small></div><div><span>Audit events</span><strong>${summary.audit_events || 0}</strong><small>traceable system actions</small></div></div><div class="report-grid"><section class="report-panel"><h2>Routing distribution</h2><p>Every message receives one operational category.</p><div class="breakdown">${bars(summary.by_category)}</div></section><section class="report-panel"><h2>Verification outcomes</h2><p>Effective outcomes include the latest recorded human decision.</p><div class="breakdown">${bars(summary.by_status, "red")}</div></section><section class="report-panel"><h2>Escalation causes</h2><p>Uncertain input is made visible instead of silently accepted.</p><div class="breakdown">${bars(summary.by_review_reason, "amber")}</div></section><section class="report-panel"><h2>Submission readiness</h2><p>The export uses the participant sample schema and excludes model prompts, source paths, and provider secrets.</p><div class="breakdown"><div class="breakdown-row"><span>Required records</span><span class="meter"><i style="width:100%"></i></span><b>520</b></div><div class="breakdown-row"><span>Current records</span><span class="meter"><i style="width:${Math.min(100, Math.round((summary.processed_emails || 0) / 520 * 100))}%"></i></span><b>${summary.processed_emails || 0}</b></div></div></section></div>`;
}

async function downloadSubmission() {
  try {
    const data = await api("/reports/export?format=json");
    const blob = new Blob([JSON.stringify(data.items, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "cargoclarity-submission.json";
    link.click();
    URL.revokeObjectURL(url);
    toast("Submission JSON downloaded.");
  } catch (error) { showError(error); }
}

function openFieldEvidence(fieldName) {
  const field = (state.comparison?.fields || []).find((item) => item.field_name === fieldName);
  if (!field) return;
  $("#drawer-title").textContent = label(field.field_name);
  $("#drawer-body").innerHTML = `<section class="evidence-section"><h3>Decision basis</h3><div class="evidence-meta"><span>Result <strong>${escapeHtml(label(field.result))}</strong></span><span>Comparison method <strong>${escapeHtml(label(field.comparison_method))}</strong></span><span>Confidence <strong>${Number.isFinite(Number(field.confidence)) ? Math.round(Number(field.confidence) * 100) + "%" : "—"}</strong></span><span>Explanation <strong>${escapeHtml(field.explanation || "—")}</strong></span></div></section>${evidenceSection("Shipping Instructions — reference", field.si)}${evidenceSection("Draft Bill of Lading", field.bl)}`;
  openDrawer();
}

function evidenceSection(title, value) {
  if (!value) return `<section class="evidence-section"><h3>${escapeHtml(title)}</h3><p class="value-empty">No dependable value was extracted.</p></section>`;
  return `<section class="evidence-section"><h3>${escapeHtml(title)}</h3><pre class="evidence-quote">${escapeHtml(value.evidence_excerpt || "No source excerpt recorded.")}</pre><div class="evidence-meta"><span>Raw value <strong>${escapeHtml(value.raw_value || "—")}</strong></span><span>Normalized <strong>${escapeHtml(value.normalized_value || "—")}</strong></span><span>Extraction <strong>${escapeHtml(label(value.extraction_method))}</strong></span></div></section>`;
}

async function openAttachment(attachmentId) {
  try {
    const preview = await api(`/emails/${encodeURIComponent(state.selectedId)}/attachments/${encodeURIComponent(attachmentId)}/preview`);
    $("#drawer-title").textContent = preview.filename || "Attachment preview";
    $("#drawer-body").innerHTML = `<section class="evidence-section"><h3>Parser record</h3><div class="evidence-meta"><span>Parser <strong>${escapeHtml(preview.parser_name || "—")}</strong></span><span>Readability <strong>${escapeHtml(label(preview.readability_status))}</strong></span><span>Error code <strong>${escapeHtml(preview.error_code || "None")}</strong></span></div></section><section class="evidence-section"><h3>Bounded source excerpt</h3><pre class="evidence-quote">${escapeHtml(preview.text_excerpt || "No readable text was found.")}</pre></section>`;
    openDrawer();
  } catch (error) { showError(error); }
}

function openDrawer() {
  $("#drawer-scrim").hidden = false;
  $("#evidence-drawer").classList.add("open");
  $("#evidence-drawer").setAttribute("aria-hidden", "false");
  state.drawerOpen = true;
}

function closeDrawer() {
  $("#drawer-scrim").hidden = true;
  $("#evidence-drawer").classList.remove("open");
  $("#evidence-drawer").setAttribute("aria-hidden", "true");
  state.drawerOpen = false;
}

function bindEvents() {
  $$("[data-view]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $("#refresh-button").addEventListener("click", async () => {
    try { await Promise.all([loadHealth(), loadInbox(), loadSummary()]); toast("Workspace refreshed."); }
    catch (error) { showError(error); }
  });
  $("#run-inbox").addEventListener("click", verifyInbox);
  $("#process-selected").addEventListener("click", () => processCase(false));
  $("#refresh-review").addEventListener("click", loadReviewQueue);
  $("#refresh-audit").addEventListener("click", loadAudit);
  $("#export-button").addEventListener("click", downloadSubmission);
  $("#drawer-close").addEventListener("click", closeDrawer);
  $("#drawer-scrim").addEventListener("click", closeDrawer);
  $("#prev-page").addEventListener("click", () => { if (state.page > 1) { state.page -= 1; loadInbox().catch(showError); } });
  $("#next-page").addEventListener("click", () => { if (state.page * state.pageSize < state.total) { state.page += 1; loadInbox().catch(showError); } });
  ["#category-filter", "#status-filter", "#review-filter"].forEach((selector) => $(selector).addEventListener("change", () => { state.page = 1; loadInbox().catch(showError); }));
  $("#search-input").addEventListener("input", () => { clearTimeout(bindEvents.searchTimer); bindEvents.searchTimer = setTimeout(() => { state.page = 1; loadInbox().catch(showError); }, 240); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && state.drawerOpen) closeDrawer(); });
}

async function boot() {
  bindEvents();
  try {
    await Promise.all([loadHealth(), loadInbox(), loadSummary()]);
  } catch (error) {
    $("#system-state").className = "system-state degraded";
    $("#system-state span").textContent = "API unavailable";
    $("#inbox-body").innerHTML = `<tr><td colspan="6"><div class="blank-state"><span>OFFLINE</span><h2>Start the CargoClarity API, then refresh this page.</h2><code>cargoclarity-api</code></div></td></tr>`;
    showError(error);
  }
}

document.addEventListener("DOMContentLoaded", boot);

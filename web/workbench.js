const queueList = document.getElementById("queue-list");
const queueState = document.getElementById("queue-state");
const queueCount = document.getElementById("queue-count");
const candidateList = document.getElementById("candidate-list");
const candidatesState = document.getElementById("candidates-state");
const candidateCount = document.getElementById("candidate-count");
const detailState = document.getElementById("detail-state");
const detail = document.getElementById("candidate-detail");

let candidates = [];
let selectedCandidateId = null;
const decisionMessages = new Map();

function element(tag, options = {}) {
  const node = document.createElement(tag);
  if (options.className) node.className = options.className;
  if (options.text !== undefined) node.textContent = String(options.text);
  return node;
}

function setState(node, message, isError = false) {
  node.textContent = message;
  node.classList.toggle("error", isError);
  node.hidden = false;
}

async function getJSON(url, options) {
  const response = await fetch(url, {
    cache: "no-store",
    ...options,
    headers: { Accept: "application/json", ...(options?.headers || {}) },
  });
  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    throw new Error(payload?.error || `Request failed (${response.status})`);
  }
  return payload;
}

function externalLink(url, label) {
  const link = element("a", { text: label });
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener";
  return link;
}

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "—" : value;
}

function formatBytes(value) {
  if (!Number.isFinite(value)) return valueOrDash(value);
  if (value < 1024) return `${value.toLocaleString()} bytes`;
  const units = ["KB", "MB", "GB"];
  let amount = value;
  let index = -1;
  do {
    amount /= 1024;
    index += 1;
  } while (amount >= 1024 && index < units.length - 1);
  return `${amount.toFixed(amount >= 10 ? 1 : 2)} ${units[index]} (${value.toLocaleString()} bytes)`;
}

function actionLabel(action) {
  return {
    approve_registration: "Approved for registration",
    reject: "Rejected",
    continue_research: "Continue research",
  }[action] || valueOrDash(action);
}

async function loadQueue() {
  setState(queueState, "Loading queue…");
  try {
    const payload = await getJSON("/api/workbench/queue");
    const items = Array.isArray(payload.items) ? payload.items : [];
    queueCount.textContent = String(items.length);
    queueList.replaceChildren();
    if (!items.length) {
      setState(queueState, "The research queue is empty.");
      return;
    }
    queueState.hidden = true;
    items.forEach((item) => {
      const row = element("li");
      const card = element("article", { className: "item-button" });
      card.append(
        element("span", { className: "item-id", text: item.id }),
        element("strong", { text: valueOrDash(item.deciding_record || item.description) }),
        element("span", {
          className: "item-summary",
          text: valueOrDash(item.description),
        }),
        element("span", {
          className: "item-meta",
          text: [
            "Agent evidence gap",
            item.case_id,
            item.likely_custodian,
          ].filter(Boolean).join(" · "),
        }),
        element("span", {
          className: "parent-prompt",
          text: `Parent prompt context: ${valueOrDash(item.question)}`,
        }),
        element("span", {
          className: "status-pill",
          text: valueOrDash(item.status),
        }),
      );
      row.append(card);
      queueList.append(row);
    });
  } catch (error) {
    queueCount.textContent = "!";
    setState(queueState, `Could not load queue: ${error.message}`, true);
  }
}

function renderCandidateList() {
  candidateList.replaceChildren();
  candidates.forEach((candidate) => {
    const row = element("li");
    const button = element("button", { className: "item-button" });
    button.type = "button";
    button.dataset.candidateId = candidate.id;
    if (candidate.id === selectedCandidateId) {
      button.setAttribute("aria-current", "true");
    }
    button.append(
      element("span", { className: "item-id", text: candidate.id }),
      element("strong", { text: valueOrDash(candidate.title) }),
      element("span", {
        className: "item-meta",
        text: [candidate.publisher, candidate.document_date].filter(Boolean).join(" · ") || "Issuer and date not supplied",
      }),
    );
    const status = candidate.latest_decision
      ? actionLabel(candidate.latest_decision.action)
      : valueOrDash(candidate.status);
    button.append(element("span", {
      className: `status-pill${candidate.latest_decision ? " decided" : ""}`,
      text: status,
    }));
    button.addEventListener("click", () => selectCandidate(candidate.id));
    row.append(button);
    candidateList.append(row);
  });
}

async function loadCandidates(preferredId = selectedCandidateId) {
  setState(candidatesState, "Loading candidates…");
  try {
    const payload = await getJSON("/api/workbench/candidates");
    candidates = Array.isArray(payload.items) ? payload.items : [];
    const validationErrors = Array.isArray(payload.validation_errors)
      ? payload.validation_errors
      : [];
    candidateCount.textContent = String(candidates.length);
    if (!candidates.length) {
      candidateList.replaceChildren();
      setState(
        candidatesState,
        validationErrors.length
          ? `No valid candidates. ${validationErrors.length} staging bundle(s) failed validation.`
          : "No staged evidence candidates are available.",
        validationErrors.length > 0,
      );
      selectedCandidateId = null;
      detail.hidden = true;
      setState(detailState, "Select a candidate when staged evidence becomes available.");
      return;
    }
    if (validationErrors.length) {
      setState(
        candidatesState,
        `${validationErrors.length} staging bundle(s) failed validation: ` +
          validationErrors
            .map((item) => `${item.bundle}: ${item.error}`)
            .join("; "),
        true,
      );
    } else {
      candidatesState.hidden = true;
    }
    const nextId = candidates.some((item) => item.id === preferredId)
      ? preferredId
      : candidates[0].id;
    selectedCandidateId = nextId;
    renderCandidateList();
    await loadCandidateDetail(nextId);
  } catch (error) {
    candidateCount.textContent = "!";
    setState(candidatesState, `Could not load candidates: ${error.message}`, true);
    detail.hidden = true;
    setState(detailState, "Candidate details are unavailable.", true);
  }
}

async function selectCandidate(candidateId) {
  if (candidateId === selectedCandidateId && !detail.hidden) return;
  selectedCandidateId = candidateId;
  renderCandidateList();
  await loadCandidateDetail(candidateId);
}

function factList(candidate) {
  const facts = element("dl", { className: "facts" });
  const values = [
    ["Issuer", candidate.publisher],
    ["Document date", candidate.document_date],
    ["Status", candidate.status],
    ["MIME type", candidate.mime_type],
    ["File size", formatBytes(candidate.bytes)],
    ["Retrieved", candidate.retrieved_at],
    ["SHA-256", candidate.sha256],
    ["Version", candidate.version],
    ["Signature", candidate.signature_status],
  ];
  values.forEach(([label, value]) => {
    const group = element("div");
    group.append(element("dt", { text: label }), element("dd", { text: valueOrDash(value) }));
    facts.append(group);
  });
  return facts;
}

function preview(candidate) {
  const section = element("section", { className: "preview-section" });
  section.append(element("h4", { text: "Evidence preview" }));
  const mime = String(candidate.mime_type || "").toLowerCase();
  const previewUrl = candidate.preview_url;
  const fileUrl = candidate.file_url;

  if (previewUrl) {
    const image = element("img", { className: "image-preview" });
    image.src = previewUrl;
    image.alt = `Generated preview of ${valueOrDash(candidate.title)}`;
    section.append(image);
  } else if (mime === "application/pdf") {
    const object = element("object", { className: "preview-frame" });
    object.data = fileUrl;
    object.type = "application/pdf";
    object.setAttribute("aria-label", `PDF preview of ${valueOrDash(candidate.title)}`);
    object.append(element("p", { text: "This browser cannot display the PDF preview. Use the evidence file link below." }));
    section.append(object);
  } else if (mime === "application/geo+json" || mime === "application/vnd.geo+json") {
    const panel = element("div", { className: "geo-preview" });
    panel.append(
      element("p", { text: "GeoJSON candidate. Review the verified file and proposed manifest metadata before deciding." }),
      externalLink(fileUrl, "Open GeoJSON file ↗"),
    );
    section.append(panel);
  } else {
    section.append(element("p", { className: "empty-copy", text: "No inline preview is available for this file type." }));
  }

  const links = element("p", { className: "preview-links" });
  links.append(externalLink(fileUrl, "Open evidence file ↗"));
  if (previewUrl) links.append(externalLink(previewUrl, "Open supplied preview ↗"));
  section.append(links);
  return section;
}

function claimCard(title, values, className = "") {
  const card = element("section", { className: `claim-card ${className}`.trim() });
  card.append(element("h4", { text: title }));
  if (!Array.isArray(values) || values.length === 0) {
    card.append(element("p", { className: "empty-copy", text: "None stated." }));
    return card;
  }
  const list = element("ul");
  values.forEach((value) => list.append(element("li", { text: value })));
  card.append(list);
  return card;
}

function decisionSummary(decision) {
  if (!decision) return null;
  const note = decision.note ? `\nNote: ${decision.note}` : "";
  return {
    message: `Latest audited decision: ${actionLabel(decision.action)} · ${valueOrDash(decision.created_at)} · ${valueOrDash(decision.actor)}${note}\nCanonical registration is not represented as complete by this decision.`,
    kind: "success",
  };
}

function nextPendingCandidateId(candidateId) {
  return candidates.find(
    (item) => item.id !== candidateId && !item.latest_decision,
  )?.id || null;
}

function completedDecisionPanel(candidate) {
  const section = element("section", { className: "decision-section decision-complete" });
  section.append(element("h4", { text: "Review decision complete" }));

  const summary = decisionSummary(candidate.latest_decision);
  const status = element("p", {
    className: "decision-status success",
    text: summary.message,
  });
  status.setAttribute("role", "status");
  section.append(status);

  const guidance = candidate.latest_decision.action === "approve_registration"
    ? "No further action is needed for this candidate. Its exact reviewed file is authorized and waiting for the separate deterministic registration process."
    : "No further action is needed for this candidate unless you want to revise the audited decision.";
  section.append(element("p", { className: "decision-guidance", text: guidance }));

  const actions = element("div", { className: "decision-actions" });
  const nextId = nextPendingCandidateId(candidate.id);
  if (nextId) {
    const next = element("button", { text: "Review next pending candidate" });
    next.type = "button";
    next.addEventListener("click", () => selectCandidate(nextId));
    actions.append(next);
  }
  const revise = element("button", {
    className: "secondary",
    text: "Record a revised decision",
  });
  revise.type = "button";
  revise.addEventListener("click", () => {
    section.replaceWith(decisionPanel(candidate, true));
  });
  actions.append(revise);
  section.append(actions);
  return section;
}

function decisionPanel(candidate, revising = false) {
  if (candidate.latest_decision && !revising) {
    return completedDecisionPanel(candidate);
  }

  const section = element("section", { className: "decision-section" });
  section.append(element("h4", {
    text: revising ? "Record a revised audited decision" : "Record an audited decision",
  }));
  const label = element("label", { text: "Reviewer note (optional)" });
  label.htmlFor = "decision-note";
  const note = element("textarea");
  note.id = "decision-note";
  note.maxLength = 2000;
  note.placeholder = "Record identity, provenance, scope, or reason for the decision.";
  section.append(
    label,
    note,
    element("p", { className: "note-help", text: "Maximum 2,000 characters. The response remains visible below." }),
  );

  const actions = element("div", { className: "decision-actions" });
  const definitions = [
    ["approve_registration", "Approve for registration", ""],
    ["continue_research", "Continue research", "secondary"],
    ["reject", "Reject", "reject"],
  ];
  const buttons = definitions.map(([action, labelText, className]) => {
    const button = element("button", { className, text: labelText });
    button.type = "button";
    button.addEventListener("click", async () => {
      const confirmed = window.confirm(
        `${labelText}: ${candidate.title}?\n\n` +
        "This records an audited decision. It does not mutate canonical evidence.",
      );
      if (!confirmed) return;
      await submitDecision(
        candidate.id,
        candidate.sha256,
        action,
        note.value,
        buttons,
        status,
      );
    });
    actions.append(button);
    return button;
  });
  section.append(actions);

  const status = element("p", { className: "decision-status" });
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  const stored = decisionMessages.get(candidate.id) || decisionSummary(candidate.latest_decision);
  if (stored) {
    status.textContent = stored.message;
    status.classList.add(stored.kind);
  } else {
    status.textContent = "No audited decision is recorded for this candidate.";
  }
  section.append(status);
  return section;
}

async function submitDecision(candidateId, candidateSha256, action, note, buttons, status) {
  buttons.forEach((button) => { button.disabled = true; });
  status.className = "decision-status";
  status.textContent = "Recording audited decision…";
  try {
    const body = {
      candidate_id: candidateId,
      candidate_sha256: candidateSha256,
      action,
    };
    if (note.trim()) body.note = note.trim();
    const response = await getJSON("/api/workbench/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const canonicalMessage = response.canonical_registration_performed
      ? "The response requires verification in the separate deterministic registration workflow; this Workbench does not represent canonical evidence as changed."
      : "Canonical registration was not performed. It remains a separate deterministic step.";
    const unmatchedMessage = response.unmatched_lead_ids?.length
      ? `\nWarning: related queue leads were unavailable: ${response.unmatched_lead_ids.join(", ")}`
      : "";
    const stored = {
      message: `Decision recorded: ${actionLabel(response.action)} · ${valueOrDash(response.created_at)}\n${canonicalMessage}${unmatchedMessage}`,
      kind: "success",
    };
    decisionMessages.set(candidateId, stored);
    status.textContent = stored.message;
    status.classList.add(stored.kind);
    await Promise.all([refreshCandidateIndex(), loadQueue()]);
    await loadCandidateDetail(candidateId);
  } catch (error) {
    const stored = { message: `Decision was not recorded: ${error.message}`, kind: "error" };
    decisionMessages.set(candidateId, stored);
    status.textContent = stored.message;
    status.classList.add(stored.kind);
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
  }
}

async function refreshCandidateIndex() {
  try {
    const payload = await getJSON("/api/workbench/candidates");
    candidates = Array.isArray(payload.items) ? payload.items : candidates;
    candidateCount.textContent = String(candidates.length);
    renderCandidateList();
  } catch {
    // The durable decision response remains visible even if list refresh fails.
  }
}

function renderDetail(candidate) {
  detail.replaceChildren();
  const titleRow = element("div", { className: "title-row" });
  const heading = element("div");
  heading.append(
    element("h3", { text: valueOrDash(candidate.title) }),
    element("p", { className: "candidate-id", text: candidate.id }),
  );
  titleRow.append(heading);
  detail.append(titleRow, factList(candidate));

  const official = element("p", { className: "official-url" });
  official.append(element("strong", { text: "Official source URL" }));
  if (candidate.source_url) {
    official.append(externalLink(candidate.source_url, candidate.source_url));
  } else {
    official.append(element("span", { text: "—" }));
  }
  detail.append(official, preview(candidate));

  const claims = element("div", { className: "claims-grid" });
  claims.append(
    claimCard("Establishes", candidate.establishes),
    claimCard("Does not establish", candidate.does_not_establish, "limits"),
  );
  detail.append(claims);

  const leadSection = element("section", { className: "manifest-section" });
  leadSection.append(element("h4", { text: "Related research lead IDs" }));
  if (Array.isArray(candidate.related_lead_ids) && candidate.related_lead_ids.length) {
    const leads = element("ul", { className: "lead-list" });
    candidate.related_lead_ids.forEach((id) => leads.append(element("li", { text: id })));
    leadSection.append(leads);
  } else {
    leadSection.append(element("p", { className: "empty-copy", text: "No related lead IDs supplied." }));
  }
  detail.append(leadSection);

  const manifestSection = element("section", { className: "manifest-section" });
  manifestSection.append(
    element("h4", { text: "Proposed manifest JSON" }),
    element("pre", {
      className: "manifest",
      text: JSON.stringify(candidate.proposed_manifest ?? {}, null, 2),
    }),
  );
  detail.append(manifestSection, decisionPanel(candidate));
}

async function loadCandidateDetail(candidateId) {
  detail.hidden = true;
  setState(detailState, "Loading candidate details…");
  try {
    const candidate = await getJSON(`/api/workbench/candidates/${encodeURIComponent(candidateId)}`);
    if (candidateId !== selectedCandidateId) return;
    decisionMessages.delete(candidateId);
    renderDetail(candidate);
    detailState.hidden = true;
    detail.hidden = false;
  } catch (error) {
    if (candidateId !== selectedCandidateId) return;
    setState(detailState, `Could not load candidate: ${error.message}`, true);
  }
}

await Promise.all([loadQueue(), loadCandidates()]);

const queueList = document.getElementById("queue-list");
const queueState = document.getElementById("queue-state");
const queueCount = document.getElementById("queue-count");
const researchActivityList = document.getElementById("research-activity-list");
const researchActivityState = document.getElementById("research-activity-state");
const pendingSearchApprovals = document.getElementById("pending-search-approvals");
const pendingSearchCount = document.getElementById("pending-search-count");
const pendingSearchList = document.getElementById("pending-search-list");
const actionCenter = document.getElementById("action-center");
const actionCenterHeading = document.getElementById("action-center-heading");
const actionCenterDetail = document.getElementById("action-center-detail");
const actionCenterProgress = document.getElementById("action-center-progress");
const systemActivityHeading = document.getElementById("system-activity-heading");
const systemActivityQuestion = document.getElementById("system-activity-question");
const systemActivityDetail = document.getElementById("system-activity-detail");
const systemActivityStages = document.getElementById("system-activity-stages");
const progressSummaryState = document.getElementById("progress-summary-state");
const progressSummaryMetrics = document.getElementById("progress-summary-metrics");
const progressSummaryLatest = document.getElementById("progress-summary-latest");
const viewResearchDetail = document.getElementById("view-research-detail");
const reviewNextCandidate = document.getElementById("review-next-candidate");
const candidateList = document.getElementById("candidate-list");
const candidatesState = document.getElementById("candidates-state");
const candidateCount = document.getElementById("candidate-count");
const detailState = document.getElementById("detail-state");
const detail = document.getElementById("candidate-detail");

let candidates = [];
let researchDirectives = [];
let queueItems = [];
let progressSummary = null;
let researchActivityLoadSequence = 0;
const directiveActionsInFlight = new Set();
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

async function postJSONWithTimeout(url, timeoutMilliseconds) {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    timeoutMilliseconds,
  );
  try {
    return await getJSON(url, {
      method: "POST",
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(
        "The browser stopped waiting, but watershop may still be processing the workflow. Durable status will be refreshed before retry is offered.",
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
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

function countStatus(group, status) {
  return Number(group?.[status] || 0);
}

function metric(value, label, detail, warning = false) {
  const card = element("div", {
    className: `progress-metric${warning ? " warning" : ""}`,
  });
  card.append(
    element("strong", { text: value }),
    element("span", { text: label }),
    element("span", { text: detail }),
  );
  return card;
}

function activityStage(label, detail, status) {
  const item = element("li", { className: `activity-stage ${status}` });
  item.append(
    element("strong", { text: label }),
    element("span", { text: detail }),
  );
  return item;
}

function renderSystemActivity() {
  const automation = progressSummary?.triage_automation || {};
  const foundryLoopActive = automation.configured && automation.healthy;
  if (!progressSummary?.latest_question) {
    systemActivityHeading.textContent = foundryLoopActive
      ? "IN THE LOOP — Foundry automation is monitoring"
      : "OUT OF THE LOOP — no agent is running";
    systemActivityDetail.textContent = foundryLoopActive
      ? "The persistent watershop worker is polling for question runs. Copilot is not part of this runtime path."
      : "Copilot is not connected between messages, and the evidence workflow has not recorded a question run.";
    systemActivityQuestion.hidden = true;
    systemActivityStages.hidden = true;
    return;
  }
  const latest = progressSummary.latest_question;
  const gapStatuses = latest.gap_statuses || {};
  const directiveStatuses = latest.directive_statuses || {};
  const triageCount = countStatus(gapStatuses, "triage");
  const pendingSearches = countStatus(directiveStatuses, "pending_approval");
  const activeSearches = countStatus(directiveStatuses, "running");
  const approvedSearches = countStatus(directiveStatuses, "approved");
  const completedSearches = countStatus(directiveStatuses, "completed");
  const failedSearches = countStatus(directiveStatuses, "failed");
  const stagedGaps = countStatus(gapStatuses, "candidate_staged");

  systemActivityQuestion.textContent = `Latest question: “${latest.question}”`;
  systemActivityQuestion.hidden = false;

  if (!latest.gap_count) {
    systemActivityHeading.textContent = foundryLoopActive
      ? "IN THE LOOP — Foundry automation is monitoring"
      : "OUT OF THE LOOP — the question run is complete";
    systemActivityDetail.textContent = foundryLoopActive
      ? "The latest chat run identified no evidence gap. The watershop worker remains active; Copilot is not part of this runtime path."
      : "Foundry completed the latest chat request without identifying an evidence gap. No agent remains active.";
  } else if (stagedGaps || pendingSearches) {
    systemActivityHeading.textContent =
      foundryLoopActive
        ? "IN THE LOOP — Foundry automation is waiting for your decision"
        : "OUT OF THE LOOP — waiting for your decision";
    systemActivityDetail.textContent =
      `${stagedGaps} gap${stagedGaps === 1 ? " has" : "s have"} staged evidence; ${pendingSearches} search approval${pendingSearches === 1 ? " is" : "s are"} ready for this question.`;
  } else if (activeSearches) {
    systemActivityHeading.textContent =
      "IN THE LOOP — Foundry research is running";
    systemActivityDetail.textContent =
      `${activeSearches} bounded search${activeSearches === 1 ? " is" : "es are"} active for the latest question.`;
  } else if (approvedSearches) {
    systemActivityHeading.textContent =
      foundryLoopActive
        ? "IN THE LOOP — approved search awaits dispatch"
        : "OUT OF THE LOOP — approved search awaits dispatch";
    systemActivityDetail.textContent =
      `${approvedSearches} bounded search${approvedSearches === 1 ? " is" : "es are"} approved, but no Foundry run has started.`;
  } else if (
    triageCount
    && !Object.keys(directiveStatuses).length
  ) {
    if (automation.state === "failed") {
      systemActivityHeading.textContent =
        "OUT OF THE LOOP — the Foundry triage worker failed";
      systemActivityDetail.textContent =
        `The failure was persisted and requires repair: ${automation.last_error || "no error detail was recorded"}`;
    } else if (foundryLoopActive) {
      systemActivityHeading.textContent =
        automation.state === "running"
          ? "IN THE LOOP — Foundry is triaging this question"
          : "IN THE LOOP — the Foundry triage worker is active";
      systemActivityDetail.textContent =
        `The latest chat run identified ${latest.gap_count} gap${latest.gap_count === 1 ? "" : "s"}. The persistent watershop worker is processing or polling the queue; Copilot is not part of this runtime path.`;
    } else {
      systemActivityHeading.textContent =
        "OUT OF THE LOOP — no agent is processing these gaps";
      systemActivityDetail.textContent =
        `The latest chat run identified ${latest.gap_count} gap${latest.gap_count === 1 ? "" : "s"}: ${latest.new_gap_count} new and ${latest.matched_gap_count} matched to existing gaps. They are saved on watershop. No automatic triage worker is configured, and Copilot is not connected between messages.`;
    }
  } else {
    systemActivityHeading.textContent = foundryLoopActive
      ? "IN THE LOOP — Foundry automation is active"
      : "OUT OF THE LOOP — no agent is currently running";
    systemActivityDetail.textContent =
      `${completedSearches} search${completedSearches === 1 ? "" : "es"} completed and ${failedSearches} failed for gaps associated with this question.`;
  }

  const searchDetail = activeSearches
    ? `${activeSearches} running`
    : pendingSearches
      ? `${pendingSearches} awaiting CIO approval`
      : approvedSearches
        ? `${approvedSearches} approved · not dispatched`
      : completedSearches || failedSearches
        ? `${completedSearches} completed · ${failedSearches} failed`
        : "Not prepared";
  const reviewCount = stagedGaps + pendingSearches;
  const reviewDetail = reviewCount
    ? `${reviewCount} decision${reviewCount === 1 ? "" : "s"} ready`
    : "Nothing waiting";
  const searchStatus = activeSearches
    ? "active"
    : pendingSearches
        || approvedSearches
        || (!Object.keys(directiveStatuses).length && triageCount)
      ? "waiting"
      : "complete";

  systemActivityStages.replaceChildren(
    activityStage("1. Chat answer", "Completed", "complete"),
    activityStage(
      "2. Evidence gaps",
      `${latest.new_gap_count} new · ${latest.matched_gap_count} matched`,
      "complete",
    ),
    activityStage(
      "3. Agent triage",
      triageCount
        ? foundryLoopActive
          ? automation.state === "running"
            ? "Foundry processing"
            : `${triageCount} queued · worker polling`
          : "Waiting · no worker configured"
        : "No gaps waiting",
      triageCount ? foundryLoopActive ? "active" : "waiting" : "complete",
    ),
    activityStage(
      "4. Bounded search",
      searchDetail,
      searchStatus,
    ),
    activityStage(
      "5. CIO review",
      reviewDetail,
      reviewCount ? "waiting" : "complete",
    ),
  );
  systemActivityStages.hidden = false;
}

function renderProgressSummary() {
  if (!progressSummary) return;
  const queueStatuses = progressSummary.queue_statuses || {};
  const directiveStatuses = progressSummary.directive_statuses || {};
  const triageCount = countStatus(queueStatuses, "triage");
  const parkedCount = countStatus(
    queueStatuses,
    "requires_transaction_identification",
  );
  const completedSearches = countStatus(directiveStatuses, "completed");
  const failedSearches = countStatus(directiveStatuses, "failed");
  const activeSearches = countStatus(directiveStatuses, "running");
  const approvedSearches = countStatus(directiveStatuses, "approved");
  const pendingActions =
    candidates.filter((candidate) => !candidate.latest_decision).length
    + researchDirectives.filter(
      (directive) => directive.status === "pending_approval",
    ).length;

  progressSummaryMetrics.replaceChildren(
    metric(
      progressSummary.queue_count,
      "evidence gaps logged",
      `${progressSummary.recent_triage_count} new · ${triageCount} awaiting triage · ${parkedCount} parked`,
      triageCount > 0,
    ),
    metric(
      progressSummary.directive_count,
      "bounded searches prepared",
      `${completedSearches} completed · ${failedSearches} failed · ${activeSearches} running · ${approvedSearches} awaiting dispatch`,
      failedSearches > 0,
    ),
    metric(
      progressSummary.registration_count,
      "documents registered",
      `${progressSummary.decision_count} audited CIO decisions`,
    ),
    metric(
      pendingActions,
      "decisions waiting for you",
      pendingActions ? "Action buttons appear above" : "No CIO action required",
    ),
  );
  progressSummaryMetrics.hidden = false;
  progressSummaryState.hidden = true;

  const latestDirective = [...researchDirectives]
    .sort(
      (left, right) =>
        Date.parse(right.updated_at || right.created_at)
        - Date.parse(left.updated_at || left.created_at),
    )[0];
  const timestamp = progressSummary.latest_activity_at
    ? new Date(progressSummary.latest_activity_at).toLocaleString()
    : "not recorded";
  progressSummaryLatest.textContent = latestDirective
    ? `Latest search outcome: ${latestDirective.title} — ${latestDirective.status}. Last audited activity: ${timestamp}.`
    : `Last audited activity: ${timestamp}.`;
  progressSummaryLatest.hidden = false;
  renderSystemActivity();
}

async function loadProgressSummary() {
  try {
    progressSummary = await getJSON("/api/workbench/progress");
    renderProgressSummary();
    updateActionCenter();
  } catch (error) {
    progressSummary = null;
    progressSummaryMetrics.hidden = true;
    progressSummaryLatest.hidden = true;
    setState(
      progressSummaryState,
      `Could not load progress: ${error.message}`,
      true,
    );
  }
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

async function approveDirective(directive, button) {
  await runDirectiveAction(directive, button, true);
}

async function dispatchDirective(directive, button) {
  await runDirectiveAction(directive, button, false);
}

async function runDirectiveAction(directive, button, requiresApproval) {
  if (directiveActionsInFlight.has(directive.id)) return;
  directiveActionsInFlight.add(directive.id);
  button.disabled = true;
  button.textContent = requiresApproval
    ? "Recording approval…"
    : "Starting Foundry search…";
  updateActionCenter();
  let phase = requiresApproval ? "approval" : "dispatch";
  try {
    if (requiresApproval) {
      await postJSONWithTimeout(
        `/api/workbench/research-directives/${encodeURIComponent(directive.id)}/approval`,
        30000,
      );
      phase = "dispatch";
      button.textContent = "Starting Foundry search…";
    }
    await postJSONWithTimeout(
      `/api/workbench/research-directives/${encodeURIComponent(directive.id)}/dispatch`,
      360000,
    );
  } catch (error) {
    setState(
      researchActivityState,
      phase === "approval"
        ? `Could not approve workflow ${directive.id}: ${error.message}`
        : `Foundry workflow ${directive.id} failed to start or complete: ${error.message}`,
      true,
    );
  } finally {
    try {
      await Promise.all([
        loadResearchActivity(),
        loadQueue(),
        loadCandidates(),
        loadProgressSummary(),
      ]);
    } finally {
      directiveActionsInFlight.delete(directive.id);
    }
    await loadResearchActivity();
  }
}

function renderPendingSearchApprovals(directives) {
  const pending = directives.filter(
    (directive) =>
      (
        directive.status === "pending_approval"
        || directive.status === "approved"
      )
      && !directiveActionsInFlight.has(directive.id),
  );
  pendingSearchList.replaceChildren();
  pendingSearchCount.textContent = String(pending.length);
  pendingSearchApprovals.hidden = pending.length === 0;
  pending.forEach((directive) => {
    const item = element("li");
    const text = element("div");
    text.append(
      element("strong", { text: directive.title }),
      element("span", { text: `Workflow ${directive.id}` }),
      element("span", {
        text: `Official hosts: ${directive.allowed_hosts.join(", ")}`,
      }),
    );
    const approved = directive.status === "approved";
    const approve = element("button", {
      className: "primary-button",
      text: approved
        ? "Start approved Foundry search"
        : "Approve and start Foundry search",
    });
    approve.type = "button";
    approve.addEventListener("click", () => {
      if (approved) {
        dispatchDirective(directive, approve);
      } else {
        approveDirective(directive, approve);
      }
    });
    item.append(text, approve);
    pendingSearchList.append(item);
  });
}

function updateActionCenter() {
  const pendingCandidates = candidates.filter(
    (candidate) => !candidate.latest_decision,
  );
  const waitingRegistration = candidates.filter(
    (candidate) =>
      candidate.latest_decision?.action === "approve_registration"
      && !candidate.canonical_registration,
  );
  const pendingSearches = researchDirectives.filter(
    (directive) =>
      directive.status === "pending_approval"
      && !directiveActionsInFlight.has(directive.id),
  );
  const approvedSearches = researchDirectives.filter(
    (directive) =>
      directive.status === "approved"
      && !directiveActionsInFlight.has(directive.id),
  );
  const runningSearches = researchDirectives.filter(
    (directive) => directive.status === "running",
  );
  const activeTriageCount = progressSummary?.recent_triage_count
    ?? queueItems.filter(
      (item) =>
        item.status === "triage"
        && Date.parse(item.created_at) >= Date.now() - 6 * 60 * 60 * 1000,
    ).length;
  const parkedTransactionCount = progressSummary
    ? countStatus(
      progressSummary.queue_statuses,
      "requires_transaction_identification",
    )
    : queueItems.filter(
      (item) => item.status === "requires_transaction_identification",
    ).length;
  const actionCount =
    pendingCandidates.length
    + pendingSearches.length
    + approvedSearches.length;
  const inFlightSearches = directiveActionsInFlight.size;

  actionCenter.className = `action-center ${actionCount ? "action-required" : "waiting"}`;
  reviewNextCandidate.hidden = pendingCandidates.length === 0;
  renderPendingSearchApprovals(researchDirectives);

  if (actionCount) {
    actionCenterHeading.textContent =
      `${actionCount} action${actionCount === 1 ? "" : "s"} need your attention`;
    const parts = [];
    if (pendingCandidates.length) {
      parts.push(
        `${pendingCandidates.length} document${pendingCandidates.length === 1 ? "" : "s"}`,
      );
    }
    if (pendingSearches.length || approvedSearches.length) {
      const searchCount = pendingSearches.length + approvedSearches.length;
      parts.push(
        `${searchCount} bounded search${searchCount === 1 ? "" : "es"}`,
      );
    }
    actionCenterDetail.textContent =
      `Review ${parts.join(" and ")}. Approval buttons record an explicit decision; approved searches may need a dispatch retry.`;
  } else if (waitingRegistration.length) {
    actionCenterHeading.textContent = "No action needed — registration is pending";
    actionCenterDetail.textContent =
      `${waitingRegistration.length} approved document${waitingRegistration.length === 1 ? " is" : "s are"} waiting for deterministic registration. Stay in Workbench until this panel says registration is complete.`;
  } else if (inFlightSearches) {
    actionCenterHeading.textContent = "No action needed — starting Foundry";
    actionCenterDetail.textContent =
      `${inFlightSearches} workflow${inFlightSearches === 1 ? " is" : "s are"} being approved or dispatched. Its button will not return unless the server reports that another action is genuinely required.`;
  } else if (runningSearches.length) {
    actionCenterHeading.textContent = "No action needed — research is running";
    actionCenterDetail.textContent =
      `${runningSearches.length} bounded search${runningSearches.length === 1 ? " is" : "es are"} running. New documents will appear here for review if found.`;
  } else if (
    progressSummary?.triage_automation?.configured
    && ["failed", "stale", "not_started"].includes(
      progressSummary.triage_automation.state,
    )
  ) {
    actionCenter.className = "action-center action-required";
    actionCenterHeading.textContent = "Foundry automation needs repair";
    actionCenterDetail.textContent =
      progressSummary.triage_automation.last_error
        || `The triage worker is ${progressSummary.triage_automation.state}; queued gaps will not advance until the service is restored.`;
  } else if (activeTriageCount) {
    const automation = progressSummary?.triage_automation;
    if (automation?.configured && automation?.healthy) {
      actionCenterHeading.textContent =
        automation.state === "running"
          ? "No action needed — Foundry is triaging gaps"
          : "No action needed — the Foundry worker is polling";
      actionCenterDetail.textContent =
        `${activeTriageCount} new evidence gap${activeTriageCount === 1 ? " is" : "s are"} in the persistent queue. Copilot is not involved; a search-approval button will appear after Foundry prepares bounded retrieval work.`;
    } else {
      actionCenterHeading.textContent =
        "No action needed — gaps await agent triage";
      actionCenterDetail.textContent =
        `${activeTriageCount} new evidence gap${activeTriageCount === 1 ? " is" : "s are"} queued for classification. No triage run is recorded yet; a search-approval button will appear only after bounded retrieval work is prepared.`;
    }
  } else {
    actionCenter.className = "action-center ready";
    actionCenterHeading.textContent = "Workbench complete — return to chat";
    actionCenterDetail.textContent =
      "There are no document or search decisions waiting for you. You may ask the evidence question again; a new answer can identify additional work.";
  }

  const progress = [];
  if (runningSearches.length) {
    progress.push(`${runningSearches.length} search${runningSearches.length === 1 ? "" : "es"} running`);
  }
  if (inFlightSearches) {
    progress.push(`${inFlightSearches} workflow${inFlightSearches === 1 ? "" : "s"} starting`);
  }
  if (waitingRegistration.length) {
    progress.push(`${waitingRegistration.length} registration${waitingRegistration.length === 1 ? "" : "s"} pending`);
  }
  if (parkedTransactionCount) {
    progress.push(`${parkedTransactionCount} transaction-specific gap${parkedTransactionCount === 1 ? "" : "s"} parked`);
  }
  actionCenterProgress.textContent = progress.join(" · ");
  renderProgressSummary();
}

viewResearchDetail.addEventListener("click", () => {
  const drawer = document.querySelector(".research-drawer");
  drawer.open = true;
  drawer.scrollIntoView({ behavior: "smooth", block: "start" });
});

reviewNextCandidate.addEventListener("click", () => {
  const candidate = candidates.find((item) => !item.latest_decision);
  if (!candidate) return;
  selectCandidate(candidate.id);
  document.getElementById("candidate-detail").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
});

async function loadResearchActivity() {
  const requestSequence = ++researchActivityLoadSequence;
  setState(researchActivityState, "Loading search activity…");
  try {
    const payload = await getJSON("/api/workbench/research-activity");
    if (requestSequence !== researchActivityLoadSequence) return;
    const items = Array.isArray(payload.items) ? payload.items : [];
    researchDirectives = items;
    updateActionCenter();
    researchActivityList.replaceChildren();
    if (!items.length) {
      setState(
        researchActivityState,
        "No grouped search directive has been prepared yet.",
      );
      return;
    }
    researchActivityState.hidden = true;
    items.forEach((directive) => {
      const row = element("li");
      const card = element("article", { className: "item-button" });
      const report = directive.latest_run?.report;
      const candidateCountValue = Array.isArray(report?.candidates)
        ? report.candidates.length
        : 0;
      const outcomes = Array.isArray(directive.latest_run?.candidate_outcomes)
        ? directive.latest_run.candidate_outcomes
        : [];
      const stagedCount = outcomes.filter(
        (item) => item.disposition === "staged_for_review",
      ).length;
      const duplicateCount = outcomes.filter(
        (item) => item.disposition === "already_in_corpus",
      ).length;
      const negativeCount = Array.isArray(report?.negative_findings)
        ? report.negative_findings.length
        : 0;
      card.append(
        element("span", { className: "item-id", text: directive.id }),
        element("strong", { text: valueOrDash(directive.title) }),
        element("span", {
          className: "item-summary",
          text: report?.summary || directive.search_brief,
        }),
        element("span", {
          className: "item-meta",
          text: [
            directive.latest_run?.provider,
            directive.latest_run?.model,
            report ? `${candidateCountValue} discovered` : null,
            outcomes.length ? `${stagedCount} new document(s)` : null,
            duplicateCount ? `${duplicateCount} already indexed` : null,
            report ? `${negativeCount} negative finding(s)` : null,
          ].filter(Boolean).join(" · ") || "Not dispatched",
        }),
        element("span", {
          className: "item-meta",
          text: `Approved official hosts: ${directive.allowed_hosts.join(", ")}`,
        }),
        element("span", {
          className: `status-pill${directive.status === "completed" ? " decided" : ""}`,
          text: valueOrDash(directive.status),
        }),
      );
      if (directive.latest_run?.error) {
        card.append(element("span", {
          className: "activity-error",
          text: `Dispatch failed: ${directive.latest_run.error}`,
        }));
      }
      const diagnosis = directive.latest_run?.acquisition_diagnosis;
      if (diagnosis) {
        const engineering = element("section", {
          className: "engineering-diagnosis",
        });
        engineering.append(
          element("strong", { text: "Acquisition Engineer diagnosis" }),
          element("p", { text: diagnosis.summary }),
          element("p", {
            text: `Root cause: ${diagnosis.root_cause}`,
          }),
          element("p", {
            className: "finding-limitation",
            text: diagnosis.code_change_required
              ? "A constrained adapter code proposal is required. No code, evidence, deployment, or merge was changed."
              : "No code change is proposed. A revised directive or controlled retry requires review.",
          }),
          element("span", {
            className: "status-pill",
            text: diagnosis.status,
          }),
        );
        card.append(engineering);
      }
      if (negativeCount) {
        const findings = element("details", {
          className: "negative-findings",
        });
        findings.append(element("summary", {
          text: `View ${negativeCount} negative finding(s)`,
        }));
        const list = element("ol");
        report.negative_findings.forEach((finding) => {
          const item = element("li");
          item.append(
            element("strong", { text: finding.repository }),
            element("p", { text: finding.result }),
            element("p", {
              className: "finding-limitation",
              text: `Limitation: ${finding.limitation}`,
            }),
          );
          list.append(item);
        });
        findings.append(list);
        card.append(findings);
      }
      const actionInFlight = directiveActionsInFlight.has(directive.id);
      if (
        directive.status === "pending_approval"
        || directive.status === "approved"
      ) {
        const approved = directive.status === "approved";
        const approve = element("button", {
          className: "secondary-button directive-approve",
          text: actionInFlight
            ? "Starting Foundry search…"
            : approved
              ? "Start Foundry search"
              : "Approve and start Foundry search",
        });
        approve.type = "button";
        approve.disabled = actionInFlight;
        approve.addEventListener(
          "click",
          () => {
            if (approved) {
              dispatchDirective(directive, approve);
            } else {
              approveDirective(directive, approve);
            }
          },
        );
        card.append(approve);
      }
      row.append(card);
      researchActivityList.append(row);
    });
  } catch (error) {
    if (requestSequence !== researchActivityLoadSequence) return;
    researchDirectives = [];
    pendingSearchApprovals.hidden = true;
    updateActionCenter();
    setState(
      researchActivityState,
      `Could not load search activity: ${error.message}`,
      true,
    );
  }
}

async function loadQueue() {
  setState(queueState, "Loading queue…");
  try {
    const payload = await getJSON("/api/workbench/queue");
    const items = Array.isArray(payload.items) ? payload.items : [];
    queueItems = items;
    updateActionCenter();
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
    queueItems = [];
    updateActionCenter();
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
    const status = candidate.canonical_registration
      ? "Registered"
      : candidate.latest_decision
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

function candidatePriority(candidate) {
  if (!candidate.latest_decision) return 0;
  if (
    candidate.latest_decision.action === "approve_registration"
    && !candidate.canonical_registration
  ) return 1;
  return 2;
}

function sortCandidates(items) {
  return items.sort((left, right) =>
    candidatePriority(left) - candidatePriority(right),
  );
}

async function loadCandidates(preferredId = selectedCandidateId) {
  setState(candidatesState, "Loading candidates…");
  try {
    const payload = await getJSON("/api/workbench/candidates");
    candidates = sortCandidates(Array.isArray(payload.items) ? payload.items : []);
    updateActionCenter();
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

function geoJsonPolygons(payload) {
  if (payload?.type !== "FeatureCollection" || !Array.isArray(payload.features)) {
    throw new Error("GeoJSON preview requires a FeatureCollection.");
  }
  const polygons = [];
  payload.features.forEach((feature) => {
    const geometry = feature?.geometry;
    if (geometry?.type === "Polygon" && Array.isArray(geometry.coordinates)) {
      polygons.push(geometry.coordinates);
    } else if (geometry?.type === "MultiPolygon" && Array.isArray(geometry.coordinates)) {
      polygons.push(...geometry.coordinates);
    } else {
      throw new Error(`Unsupported GeoJSON geometry: ${valueOrDash(geometry?.type)}`);
    }
  });
  if (!polygons.length) throw new Error("GeoJSON contains no polygon geometry.");
  return polygons;
}

function webMercatorPoint([longitude, latitude], zoom) {
  const scale = (2 ** zoom) * 256;
  const boundedLatitude = Math.max(-85.05112878, Math.min(85.05112878, latitude));
  const latitudeRadians = boundedLatitude * Math.PI / 180;
  return [
    ((longitude + 180) / 360) * scale,
    (
      1 -
      (Math.log(Math.tan(latitudeRadians) + (1 / Math.cos(latitudeRadians))) / Math.PI)
    ) / 2 * scale,
  ];
}

function loadMapTile(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.addEventListener("load", () => resolve(image), { once: true });
    image.addEventListener("error", () => reject(new Error(`Could not load map tile ${url}`)), { once: true });
    image.src = url;
  });
}

async function renderGeoJsonMap(canvas, status, fileUrl) {
  const payload = await getJSON(fileUrl);
  const polygons = geoJsonPolygons(payload);
  const points = polygons.flat(2);
  if (!points.every(
    (point) => Array.isArray(point) &&
      point.length >= 2 &&
      Number.isFinite(point[0]) &&
      Number.isFinite(point[1]),
  )) {
    throw new Error("GeoJSON contains invalid polygon coordinates.");
  }

  let minLongitude = Infinity;
  let maxLongitude = -Infinity;
  let minLatitude = Infinity;
  let maxLatitude = -Infinity;
  points.forEach(([longitude, latitude]) => {
    minLongitude = Math.min(minLongitude, longitude);
    maxLongitude = Math.max(maxLongitude, longitude);
    minLatitude = Math.min(minLatitude, latitude);
    maxLatitude = Math.max(maxLatitude, latitude);
  });
  if (minLongitude === maxLongitude || minLatitude === maxLatitude) {
    throw new Error("GeoJSON boundary has an empty geographic extent.");
  }

  const context = canvas.getContext("2d");
  if (!context) throw new Error("This browser cannot render a map canvas.");
  const width = canvas.width;
  const height = canvas.height;
  const margin = 70;
  const footer = 95;
  const mapWidth = width - (margin * 2);
  const mapHeight = height - margin - footer;

  context.fillStyle = "#f4f5ef";
  context.fillRect(0, 0, width, height);

  let zoom = 2;
  for (let candidateZoom = 16; candidateZoom >= 2; candidateZoom -= 1) {
    const northwest = webMercatorPoint([minLongitude, maxLatitude], candidateZoom);
    const southeast = webMercatorPoint([maxLongitude, minLatitude], candidateZoom);
    if (
      southeast[0] - northwest[0] <= mapWidth * .88 &&
      southeast[1] - northwest[1] <= mapHeight * .88
    ) {
      zoom = candidateZoom;
      break;
    }
  }

  const northwest = webMercatorPoint([minLongitude, maxLatitude], zoom);
  const southeast = webMercatorPoint([maxLongitude, minLatitude], zoom);
  const centerX = (northwest[0] + southeast[0]) / 2;
  const centerY = (northwest[1] + southeast[1]) / 2;
  const originX = centerX - (mapWidth / 2);
  const originY = centerY - (mapHeight / 2);
  const project = (point) => {
    const [worldX, worldY] = webMercatorPoint(point, zoom);
    return [margin + worldX - originX, margin + worldY - originY];
  };

  const firstTileX = Math.floor(originX / 256);
  const lastTileX = Math.floor((originX + mapWidth) / 256);
  const firstTileY = Math.floor(originY / 256);
  const lastTileY = Math.floor((originY + mapHeight) / 256);
  const tileCount = (lastTileX - firstTileX + 1) * (lastTileY - firstTileY + 1);
  if (tileCount > 30) {
    throw new Error(`Basemap preview unexpectedly requires ${tileCount} tiles.`);
  }
  context.save();
  context.beginPath();
  context.rect(margin, margin, mapWidth, mapHeight);
  context.clip();
  const tileJobs = [];
  for (let tileX = firstTileX; tileX <= lastTileX; tileX += 1) {
    for (let tileY = firstTileY; tileY <= lastTileY; tileY += 1) {
      const url = `https://tile.openstreetmap.org/${zoom}/${tileX}/${tileY}.png`;
      tileJobs.push(
        loadMapTile(url).then((image) => {
          context.drawImage(
            image,
            margin + (tileX * 256) - originX,
            margin + (tileY * 256) - originY,
            256,
            256,
          );
        }),
      );
    }
  }
  const tileResults = await Promise.allSettled(tileJobs);
  const failedTiles = tileResults.filter((result) => result.status === "rejected");

  context.fillStyle = "rgba(18, 101, 112, .25)";
  context.strokeStyle = "#126570";
  context.lineWidth = 5;
  polygons.forEach((polygon) => {
    context.beginPath();
    polygon.forEach((ring) => {
      ring.forEach((point, index) => {
        const [x, y] = project(point);
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      context.closePath();
    });
    context.fill("evenodd");
    context.stroke();
  });
  context.restore();

  context.strokeStyle = "#8a8f89";
  context.lineWidth = 2;
  context.strokeRect(margin, margin, mapWidth, mapHeight);
  context.fillStyle = "#1c2925";
  context.font = "700 25px system-ui, sans-serif";
  context.fillText("Mendocino Unified School District governance boundary", margin, height - 54);
  context.fillStyle = "#5d6a65";
  context.font = "18px system-ui, sans-serif";
  context.fillText(
    `County GIS geometry · ${Math.abs(minLongitude).toFixed(4)}°W to ${Math.abs(maxLongitude).toFixed(4)}°W · ` +
      `${minLatitude.toFixed(4)}° to ${maxLatitude.toFixed(4)}° N`,
    margin,
    height - 22,
  );
  if (failedTiles.length) {
    status.textContent = `Boundary rendered, but ${failedTiles.length} of ${tileCount} OpenStreetMap basemap tiles failed to load. This is a school-district governance boundary, not a water-service area.`;
    status.classList.add("warning");
  } else {
    status.textContent = "Verified County GeoJSON boundary over an OpenStreetMap basemap. This is a school-district governance boundary, not a water-service area.";
    status.classList.add("success");
  }
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
    const canvas = element("canvas", { className: "geo-map" });
    canvas.width = 1200;
    canvas.height = 900;
    canvas.setAttribute("role", "img");
    canvas.setAttribute(
      "aria-label",
      `Boundary map derived from ${valueOrDash(candidate.title)}`,
    );
    const mapStatus = element("p", {
      className: "map-status",
      text: "Rendering verified GeoJSON boundary…",
    });
    const attribution = element("p", {
      className: "map-attribution",
      text: "Basemap ",
    });
    attribution.append(
      externalLink("https://www.openstreetmap.org/copyright", "© OpenStreetMap contributors"),
    );
    panel.append(
      canvas,
      mapStatus,
      attribution,
    );
    section.append(panel);
    renderGeoJsonMap(canvas, mapStatus, fileUrl).catch((error) => {
      canvas.hidden = true;
      mapStatus.textContent = `Map preview failed: ${error.message}`;
      mapStatus.classList.add("error");
    });
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

function decisionSummary(decision, registration = null) {
  if (!decision) return null;
  const note = decision.note ? `\nNote: ${decision.note}` : "";
  const registrationMessage = registration
    ? `\nCanonical registration completed: ${valueOrDash(registration.registered_at)} · source ${valueOrDash(registration.source_id)}`
    : "\nCanonical registration is not represented as complete by this decision.";
  return {
    message: `Latest audited decision: ${actionLabel(decision.action)} · ${valueOrDash(decision.created_at)} · ${valueOrDash(decision.actor)}${note}${registrationMessage}`,
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

  const summary = decisionSummary(
    candidate.latest_decision,
    candidate.canonical_registration,
  );
  const status = element("p", {
    className: "decision-status success",
    text: summary.message,
  });
  status.setAttribute("role", "status");
  section.append(status);

  const guidance = candidate.canonical_registration
    ? "This exact reviewed file is registered in the canonical case corpus and is available to corpus-backed analysis."
    : candidate.latest_decision.action === "approve_registration"
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
  const stored = decisionMessages.get(candidate.id) ||
    decisionSummary(candidate.latest_decision, candidate.canonical_registration);
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
    const nextId = nextPendingCandidateId(candidateId) || candidateId;
    await Promise.all([
      loadCandidates(nextId),
      loadQueue(),
      loadResearchActivity(),
      loadProgressSummary(),
    ]);
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
    candidates = sortCandidates(
      Array.isArray(payload.items) ? payload.items : candidates,
    );
    updateActionCenter();
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

  if (Array.isArray(candidate.occurrences) && candidate.occurrences.length > 1) {
    const occurrenceSection = element("section", { className: "manifest-section" });
    occurrenceSection.append(
      element("h4", { text: "Discovery workflow occurrences" }),
      element("p", {
        className: "empty-copy",
        text: "Exact evidence identity matched across these staged workflow bundles.",
      }),
    );
    const occurrences = element("ul", { className: "lead-list" });
    candidate.occurrences.forEach((occurrence) => {
      const leadIds = Array.isArray(occurrence.related_lead_ids)
        ? occurrence.related_lead_ids.join(", ")
        : "";
      occurrences.append(element("li", {
        text: [
          valueOrDash(occurrence.bundle),
          valueOrDash(occurrence.title),
          leadIds ? `leads: ${leadIds}` : null,
        ].filter(Boolean).join(" · "),
      }));
    });
    occurrenceSection.append(occurrences);
    detail.append(occurrenceSection);
  }

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

await Promise.all([
  loadResearchActivity(),
  loadQueue(),
  loadCandidates(),
  loadProgressSummary(),
]);
setInterval(() => {
  if (!document.hidden) {
    Promise.all([loadResearchActivity(), loadProgressSummary()]);
  }
}, 10000);

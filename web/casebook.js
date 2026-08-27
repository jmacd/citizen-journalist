const data = window.MENDO_CASEBOOK_DATA;

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const humanize = (value) => String(value ?? "")
  .replaceAll("_", " ")
  .replace(/\b\w/g, (letter) => letter.toUpperCase());

const conclusionLabel = (value) => ({
  affirmative: "Affirmatively established",
  not_established: "Not established by reviewed records",
  prohibited: "Affirmatively prohibited",
  unspecified: "Unclassified legacy answer",
})[value] || humanize(value);

const sourceById = new Map(data.sources.map((source) => [source.id, source]));

function locatorLabel(citation) {
  if (citation.page) return `page ${citation.page}`;
  if (citation.section) return `section ${citation.section}`;
  if (citation.timestamp) return `timestamp ${citation.timestamp}`;
  if (citation.field) return `field ${citation.field}`;
  return "source";
}

function renderChatResult(question, result) {
  const container = document.getElementById("chat-result");
  const claims = result.claims || [];
  const gaps = result.gaps || [];
  const queuedResearch = result.queued_research || [];
  const reviewFindings = result.review_findings || [];
  const withheldClaims = result.withheld_claims || [];
  container.hidden = false;
  container.insertAdjacentHTML("beforeend", `
    <article class="chat-turn chat-turn-user">
      <strong>You</strong>
      <p>${escapeHtml(question)}</p>
    </article>
    <article class="chat-answer ${result.answer ? "" : "blocked"}">
      <header>
        <span class="status ${escapeHtml(result.status)}">${escapeHtml(humanize(result.status))}</span>
        <strong>${result.answer ? "Casebook answer" : "Answer withheld"}</strong>
      </header>
      <p class="chat-answer-text">${escapeHtml(result.answer || result.summary)}</p>
      ${result.conclusion_kind ? `<p class="chat-answer-kind">
        <strong>Conclusion:</strong> ${escapeHtml(conclusionLabel(result.conclusion_kind))}
      </p>` : ""}
      ${result.answer && result.scope_statement ? `<p class="chat-answer-scope">
        <strong>Reviewed scope:</strong> ${escapeHtml(result.scope_statement)}
      </p>` : ""}
      ${!result.answer && (result.withheld_answer || withheldClaims.length) ? `
        <details class="chat-withheld" open>
          <summary>Withheld draft context — not an answer</summary>
          <p class="withheld-warning">These are propositions the Analyst attempted. The Skeptic did not approve them for publication. Use the claim numbers below to understand the review findings; do not rely on them as conclusions.</p>
          ${result.scope_statement ? `<p><strong>Draft scope:</strong> ${escapeHtml(result.scope_statement)}</p>` : ""}
          ${result.withheld_answer ? `<blockquote>${escapeHtml(result.withheld_answer)}</blockquote>` : ""}
          ${withheldClaims.length ? `<ol class="chat-claims">${withheldClaims.map((claim) => `
            <li>
              <p>${escapeHtml(claim.text)}</p>
              ${claim.citations.length ? `<div class="chat-citations">${claim.citations.map((citation) => `
                ${citation.invalid ? `<span class="invalid-citation">
                  ${escapeHtml(citation.title)} · ${escapeHtml(locatorLabel(citation))}
                </span>` : `<a href="${citation.url
                  ? escapeHtml(citation.url)
                  : `#source-${escapeHtml(citation.document_id)}`}"
                  ${citation.url ? 'target="_blank" rel="noreferrer"' : ""}>
                  ${escapeHtml(citation.title)} · ${escapeHtml(locatorLabel(citation))}
                </a>`}
              `).join("")}</div>` : `<strong class="uncited-warning">No evidence locator supplied</strong>`}
              <details>
                <summary>${escapeHtml(humanize(claim.confidence))} · claimed limit</summary>
                <p>${escapeHtml(claim.does_not_establish)}</p>
              </details>
            </li>
          `).join("")}</ol>` : ""}
        </details>` : ""}
      ${claims.length ? `<details class="chat-evidence">
        <summary>${claims.length} evidence-backed ${claims.length === 1 ? "finding" : "findings"} and citations</summary>
        <ol class="chat-claims">${claims.map((claim) => `
        <li>
          <p>${escapeHtml(claim.text)}</p>
          <div class="chat-citations">${claim.citations.map((citation) => `
            <a href="${citation.url
              ? escapeHtml(citation.url)
              : `#source-${escapeHtml(citation.document_id)}`}"
              ${citation.url ? 'target="_blank" rel="noreferrer"' : ""}>
              ${escapeHtml(citation.title)} · ${escapeHtml(locatorLabel(citation))}
            </a>
          `).join("")}</div>
          <details>
            <summary>${escapeHtml(humanize(claim.confidence))} · limits</summary>
            <p>${escapeHtml(claim.does_not_establish)}</p>
          </details>
        </li>
      `).join("")}</ol>
      </details>` : ""}
      ${reviewFindings.length ? `<details class="chat-review" open>
        <summary>${result.answer ? "Analysis excluded from this answer" : "Why the Skeptic blocked this answer"}</summary>
        <p>${result.answer
          ? "These supplementary propositions were not needed for the answer and were excluded after review:"
          : "The draft was withheld because these evidence problems remained after two revision attempts:"}</p>
        <ul>${reviewFindings.map((finding) => `<li class="${escapeHtml(finding.severity)}">
          <strong>${finding.claim_number
            ? `Claim ${escapeHtml(finding.claim_number)} · `
            : ""}${escapeHtml(humanize(finding.code))}</strong>
          <span>${escapeHtml(finding.message)}</span>
        </li>`).join("")}</ul>
      </details>` : ""}
      ${gaps.length ? `<details class="chat-gaps">
        <summary>${gaps.length} unresolved evidence ${gaps.length === 1 ? "gap" : "gaps"}</summary>
        <ul>${gaps.map((gap) => `<li>
          ${escapeHtml(gap.description)}
          <small>Deciding record: ${escapeHtml(gap.deciding_record)}</small>
        </li>`).join("")}</ul>
      </details>` : ""}
      ${queuedResearch.length ? `<div class="chat-queued">
        <strong>Queued for research triage</strong>
        <ul>${queuedResearch.map((item) => `
          <li>${escapeHtml(item.deciding_record)}
            <small>${escapeHtml(item.id)} · no request sent</small>
          </li>`).join("")}</ul>
      </div>` : ""}
      ${result.answer
        ? `<p class="chat-continue">Continue the conversation below. Your next question will include this exchange as context.</p>`
        : `<div class="chat-recovery">
          <p>The rejected draft is not published as an answer. You can retry with a narrower question that asks only what the cited record establishes.</p>
          <button type="button" class="chat-retry">Prepare a narrower question</button>
        </div>`}
    </article>`);
  if (!result.answer) {
    container.lastElementChild.querySelector(".chat-retry")?.addEventListener("click", () => {
      const topic = question.slice(0, 1600);
      chatQuestion.value = `What can the current corpus establish with confidence about: ${topic}\n\nSeparate verified facts from unresolved points, and do not make conclusions beyond the cited records.`;
      chatQuestionLabel.textContent = "Review and retry";
      chatSubmit.textContent = "Ask narrower question";
      chatQuestion.focus();
      chatForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }
}

const chatForm = document.getElementById("chat-form");
const chatQuestion = document.getElementById("chat-question");
const chatQuestionLabel = document.getElementById("chat-question-label");
const chatSubmit = document.getElementById("chat-submit");
const chatState = document.getElementById("chat-state");
const chatModel = document.getElementById("chat-model");
const chatResult = document.getElementById("chat-result");
const chatHistory = [];

function runtimeLabel(runtime) {
  const label = runtime?.label || "Answer runtime unavailable";
  return `${label} · ${window.location.origin}`;
}

fetch("/api/health")
  .then((response) => response.json())
  .then((health) => {
    chatModel.textContent = runtimeLabel(health.runtime);
  })
  .catch(() => {
    chatModel.textContent = "Answer runtime unavailable";
  });

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = chatQuestion.value.trim();
  if (!question) return;
  chatSubmit.disabled = true;
  chatState.textContent = "Case Worker → corpus → Analyst → Skeptic…";
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history: chatHistory }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The casebook could not answer.");
    renderChatResult(question, result);
    chatHistory.push(
      { role: "user", content: question },
      {
        role: "assistant",
        content: result.answer || result.summary || "No answer was published.",
      },
    );
    if (chatHistory.length > 12) chatHistory.splice(0, chatHistory.length - 12);
    chatQuestion.value = "";
    chatQuestionLabel.textContent = result.answer ? "Ask a follow-up" : "Try a narrower question";
    chatQuestion.placeholder = result.answer
      ? "What should I understand next about this answer?"
      : "Ask only what the available records directly establish…";
    chatSubmit.textContent = result.answer ? "Ask follow-up" : "Ask narrower question";
    chatQuestion.focus();
    chatForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
    chatModel.textContent = runtimeLabel(result.runtime);
    chatState.textContent = result.answer
      ? "Answer complete · continue below"
      : "Skeptic block · review feedback above";
  } catch (error) {
    chatResult.hidden = false;
    chatResult.insertAdjacentHTML("beforeend", `
      <p class="chat-error">${escapeHtml(error.message)}</p>`);
    chatState.textContent = "Workflow failed";
  } finally {
    chatSubmit.disabled = false;
  }
});

document.getElementById("chat-new").addEventListener("click", () => {
  chatHistory.length = 0;
  chatResult.replaceChildren();
  chatResult.hidden = true;
  chatQuestion.value = "";
  chatQuestionLabel.textContent = "Question about this case";
  chatQuestion.placeholder = "What did the Planning Commission decide on August 20, 2026?";
  chatSubmit.textContent = "Ask";
  chatQuestion.focus();
  chatState.textContent = "New conversation";
});

document.querySelectorAll(".chat-suggestions button").forEach((button) => {
  button.addEventListener("click", () => {
    chatQuestion.value = button.textContent.trim();
    chatQuestion.focus();
  });
});

function originFor(source) {
  if (source.id.startsWith("public_")) return "Public submission";
  if (source.id.startsWith("hearing_video")) return "Meeting recording";
  if (source.id.startsWith("county_")) return "County hearing packet";
  if (source.id === "ccc_appeal_report") return "Coastal Commission";
  if (source.id === "rwqcb_noa") return "Regional Water Board";
  if (source.id === "ceqanet_cdfw_nod") return "CDFW via CEQAnet";
  if (source.id.startsWith("ceqanet_")) return "CEQAnet";
  return source.publisher || "Other public source";
}

function sourceLink(source, compact = false) {
  if (!source) return "";
  const metadata = [
    source.document_date,
    source.document_id ? `County doc ${source.document_id}` : null,
  ].filter(Boolean).join(" · ");
  return `
    <article class="source-link ${compact ? "compact" : ""}" id="source-${escapeHtml(source.id)}">
      <span class="origin ${escapeHtml(originFor(source).toLowerCase().replaceAll(" ", "-"))}">${escapeHtml(originFor(source))}</span>
      <div>
        ${source.url
          ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.title)} ↗</a>`
          : `<strong>${escapeHtml(source.title)}</strong>`}
        ${metadata ? `<small>${escapeHtml(metadata)}</small>` : ""}
        ${compact ? "" : `<small>${escapeHtml(humanize(source.status))}</small>`}
        ${source.note && !compact ? `<p>${escapeHtml(source.note)}</p>` : ""}
      </div>
    </article>`;
}

document.getElementById("case-id").textContent = data.case.id;
document.getElementById("case-title").textContent = data.case.title;
document.getElementById("case-description").textContent = data.case.description;
document.getElementById("applicant").textContent = data.case.applicant;
document.getElementById("project-site").textContent = data.case.locations.project_site.address;
document.getElementById("project-apns").textContent = data.case.locations.apns.join(", ");
document.getElementById("case-status").textContent = humanize(data.case.status);
document.getElementById("next-hearing").textContent = data.case.next_hearing;
document.getElementById("record-total").textContent = `(${data.sources.length})`;

document.getElementById("lineage-list").innerHTML =
  data.relationships.direct_lineage.map((item, index) => `
    <button class="lineage-node ${item.relationship === "current_case" ? "current" : ""}"
      type="button" data-lineage-id="${escapeHtml(item.id)}">
      <small>${escapeHtml(humanize(item.type))}</small>
      <strong>${escapeHtml(item.id)}</strong>
      <span>${escapeHtml(humanize(item.relationship))}</span>
    </button>${index < data.relationships.direct_lineage.length - 1 ? '<i aria-hidden="true">→</i>' : ""}
  `).join("");

function relationshipList(items) {
  return items.map((item) => `
    <p><strong>${escapeHtml(item.id)}</strong> — ${escapeHtml(item.reason || humanize(item.relationship))}</p>
  `).join("");
}
document.getElementById("related-list").innerHTML =
  relationshipList(data.relationships.related_not_direct);
document.getElementById("excluded-list").innerHTML =
  relationshipList(data.relationships.excluded_false_matches);

document.getElementById("meeting-cycles").innerHTML = data.meeting_cycles.map((cycle, index) => {
  const cycleEvents = data.events.filter((event) => cycle.event_dates.includes(event.date));
  return `
    <article class="meeting-cycle ${cycle.id === "stream_restoration_2026" ? "current-cycle" : ""}">
      <header>
        <span class="cycle-number">${String(index + 1).padStart(2, "0")}</span>
        <div>
          <p class="cycle-date">${escapeHtml(cycle.dates)} · ${escapeHtml(cycle.forum)}</p>
          <h3>${escapeHtml(cycle.title)}</h3>
          <p>${escapeHtml(cycle.summary)}</p>
          <p class="identifiers">${cycle.identifiers.map(escapeHtml).join(" · ")}</p>
        </div>
      </header>
      <div class="cycle-body">
        <ol class="cycle-events">${cycleEvents.map((event) => `
          <li class="${event.event.includes("unverified") ? "unresolved-event" : ""}">
            <time>${escapeHtml(event.date)}</time><span>${escapeHtml(event.event)}</span>
          </li>`).join("")}
        </ol>
        <div class="cycle-documents">
          ${cycle.source_ids.map((id) => sourceLink(sourceById.get(id), true)).join("")}
        </div>
      </div>
    </article>`;
}).join("");

document.getElementById("authority-conclusion").textContent =
  data.authorityChain.preliminary_conclusion;
document.getElementById("authority-actors").innerHTML =
  data.authorityChain.actors.map((actor) => `
    <article class="authority-actor">
      <header>
        <span>${escapeHtml(humanize(actor.role))}</span>
        <h3>${escapeHtml(actor.name)}</h3>
      </header>
      <div>
        <p><strong>Can</strong> ${escapeHtml(actor.powers.join(" "))}</p>
        <p><strong>Limit</strong> ${escapeHtml(actor.limits.join(" "))}</p>
      </div>
      <small>${actor.source_ids.map((id) => {
        const source = sourceById.get(id);
        return source?.url
          ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.title)}</a>`
          : escapeHtml(id);
      }).join(" · ")}</small>
    </article>
  `).join("");
document.getElementById("authority-chain").innerHTML =
  data.authorityChain.decision_chain.map((step) => `
    <li>
      <strong>${escapeHtml(step.question)}</strong>
      <span>${escapeHtml(step.why)}</span>
    </li>
  `).join("");
document.getElementById("authority-unresolved-list").innerHTML =
  data.authorityChain.unresolved.map((item) => `<li>${escapeHtml(item)}</li>`).join("");

const recordSearch = document.getElementById("record-search");
const publisherFilter = document.getElementById("publisher-filter");
const statusFilter = document.getElementById("status-filter");
const recordGroups = document.getElementById("record-groups");
const recordCount = document.getElementById("record-count");
let selectedSourceIds = null;

function fillFilter(select, values) {
  [...new Set(values.filter(Boolean))].sort().forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = humanize(value);
    select.append(option);
  });
}
fillFilter(publisherFilter, data.sources.map((source) => source.publisher));
fillFilter(statusFilter, data.sources.map((source) => source.status));

function renderRecords() {
  const query = recordSearch.value.trim().toLowerCase();
  const publisher = publisherFilter.value;
  const status = statusFilter.value;
  const sources = data.sources.filter((source) => {
    const searchable = [
      source.id,
      source.title,
      source.publisher,
      source.note,
      source.document_id,
      source.sha256,
    ].filter(Boolean).join(" ").toLowerCase();
    return (!query || searchable.includes(query)) &&
      (!publisher || source.publisher === publisher) &&
      (!status || source.status === status) &&
      (!selectedSourceIds || selectedSourceIds.has(source.id));
  });

  recordCount.textContent = `${sources.length} / ${data.sources.length}`;
  const grouped = sources.reduce((groups, source) => {
    const origin = originFor(source);
    if (!groups.has(origin)) groups.set(origin, []);
    groups.get(origin).push(source);
    return groups;
  }, new Map());
  recordGroups.innerHTML = [...grouped.entries()].map(([origin, records]) => `
    <section class="record-group">
      <header><h3>${escapeHtml(origin)}</h3><span>${records.length}</span></header>
      <div>${records.map((source) => sourceLink(source)).join("")}</div>
    </section>
  `).join("") || "<p>No records match these filters.</p>";
}

[recordSearch, publisherFilter, statusFilter].forEach((control) => {
  control.addEventListener(control === recordSearch ? "input" : "change", () => {
    selectedSourceIds = null;
    renderRecords();
  });
});
document.getElementById("clear-filters").addEventListener("click", () => {
  recordSearch.value = "";
  publisherFilter.value = "";
  statusFilter.value = "";
  selectedSourceIds = null;
  renderRecords();
});

document.querySelectorAll("[data-lineage-id]").forEach((button) => {
  button.addEventListener("click", () => {
    const relationship = data.relationships.direct_lineage
      .find((item) => item.id === button.dataset.lineageId);
    selectedSourceIds = new Set(relationship?.source_ids || []);
    recordSearch.value = "";
    publisherFilter.value = "";
    statusFilter.value = "";
    renderRecords();
    document.getElementById("records").scrollIntoView({ behavior: "smooth" });
  });
});

renderRecords();
document.getElementById("question-list").innerHTML = data.open_questions
  .map((question) => `<li>${escapeHtml(question)}</li>`)
  .join("");
document.getElementById("answered-questions").innerHTML = data.questions.map((question) => `
  <article class="answer-record">
    <header>
      <span class="status">${escapeHtml(humanize(question.status))}</span>
      <h3>${escapeHtml(question.question)}</h3>
    </header>
    <p class="answer-summary">${escapeHtml(question.short_answer)}</p>
    <details>
      <summary>${question.findings.length} evidence-backed findings</summary>
      <ol>${question.findings.map((finding) => {
        const source = sourceById.get(finding.source_id);
        const locator = finding.timestamp
          ? `timestamp ${finding.timestamp}`
          : `pages ${finding.pages}`;
        return `<li>
          ${escapeHtml(finding.claim)}
          <small>${source?.url
            ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.title)}</a>`
            : escapeHtml(finding.source_id)} · ${escapeHtml(locator)} · ${escapeHtml(humanize(finding.confidence))}</small>
        </li>`;
      }).join("")}</ol>
    </details>
    <details>
      <summary>What would complete this answer?</summary>
      <ul>${question.unresolved.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </details>
  </article>
`).join("");
document.getElementById("case-generated-at").textContent =
  `Built from manifest ${new Date(data.generatedAt).toLocaleString()}`;

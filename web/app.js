const data = window.MENDO_EXPLORER_DATA;

document.querySelectorAll(".tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.view).classList.add("active");
  });
});

const counts = data.hierarchy.counts;
document.getElementById("hierarchy-summary").textContent =
  `${data.hierarchy.publication.name} contains ${counts.chapters} coastal-zoning chapters and ` +
  `${counts.sections} numbered sections.`;
document.getElementById("metrics").innerHTML = [
  [counts.chapters, "chapters"],
  [counts.sections, "numbered sections"],
  [counts.documents, "API documents"],
  [counts.uniqueOrdinancesCited, "ordinances cited in source notes"],
].map(([value, label]) => `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`).join("");

const chapterList = document.getElementById("chapter-list");
function renderChapters(query = "") {
  const normalized = query.trim().toLowerCase();
  const chapters = data.hierarchy.chapters.filter((chapter) =>
    chapter.heading.toLowerCase().includes(normalized),
  );
  chapterList.innerHTML = chapters.map((chapter) =>
    `<article class="chapter"><strong>${chapter.heading}</strong><span>${chapter.sectionCount} sections</span></article>`,
  ).join("") || "<p>No chapter matched that search.</p>";
}
renderChapters();
document.getElementById("chapter-search").addEventListener("input", (event) => {
  renderChapters(event.target.value);
});

const laneLabels = {
  ccc: "Coastal Commission",
  county: "County",
  vendor: "MuniCode",
};
const laneInputs = [...document.querySelectorAll('.lane-controls input[type="checkbox"]:not(#show-versions)')];
const showVersions = document.getElementById("show-versions");
const timeline = document.getElementById("timeline-events");
function renderTimeline() {
  const activeLanes = new Set(laneInputs.filter((input) => input.checked).map((input) => input.value));
  const events = [...data.timeline.knownEvents];
  if (showVersions.checked) {
    data.timeline.versions.forEach((version) => events.push({
      ...version,
      detail: `${version.changedDocuments} Division II changed-document entries recorded by MuniCode.`,
      status: "publication",
    }));
  }
  timeline.innerHTML = events
    .filter((event) => activeLanes.has(event.lane))
    .sort((left, right) => left.date.localeCompare(right.date) || left.lane.localeCompare(right.lane))
    .map((event) => `
      <article class="event">
        <time datetime="${event.date}">${event.date}</time>
        <div class="event-card ${event.lane} ${event.status === "missing" ? "missing" : ""}">
          <span class="lane-label">${laneLabels[event.lane]}</span>
          <h3>${event.title}</h3>
          <p>${event.detail}</p>
        </div>
      </article>`)
    .join("");
}
[...laneInputs, showVersions].forEach((input) => input.addEventListener("change", renderTimeline));
renderTimeline();

const historyCounts = data.timeline.versionCounts;
document.getElementById("history-summary").innerHTML =
  `<strong>MuniCode history coverage</strong>` +
  `${historyCounts.versions} published versions and ${historyCounts.publicationTransitions} transitions are retained. ` +
  `${historyCounts.versionsWithDivisionChanges} versions contain ${historyCounts.totalDivisionChangedDocumentEntries} ` +
  `Division II changed-document entries. This history begins in 2011, not when the LCP was certified.`;

document.getElementById("generated-at").textContent =
  `Generated from captured public records ${new Date(data.generatedAt).toLocaleString()}`;

const trace = data.ordinance3857.trace;
document.getElementById("trace-detail").textContent =
  `The off-site line and Ordinance 3857 citation appear in all ${trace.versionsWithOffsite} ` +
  `of ${trace.versions} archived versions, with ${trace.retrievalErrors} retrieval errors.`;

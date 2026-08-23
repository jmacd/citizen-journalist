#!/usr/bin/env node

import { readdir, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";

async function latestDirectory(root) {
  const entries = await readdir(root, { withFileTypes: true });
  const directories = entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
  if (directories.length === 0) {
    throw new Error(`No inventory snapshots found beneath ${root}`);
  }
  return join(root, directories.at(-1));
}

const divisionSnapshot = await latestDirectory(
  resolve("captures/inventory/division-ii"),
);
const historySnapshot = await latestDirectory(
  resolve("captures/inventory/division-ii-history"),
);
const ordinanceTraceSnapshot = await latestDirectory(
  resolve("captures/history/20.376.015"),
);
const inventory = JSON.parse(
  await readFile(join(divisionSnapshot, "inventory.json"), "utf8"),
);
const tocNodes = JSON.parse(
  await readFile(join(divisionSnapshot, "toc-nodes.json"), "utf8"),
);
const history = JSON.parse(
  await readFile(join(historySnapshot, "history-summary.json"), "utf8"),
);
const ordinanceTrace = JSON.parse(
  await readFile(join(ordinanceTraceSnapshot, "summary.json"), "utf8"),
);

const chapters = tocNodes
  .filter((node) => /^CHAPTER\b/i.test(node.Heading))
  .map((chapter) => {
    const sectionCount = tocNodes.filter(
      (node) =>
        /^Sec\./i.test(node.Heading) &&
        node.lineage.includes(chapter.Id),
    ).length;
    return {
      heading: chapter.Heading,
      id: chapter.Id,
      sectionCount,
    };
  });

const data = {
  generatedAt: new Date().toISOString(),
  hierarchy: {
    chapters,
    counts: inventory.counts,
    division: inventory.division,
    publication: {
      codifiedThrough: inventory.publication.codifiedThrough,
      name: inventory.publication.publicationVersion.name,
      onlineDate: inventory.publication.publicationVersion.onlineDate,
    },
  },
  ordinance3857: {
    adoptedDate: "1993-05-10",
    boardVote: "4 ayes, 0 noes, 1 absent",
    countyText:
      "Alternative Energy Facilities: Onsite; Alternative Energy Facilities: Offsite",
    currentMunicodeText:
      "Alternative Energy Facilities: On-site; Alternative Energy Facilities: Off-site",
    section: "20.376.015",
    trace: {
      coverage: ordinanceTrace.coverage,
      retrievalErrors: ordinanceTrace.counts.retrievalErrors,
      versions: ordinanceTrace.counts.versions,
      versionsWithOffsite: ordinanceTrace.counts.versions,
    },
    status: {
      certificationRecord: "missing",
      countyAdoption: "verified",
      currentCodification: "verified",
      laterOverwrite: "not-found",
    },
  },
  timeline: {
    knownEvents: [
      {
        date: "1985-11-20",
        lane: "ccc",
        title: "Coastal Land Use Plan certified",
        detail:
          "Certified LUP Policy 3.11-12 authorizes off-site alternative energy in Agriculture, Forest Land, Range Lands, and Industrial Land.",
        status: "verified",
      },
      {
        date: "1991-03-15",
        lane: "ccc",
        title: "Implementation Plan certified with modifications",
        detail:
          "The Coastal Zoning Code became the regulatory implementation component of the LCP, subject to County acceptance and final certification steps.",
        status: "verified",
      },
      {
        date: "1991-07-22",
        lane: "county",
        title: "County adopted certification modifications",
        detail: "Board action followed the Commission's suggested modifications.",
        status: "verified",
      },
      {
        date: "1992-09-10",
        lane: "ccc",
        title: "Total LCP effectively certified",
        detail: "Reference date reported in the County's current LCP grant materials.",
        status: "verified",
      },
      {
        date: "1992-10-13",
        lane: "county",
        title: "County assumed coastal permit authority",
        detail: "County began administering coastal development permits under the certified LCP.",
        status: "verified",
      },
      {
        date: "1993-05-10",
        lane: "county",
        title: "Ordinance 3857 adopted",
        detail:
          "The Board replaced §20.376.015 and included off-site alternative energy in the RR district after considering a Commission Resolution of Certification.",
        status: "verified",
      },
      {
        date: "1993-05-10",
        lane: "ccc",
        title: "Referenced Resolution of Certification",
        detail:
          "Ordinance 3857 says this resolution was transmitted by the Commission, but the resolution, staff report, findings, and final certified text have not yet been obtained.",
        status: "missing",
      },
      {
        date: "2011-12-16",
        lane: "vendor",
        title: "Earliest retained MuniCode version",
        detail:
          "CodeBank history begins with Supplement 30; §20.376.015 already contains the off-site provision and Ordinance 3857 citation.",
        status: "verified",
      },
      {
        date: inventory.publication.publicationVersion.onlineDate.slice(0, 10),
        lane: "vendor",
        title: `${inventory.publication.publicationVersion.name} published`,
        detail:
          "Current MuniCode includes the off-site provision and cites Ordinance 3857.",
        status: "verified",
      },
    ],
    versions: history.versionsWithDivisionChanges.map((entry) => ({
      changedDocuments: entry.divisionChangedDocumentCount,
      date: entry.version.onlineDate.slice(0, 10),
      lane: "vendor",
      title: entry.version.name,
    })),
    versionCounts: history.counts,
  },
};

await writeFile(
  resolve("web/generated-data.js"),
  `window.MENDO_EXPLORER_DATA = ${JSON.stringify(data, null, 2)};\n`,
);
console.log("web/generated-data.js");

#!/usr/bin/env node

import { createHash, randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { MunicodeClient } from "../lib/municode-client.mjs";

const DIVISION_HEADING = /DIVISION II.*COASTAL ZONING CODE/i;

function timestamp() {
  return (
    new Date().toISOString().replaceAll(":", "-") +
    `-${randomUUID().slice(0, 8)}`
  );
}

function sha256(content) {
  return createHash("sha256").update(content).digest("hex");
}

function belongsToDivision(document) {
  return (
    DIVISION_HEADING.test(document.Title || "") ||
    (document.Ancestors || []).some((ancestor) =>
      DIVISION_HEADING.test(ancestor.Title || ""),
    )
  );
}

const client = new MunicodeClient();
const publication = await client.discoverPublication();
const versions = await client.getJson(
  `/localapi/Codebank/GetVersions/${publication.publicationVersion.publicationId}`,
);
const changesByVersion = [];

for (const version of versions) {
  const allChangedDocuments = await client.getJson("/api/CodesChangedDocs", {
    jobId: version.bisJobId,
    productId: publication.productId,
  });
  const divisionChangedDocuments = allChangedDocuments.filter(belongsToDivision);
  changesByVersion.push({
    allCodeChangedDocumentCount: allChangedDocuments.length,
    divisionChangedDocumentCount: divisionChangedDocuments.length,
    divisionChangedDocuments,
    version,
  });
}

const versionsWithDivisionChanges = changesByVersion.filter(
  (entry) => entry.divisionChangedDocumentCount > 0,
);
const report = {
  capturedAt: new Date().toISOString(),
  coverage: {
    earliest: versions.at(-1),
    latest: versions[0],
  },
  counts: {
    publishedVersions: versions.filter((version) => version.isPublished).length,
    publicationTransitions: Math.max(0, versions.length - 1),
    totalDivisionChangedDocumentEntries: changesByVersion.reduce(
      (total, entry) => total + entry.divisionChangedDocumentCount,
      0,
    ),
    versions: versions.length,
    versionsWithDivisionChanges: versionsWithDivisionChanges.length,
  },
  publication,
  versionsWithDivisionChanges,
};

const outputDirectory = resolve(
  "captures/inventory/division-ii-history",
  timestamp(),
);
await mkdir(resolve("captures/inventory/division-ii-history"), {
  recursive: true,
});
await mkdir(outputDirectory);
const files = {
  "all-version-changes.json": `${JSON.stringify(changesByVersion, null, 2)}\n`,
  "history-summary.json": `${JSON.stringify(report, null, 2)}\n`,
  "versions.json": `${JSON.stringify(versions, null, 2)}\n`,
};
for (const [name, content] of Object.entries(files)) {
  await writeFile(join(outputDirectory, name), content);
}
await writeFile(
  join(outputDirectory, "manifest.json"),
  `${JSON.stringify(
    Object.fromEntries(
      Object.entries(files).map(([name, content]) => [
        name,
        { bytes: Buffer.byteLength(content), sha256: sha256(content) },
      ]),
    ),
    null,
    2,
  )}\n`,
);

console.log(outputDirectory);
console.log(JSON.stringify(report.counts, null, 2));

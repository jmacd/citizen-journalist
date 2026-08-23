#!/usr/bin/env node

import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const endpoint = "https://mendocinocounty.nextrequest.com/client/documents";
const outputPath = resolve(
  "captures/cases/UM_2025-0004/pra/nextrequest-document-catalog.json",
);
const pageSize = 50;
const concurrency = 8;
const targetRequestIds = new Set(["23-445", "24-31", "24-33", "25-1012"]);
const terms = [
  "mendocino town",
  "mccsd",
  "musd",
  "um_2024",
  "um-2024",
  "pc_2024",
  "2020080439",
  "groundwater",
  "hauled water",
];

async function fetchPage(pageNumber) {
  const url = new URL(endpoint);
  url.searchParams.set("page_number", pageNumber);
  url.searchParams.set("page_size", pageSize);
  url.searchParams.set("sort_field", "count");
  url.searchParams.set("sort_order", "desc");
  const response = await fetch(url, {
    headers: {
      accept: "application/json",
      "x-requested-with": "XMLHttpRequest",
    },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} for page ${pageNumber}`);
  }
  return response.json();
}

const firstPage = await fetchPage(1);
const totalCount = firstPage.total_count;
const pageCount = Math.ceil(totalCount / pageSize);
const documents = [...firstPage.documents];

for (let start = 2; start <= pageCount; start += concurrency) {
  const pageNumbers = Array.from(
    { length: Math.min(concurrency, pageCount - start + 1) },
    (_, index) => start + index,
  );
  const pages = await Promise.all(pageNumbers.map(fetchPage));
  for (const page of pages) documents.push(...page.documents);
}

const uniqueDocuments = [
  ...new Map(documents.map((document) => [document.id, document])).values(),
];
const matches = uniqueDocuments.filter((document) => {
  if (targetRequestIds.has(document.pretty_id)) return true;
  const text = [
    document.title,
    document.description,
    document.pretty_id,
    document.folder_name,
  ].join(" ").toLowerCase();
  return terms.some((term) => text.includes(term));
});

const catalog = {
  portal: "https://mendocinocounty.nextrequest.com/documents",
  captured_at: new Date().toISOString(),
  reported_total: totalCount,
  captured_unique: uniqueDocuments.length,
  target_request_ids: [...targetRequestIds],
  search_terms: terms,
  matches,
  documents: uniqueDocuments,
};

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(catalog, null, 2)}\n`);

console.log(outputPath);
console.log(JSON.stringify({
  reported_total: totalCount,
  captured_unique: uniqueDocuments.length,
  matches: matches.length,
}));
for (const document of matches) {
  console.log(
    `${document.id}\t${document.pretty_id}\t${document.title}\t${document.document_path}`,
  );
}

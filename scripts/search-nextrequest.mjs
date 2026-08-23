#!/usr/bin/env node

import { htmlToText } from "html-to-text";

const endpoint = "https://mendocinocounty.nextrequest.com/client/requests";
const defaultTerms = [
  "UM_2025-0004",
  "UM_2024-0008",
  "U_2023-0004",
  "PC_2024-0019",
  "Mendocino Unified School District",
  "Mendocino City Community Services District",
  "2020080439",
  "CA2300584",
  "Emergency Water Service Area",
  "Slaughterhouse Gulch",
];

const args = process.argv.slice(2);
const jsonOutput = args.includes("--json");
const terms = args.filter((arg) => arg !== "--json");
if (terms.length === 0) terms.push(...defaultTerms);

async function fetchPage(term, pageNumber) {
  const url = new URL(endpoint);
  url.searchParams.set("search_term", term);
  url.searchParams.set("page_number", pageNumber);
  const response = await fetch(url, {
    headers: {
      accept: "application/json",
      "x-requested-with": "XMLHttpRequest",
    },
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} for ${url}`);
  }
  return response.json();
}

async function search(term) {
  const matches = [];
  let pageNumber = 1;
  let totalCount = 0;
  while (true) {
    const page = await fetchPage(term, pageNumber);
    totalCount = page.total_count || 0;
    const requests = page.requests || [];
    matches.push(...requests);
    if (requests.length === 0 || matches.length >= totalCount) break;
    pageNumber += 1;
  }
  return { term, total_count: totalCount, requests: matches };
}

const searches = [];
for (const term of terms) {
  searches.push(await search(term));
}

const requests = new Map();
for (const result of searches) {
  for (const request of result.requests) {
    const current = requests.get(request.id) || {
      ...request,
      request_text: htmlToText(request.request_text || "", {
        wordwrap: false,
      }).replace(/\s+/g, " ").trim(),
      matched_terms: [],
    };
    current.matched_terms.push(result.term);
    requests.set(request.id, current);
  }
}

const output = {
  portal: "https://mendocinocounty.nextrequest.com/requests",
  searched_at: new Date().toISOString(),
  searches: searches.map(({ term, total_count }) => ({ term, total_count })),
  requests: [...requests.values()].sort((a, b) => a.id.localeCompare(b.id)),
};

if (jsonOutput) {
  console.log(JSON.stringify(output, null, 2));
} else {
  for (const searchResult of output.searches) {
    console.log(`${searchResult.term}: ${searchResult.total_count} portal match(es)`);
  }
  for (const request of output.requests) {
    console.log(`\n${request.id} — ${request.request_date} — ${request.request_state}`);
    console.log(`${request.department_names || "No department"} — ${request.request_path}`);
    console.log(`Matched: ${request.matched_terms.join(", ")}`);
    console.log(request.request_text);
  }
}

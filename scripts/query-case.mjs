#!/usr/bin/env node

import { resolve } from "node:path";
import Database from "better-sqlite3";

const args = process.argv.slice(2);
const query = args.join(" ").trim();
if (!query) {
  console.error("Usage: npm run query:case -- <search terms>");
  process.exit(1);
}

const db = new Database(
  resolve("captures/cases/UM_2025-0004/casebook.sqlite"),
  { readonly: true },
);
const rows = db.prepare(`
  SELECT document_id, page_number, title,
         snippet(document_search, 4, '[', ']', ' … ', 18) AS excerpt
  FROM document_search
  WHERE document_search MATCH ?
  ORDER BY rank
  LIMIT 20
`).all(query);

if (rows.length === 0) {
  console.log("No indexed page matched.");
} else {
  for (const row of rows) {
    console.log(`\n${row.title} — page ${row.page_number} (${row.document_id})`);
    console.log(row.excerpt);
  }
}
db.close();

#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { basename, resolve } from "node:path";

const ids = process.argv.slice(2);
if (ids.length === 0) {
  console.error("Usage: npm run fetch:pra-docs -- <document-id> [...]");
  process.exit(1);
}

const outputDirectory = resolve(
  "captures/cases/UM_2025-0004/pra/nextrequest-documents",
);
await mkdir(outputDirectory, { recursive: true });

function decodeEntities(value) {
  return value
    .replaceAll("&amp;", "&")
    .replaceAll("&quot;", "\"")
    .replaceAll("&#39;", "'")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">");
}

function safeFilename(value) {
  return value
    .normalize("NFKD")
    .replace(/[^\x20-\x7E]/g, "")
    .replace(/[\/:*?"<>|]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

const records = [];
for (const id of ids) {
  const pageUrl = `https://mendocinocounty.nextrequest.com/documents/${id}`;
  const pageResponse = await fetch(pageUrl);
  if (!pageResponse.ok) {
    throw new Error(`${pageResponse.status} ${pageResponse.statusText} for ${pageUrl}`);
  }
  const html = await pageResponse.text();
  const titleMatch = html.match(/<title>(.*?) - NextRequest/s);
  const viewerMatch = html.match(
    /src="\/pdfjs\/web\/viewer\.html\?file=([^"]+)"/,
  );
  if (!titleMatch || !viewerMatch) {
    throw new Error(`Could not locate public PDF metadata for document ${id}`);
  }

  const title = decodeEntities(titleMatch[1]);
  const sourceUrl = decodeEntities(decodeURIComponent(viewerMatch[1]));
  const fileResponse = await fetch(sourceUrl);
  if (!fileResponse.ok) {
    throw new Error(
      `${fileResponse.status} ${fileResponse.statusText} downloading ${id}`,
    );
  }
  const bytes = Buffer.from(await fileResponse.arrayBuffer());
  if (!bytes.subarray(0, 5).equals(Buffer.from("%PDF-"))) {
    throw new Error(`Document ${id} did not return a PDF`);
  }

  const filename = `${id}-${safeFilename(basename(title))}`;
  const path = resolve(outputDirectory, filename);
  await writeFile(path, bytes);
  const record = {
    portal_document_id: id,
    title,
    page_url: pageUrl,
    capture_path: path,
    bytes: bytes.length,
    sha256: createHash("sha256").update(bytes).digest("hex"),
  };
  records.push(record);
  console.log(
    `${record.portal_document_id}\t${record.bytes}\t${record.sha256}\t${record.title}`,
  );
}

await writeFile(
  resolve(outputDirectory, "capture-metadata.json"),
  `${JSON.stringify({
    captured_at: new Date().toISOString(),
    documents: records,
  }, null, 2)}\n`,
);

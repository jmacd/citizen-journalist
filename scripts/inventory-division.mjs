#!/usr/bin/env node

import { createHash, randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import process from "node:process";
import { htmlToText } from "html-to-text";
import { MunicodeClient } from "../lib/municode-client.mjs";

const TITLE_HEADING = /^Title 20\b/i;
const DIVISION_HEADING = /^DIVISION II\b/i;
const CHAPTER_HEADING = /^CHAPTER\b/i;
const SECTION_HEADING = /^Sec\./i;

function timestamp() {
  return (
    new Date().toISOString().replaceAll(":", "-") +
    `-${randomUUID().slice(0, 8)}`
  );
}

function sha256(content) {
  return createHash("sha256").update(content).digest("hex");
}

async function walk(client, root) {
  const nodes = [];
  const queue = [{ lineage: [root], node: root }];
  while (queue.length > 0) {
    const current = queue.shift();
    nodes.push({ ...current.node, lineage: current.lineage.map((node) => node.Id) });
    if (!current.node.HasChildren) continue;
    const children = await client.children(current.node.Id);
    for (const child of children) {
      queue.push({
        lineage: [...current.lineage, child],
        node: child,
      });
    }
  }
  return nodes;
}

function sourceNotes(document) {
  const text = htmlToText(document.Content || "", { wordwrap: false });
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => /^\((?:Ord\.|Res\.)/i.test(line));
}

function ordinanceNumbers(notes) {
  const numbers = [];
  for (const note of notes) {
    for (const match of note.matchAll(/\bOrd\. No\. ([0-9-]+)/gi)) {
      numbers.push(match[1]);
    }
  }
  return numbers;
}

async function main() {
  const client = new MunicodeClient();
  const root = await client.root();
  const title = root.Children.find((node) => TITLE_HEADING.test(node.Heading));
  if (!title) throw new Error("Title 20 not found");
  const divisions = await client.children(title.Id);
  const division = divisions.find((node) => DIVISION_HEADING.test(node.Heading));
  if (!division) throw new Error("Division II not found");

  const nodes = await walk(client, division);
  const chapters = nodes.filter((node) => CHAPTER_HEADING.test(node.Heading));
  const documents = new Map();
  const chapterResponses = [];
  for (const chapter of chapters) {
    const response = await client.content(chapter.Id, { groupChunks: true });
    chapterResponses.push({
      chapterId: chapter.Id,
      response,
    });
    for (const document of response.Docs || []) {
      documents.set(document.Id, document);
    }
  }

  const documentInventory = [...documents.values()].map((document) => {
    const notes = sourceNotes(document);
    return {
      amendedBy: document.AmendedBy || [],
      compareStatus: document.CompareStatus,
      contentBytes: Buffer.byteLength(document.Content || ""),
      docOrderId: document.DocOrderId,
      heading: document.Title,
      id: document.Id,
      isAmended: document.IsAmended,
      isUpdated: document.IsUpdated,
      ordinanceNumbers: ordinanceNumbers(notes),
      sourceNotes: notes,
    };
  });
  const uniqueOrdinances = [
    ...new Set(documentInventory.flatMap((document) => document.ordinanceNumbers)),
  ].sort((left, right) =>
    left.localeCompare(right, undefined, { numeric: true }),
  );
  const rawResponses = `${JSON.stringify(chapterResponses, null, 2)}\n`;
  const inventory = {
    capturedAt: new Date().toISOString(),
    counts: {
      chapters: chapters.length,
      documents: documentInventory.length,
      sections: nodes.filter((node) => SECTION_HEADING.test(node.Heading)).length,
      sourceNoteOccurrences: documentInventory.reduce(
        (total, document) => total + document.sourceNotes.length,
        0,
      ),
      tocNodes: nodes.length,
      uniqueOrdinancesCited: uniqueOrdinances.length,
    },
    currentSupplementFlags: {
      amendedDocuments: documentInventory.filter((document) => document.isAmended)
        .length,
      amendedTocNodes: nodes.filter((node) => node.Data?.IsAmended).length,
      changedCompareStatusDocuments: documentInventory.filter(
        (document) => document.compareStatus !== 4,
      ).length,
      changedCompareStatusTocNodes: nodes.filter(
        (node) => node.Data?.CompareStatus !== 4,
      ).length,
      updatedDocuments: documentInventory.filter((document) => document.isUpdated)
        .length,
      updatedTocNodes: nodes.filter((node) => node.Data?.IsUpdated).length,
    },
    division: {
      heading: division.Heading,
      id: division.Id,
    },
    publication: await client.discoverPublication(),
    sizes: {
      chapterApiResponsesBytes: Buffer.byteLength(rawResponses),
      documentContentBytes: documentInventory.reduce(
        (total, document) => total + document.contentBytes,
        0,
      ),
    },
    uniqueOrdinances,
  };

  const outputDirectory = resolve("captures/inventory/division-ii", timestamp());
  await mkdir(resolve("captures/inventory/division-ii"), { recursive: true });
  await mkdir(outputDirectory);
  const files = {
    "chapter-responses.json": rawResponses,
    "documents.json": `${JSON.stringify(documentInventory, null, 2)}\n`,
    "inventory.json": `${JSON.stringify(inventory, null, 2)}\n`,
    "toc-nodes.json": `${JSON.stringify(nodes, null, 2)}\n`,
  };
  for (const [name, content] of Object.entries(files)) {
    await writeFile(join(outputDirectory, name), content);
  }
  const manifest = Object.fromEntries(
    Object.entries(files).map(([name, content]) => [
      name,
      { bytes: Buffer.byteLength(content), sha256: sha256(content) },
    ]),
  );
  await writeFile(
    join(outputDirectory, "manifest.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
  );

  console.log(outputDirectory);
  console.log(JSON.stringify(inventory, null, 2));
}

await main();

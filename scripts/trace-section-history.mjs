#!/usr/bin/env node

import { createHash, randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { htmlToText } from "html-to-text";
import { MunicodeClient, parseSectionReference } from "../lib/municode-client.mjs";

function parseArgs(argv) {
  const options = {
    division: undefined,
    section: undefined,
    texts: [],
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    switch (argument) {
      case "--division":
        options.division = argv[++index];
        break;
      case "--section":
        options.section = argv[++index];
        break;
      case "--text":
        options.texts.push(argv[++index]);
        break;
      default:
        throw new Error(`Unknown argument: ${argument}`);
    }
  }
  if (!options.section) throw new Error("--section is required");
  const reference = parseSectionReference(options.section);
  if (reference.title === "20" && !options.division) options.division = "II";
  return options;
}

function timestamp() {
  return (
    new Date().toISOString().replaceAll(":", "-") +
    `-${randomUUID().slice(0, 8)}`
  );
}

function sha256(content) {
  return createHash("sha256").update(content).digest("hex");
}

const options = parseArgs(process.argv.slice(2));
const discoveryClient = new MunicodeClient();
const currentPublication = await discoveryClient.discoverPublication();
const versions = await discoveryClient.getJson(
  `/localapi/Codebank/GetVersions/${currentPublication.publicationVersion.publicationId}`,
);
const captures = [];

for (const version of [...versions].reverse()) {
  const client = new MunicodeClient();
  client.publication = {
    ...currentPublication,
    job: {
      ...currentPublication.job,
      Id: version.bisJobId,
      IsLatest: version.isLatest,
      Name: version.name,
      OnlineDate: version.onlineDate,
    },
    publicationVersion: version,
  };
  try {
    const resolved = await client.resolveSection(options.section, {
      division: options.division,
    });
    const response = await client.content(resolved.node.Id);
    const document = response.Docs.find((doc) => doc.Id === resolved.node.Id);
    if (!document) {
      throw new Error(`Content response omitted ${resolved.node.Id}`);
    }
    const text = `${document.Title}\n\n${htmlToText(document.Content, {
      wordwrap: false,
    }).trim()}\n`;
    captures.push({
      error: null,
      nodeId: resolved.node.Id,
      presence: Object.fromEntries(
        options.texts.map((expected) => [expected, text.includes(expected)]),
      ),
      sourceNotes: text
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => /^\((?:Ord\.|Res\.)/i.test(line)),
      text,
      textSha256: sha256(text),
      version,
    });
  } catch (error) {
    captures.push({
      error: error.message,
      nodeId: null,
      presence: Object.fromEntries(options.texts.map((text) => [text, false])),
      sourceNotes: [],
      text: null,
      textSha256: null,
      version,
    });
  }
}

const transitions = [];
for (let index = 1; index < captures.length; index += 1) {
  const older = captures[index - 1];
  const newer = captures[index];
  const presenceChanged = options.texts.some(
    (text) => older.presence[text] !== newer.presence[text],
  );
  if (
    older.error !== newer.error ||
    older.textSha256 !== newer.textSha256 ||
    presenceChanged
  ) {
    transitions.push({
      from: older.version,
      fromPresence: older.presence,
      fromSha256: older.textSha256,
      presenceChanged,
      to: newer.version,
      toPresence: newer.presence,
      toSha256: newer.textSha256,
    });
  }
}

const summary = {
  capturedAt: new Date().toISOString(),
  counts: {
    retrievalErrors: captures.filter((capture) => capture.error).length,
    textTransitions: transitions.length,
    versions: captures.length,
  },
  coverage: {
    earliest: captures[0]?.version,
    latest: captures.at(-1)?.version,
  },
  firstPresence: Object.fromEntries(
    options.texts.map((text) => [
      text,
      captures.find((capture) => capture.presence[text])?.version || null,
    ]),
  ),
  options,
  transitions,
};

const outputDirectory = resolve(
  "captures/history",
  options.section,
  timestamp(),
);
await mkdir(resolve("captures/history", options.section), { recursive: true });
await mkdir(outputDirectory);
const files = {
  "summary.json": `${JSON.stringify(summary, null, 2)}\n`,
  "versions.json": `${JSON.stringify(captures, null, 2)}\n`,
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
console.log(JSON.stringify(summary, null, 2));

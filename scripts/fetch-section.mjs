#!/usr/bin/env node

import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { pathToFileURL } from "node:url";
import process from "node:process";
import { htmlToText } from "html-to-text";
import { MunicodeClient, parseSectionReference } from "../lib/municode-client.mjs";

export function parseArgs(argv) {
  const options = {
    division: undefined,
    expects: [],
    output: "captures/api",
    section: undefined,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    switch (argument) {
      case "--expect":
        options.expects.push(requiredValue(argv, ++index, argument));
        break;
      case "--division":
        options.division = requiredValue(argv, ++index, argument);
        break;
      case "--output":
        options.output = requiredValue(argv, ++index, argument);
        break;
      case "--section":
        options.section = requiredValue(argv, ++index, argument);
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

function requiredValue(argv, index, flag) {
  const value = argv[index];
  if (!value || value.startsWith("--")) {
    throw new Error(`${flag} requires a value`);
  }
  return value;
}

function timestamp() {
  return (
    new Date().toISOString().replaceAll(":", "-") +
    `-${randomUUID().slice(0, 8)}`
  );
}

function hash(content) {
  return createHash("sha256").update(content).digest("hex");
}

async function artifactMetadata(directory, files) {
  const artifacts = {};
  for (const file of files) {
    const content = await readFile(join(directory, file));
    artifacts[file] = { bytes: content.byteLength, sha256: hash(content) };
  }
  return artifacts;
}

export async function fetchSection(options, client = new MunicodeClient()) {
  const startedAt = new Date().toISOString();
  const resolved = await client.resolveSection(options.section, {
    division: options.division,
  });
  const response = await client.content(resolved.node.Id);
  const document = response.Docs.find((doc) => doc.Id === resolved.node.Id);
  if (!document) {
    throw new Error(
      `Content response did not include resolved node ${resolved.node.Id}`,
    );
  }

  const contentText = htmlToText(document.Content, {
    selectors: [
      { selector: "a", options: { ignoreHref: true } },
      { selector: "img", format: "skip" },
    ],
    wordwrap: false,
  });
  const documentText = `${document.Title}\n\n${contentText.trim()}\n`;
  const expectedText = Object.fromEntries(
    options.expects.map((expected) => [expected, documentText.includes(expected)]),
  );
  const expectationsMet =
    options.expects.length > 0
      ? Object.values(expectedText).every(Boolean)
      : null;
  const outputDirectory = resolve(
    options.output,
    options.section,
    timestamp(),
  );
  await mkdir(resolve(options.output, options.section), { recursive: true });
  await mkdir(outputDirectory);

  const files = {
    "content-response.json": `${JSON.stringify(response, null, 2)}\n`,
    "discovery-responses.json":
      `${JSON.stringify(client.responseArchive, null, 2)}\n`,
    "section.html": `${document.TitleHtml}\n${document.Content}\n`,
    "section.txt": documentText,
    "toc-lineage.json": `${JSON.stringify(resolved.lineage, null, 2)}\n`,
  };
  for (const [file, content] of Object.entries(files)) {
    await writeFile(join(outputDirectory, file), content);
  }

  const publication = await client.discoverPublication();
  const metadata = {
    artifacts: await artifactMetadata(outputDirectory, Object.keys(files)),
    capture: {
      completedAt: new Date().toISOString(),
      expectedText,
      expectationsChecked: options.expects.length,
      expectationsMet,
      expectationsSource: "section.txt",
      division: resolved.division,
      humanReadableUrl:
        `https://library.municode.com/ca/mendocino_county/codes/code_of_ordinances` +
        `?nodeId=${encodeURIComponent(resolved.node.Id)}`,
      nodeId: resolved.node.Id,
      section: options.section,
      startedAt,
    },
    environment: {
      htmlToText: JSON.parse(
        await readFile(
          new URL("../node_modules/html-to-text/package.json", import.meta.url),
          "utf8",
        ),
      ).version,
      node: process.version,
      platform: `${process.platform}-${process.arch}`,
    },
    publication,
    requests: client.requestLog,
  };
  await writeFile(
    join(outputDirectory, "metadata.json"),
    `${JSON.stringify(metadata, null, 2)}\n`,
  );

  return { expectationsMet, metadata, outputDirectory };
}

function usage() {
  return `Usage:
  npm run fetch:section -- --section <number> [options]

Options:
  --division <id>  Restrict Title 20 lookup (default: II)
  --expect <text>   Require text in section content; repeatable
  --output <path>   Artifact root (default: captures/api)
`;
}

async function main() {
  try {
    const options = parseArgs(process.argv.slice(2));
    const result = await fetchSection(options);
    console.log(result.outputDirectory);
    if (!result.expectationsMet) process.exitCode = 2;
  } catch (error) {
    console.error(error.message);
    console.error(usage());
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}

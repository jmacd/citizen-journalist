#!/usr/bin/env node

import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { parse } from "yaml";

const manifestPath = resolve(
  process.argv[2] || "cases/UM_2025-0004/manifest.yaml",
);
const manifest = parse(await readFile(manifestPath, "utf8"));
const questionsPath = resolve("cases/UM_2025-0004/questions.yaml");
const questions = parse(await readFile(questionsPath, "utf8"));
const waterLawPath = resolve("cases/UM_2025-0004/water-law.yaml");
const waterLaw = parse(await readFile(waterLawPath, "utf8"));
const authorityChainPath = resolve("cases/UM_2025-0004/authority-chain.yaml");
const authorityChain = parse(await readFile(authorityChainPath, "utf8"));

const data = {
  generatedAt: new Date().toISOString(),
  ...manifest,
  questions: questions.questions,
  waterLaw,
  authorityChain,
};

await writeFile(
  resolve("web/casebook-data.js"),
  `window.MENDO_CASEBOOK_DATA = ${JSON.stringify(data, null, 2)};\n`,
);
console.log("web/casebook-data.js");

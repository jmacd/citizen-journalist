#!/usr/bin/env node

import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { basename, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import process from "node:process";
import { chromium } from "playwright-core";

const DEFAULT_CHROME =
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const DEFAULT_TIMEOUT_MS = 120_000;
const MAX_RESPONSE_BYTES = 20 * 1024 * 1024;
const ALLOWED_HOSTS = new Set(["library.municode.com"]);
const SENSITIVE_HEADERS = new Set([
  "authorization",
  "cookie",
  "proxy-authorization",
  "set-cookie",
]);

export function parseArgs(argv) {
  const options = {
    chrome: process.env.CHROME_PATH || DEFAULT_CHROME,
    expects: [],
    headed: false,
    output: "captures",
    timeout: DEFAULT_TIMEOUT_MS,
    url: undefined,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (!argument.startsWith("--") && !options.url) {
      options.url = argument;
      continue;
    }

    switch (argument) {
      case "--chrome":
        options.chrome = requiredValue(argv, ++index, argument);
        break;
      case "--expect":
        options.expects.push(requiredValue(argv, ++index, argument));
        break;
      case "--headed":
        options.headed = true;
        break;
      case "--output":
        options.output = requiredValue(argv, ++index, argument);
        break;
      case "--timeout":
        options.timeout = Number(requiredValue(argv, ++index, argument)) * 1000;
        if (!Number.isFinite(options.timeout) || options.timeout <= 0) {
          throw new Error("--timeout must be a positive number of seconds");
        }
        break;
      default:
        throw new Error(`Unknown argument: ${argument}`);
    }
  }

  if (!options.url) {
    throw new Error("A MuniCode section URL is required");
  }

  const url = new URL(options.url);
  if (url.protocol !== "https:" || !ALLOWED_HOSTS.has(url.hostname)) {
    throw new Error(
      `Only public HTTPS pages on ${[...ALLOWED_HOSTS].join(", ")} are allowed`,
    );
  }
  options.url = url.toString();

  return options;
}

function requiredValue(argv, index, flag) {
  const value = argv[index];
  if (!value || value.startsWith("--")) {
    throw new Error(`${flag} requires a value`);
  }
  return value;
}

export function sanitizeHar(value) {
  if (Array.isArray(value)) {
    return value.map(sanitizeHar);
  }
  if (!value || typeof value !== "object") {
    return value;
  }

  const sanitized = {};
  for (const [key, child] of Object.entries(value)) {
    if (key === "headers" && Array.isArray(child)) {
      sanitized[key] = child.filter(
        (header) => !SENSITIVE_HEADERS.has(header.name?.toLowerCase()),
      );
    } else if (key === "postData") {
      sanitized[key] = { mimeType: child?.mimeType, text: "[redacted]" };
    } else if (
      ["cookies", "queryString"].includes(key) &&
      Array.isArray(child)
    ) {
      sanitized[key] = key === "cookies" ? [] : child.map(sanitizeHar);
    } else {
      sanitized[key] = sanitizeHar(child);
    }
  }
  return sanitized;
}

export function sha256(content) {
  return createHash("sha256").update(content).digest("hex");
}

function timestamp() {
  return (
    new Date().toISOString().replaceAll(":", "-") +
    `-${randomUUID().slice(0, 8)}`
  );
}

function safeName(url) {
  const nodeId = new URL(url).searchParams.get("nodeId");
  const original = nodeId || basename(new URL(url).pathname) || "municode";
  const prefix = original
    .replaceAll(/[^A-Za-z0-9._-]+/g, "-")
    .slice(0, 120);
  return `${prefix}-${sha256(original).slice(0, 8)}`;
}

function contentExtension(contentType) {
  if (contentType.includes("json")) return ".json";
  if (contentType.includes("html")) return ".html";
  if (contentType.includes("javascript")) return ".js";
  if (contentType.includes("xml")) return ".xml";
  if (contentType.startsWith("text/")) return ".txt";
  return ".bin";
}

async function writeResponse(response, directory, sequence) {
  const request = response.request();
  const requestMethod = request.method();
  const responseStatus = response.status();
  const responseUrlText = response.url();
  const responseUrl = new URL(responseUrlText);
  const contentType = response.headers()["content-type"] || "";
  const isRelevantHost =
    responseUrl.hostname.endsWith(".municode.com") ||
    responseUrl.hostname.endsWith(".civicplus.com") ||
    responseUrl.hostname.endsWith(".azurewebsites.net") ||
    responseUrl.hostname.endsWith(".blob.core.usgovcloudapi.net");
  const isRelevantType =
    ["document", "fetch", "xhr"].includes(request.resourceType()) ||
    /json|html|xml|text/.test(contentType);

  if (!isRelevantHost || !isRelevantType) return undefined;

  let body;
  try {
    body = await response.body();
  } catch {
    return undefined;
  }
  if (body.byteLength > MAX_RESPONSE_BYTES) return undefined;

  const digest = sha256(body);
  const file = `${digest}${contentExtension(contentType)}`;
  await writeFile(join(directory, file), body);
  return {
    contentType,
    file,
    method: requestMethod,
    sequence,
    sha256: digest,
    status: responseStatus,
    url: responseUrlText,
  };
}

async function hashesFor(directory, files) {
  const hashes = {};
  for (const file of files) {
    const content = await readFile(join(directory, file));
    hashes[file] = {
      bytes: content.byteLength,
      sha256: sha256(content),
    };
  }
  return hashes;
}

export async function capture(options) {
  const startedAt = new Date();
  const outputDirectory = resolve(
    options.output,
    safeName(options.url),
    timestamp(),
  );
  const networkDirectory = join(outputDirectory, "network");
  const rawHar = join(outputDirectory, "network.raw.har");
  await mkdir(resolve(options.output, safeName(options.url)), {
    recursive: true,
  });
  await mkdir(outputDirectory);
  await mkdir(networkDirectory);

  const browser = await chromium.launch({
    executablePath: options.chrome,
    headless: !options.headed,
  });
  const context = await browser.newContext({
    acceptDownloads: true,
    recordHar: {
      content: "embed",
      mode: "full",
      path: rawHar,
    },
    serviceWorkers: "block",
    viewport: { height: 1200, width: 1600 },
  });
  const page = await context.newPage();
  page.setDefaultTimeout(options.timeout);

  const consoleMessages = [];
  const pageErrors = [];
  const responsePromises = [];
  let responseSequence = 0;

  page.on("console", (message) => {
    consoleMessages.push({
      text: message.text(),
      type: message.type(),
    });
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", (response) => {
    responseSequence += 1;
    responsePromises.push(
      writeResponse(response, networkDirectory, responseSequence),
    );
  });

  let navigationError = null;
  let renderError = null;
  try {
    await page.goto(options.url, {
      timeout: options.timeout,
      waitUntil: "domcontentloaded",
    });
    await page.waitForFunction(
      () => {
        const text = document.body?.innerText || "";
        return (
          text.length > 500 &&
          !/enable javascript to run this app/i.test(text)
        );
      },
      undefined,
      { timeout: options.timeout },
    );
    await page.waitForTimeout(2_000);
  } catch (error) {
    navigationError = error.message;
  }

  let bodyText = "";
  let html = "";
  let sectionText = "";
  let sectionSelector = null;
  try {
    bodyText = await page.locator("body").innerText();
    html = await page.content();
    const nodeId = new URL(page.url()).searchParams.get("nodeId");
    if (nodeId) {
      sectionSelector = `[id="c_${nodeId}"]`;
      sectionText = await page.locator(sectionSelector).innerText();
    }
  } catch (error) {
    renderError = error.message;
  }

  const expectedText = Object.fromEntries(
    options.expects.map((expected) => [expected, sectionText.includes(expected)]),
  );
  const expectationsMet =
    options.expects.length > 0
      ? Object.values(expectedText).every(Boolean)
      : null;

  await writeFile(join(outputDirectory, "rendered.html"), html);
  await writeFile(join(outputDirectory, "rendered.txt"), bodyText);
  await writeFile(join(outputDirectory, "section-rendered.txt"), sectionText);
  await page.emulateMedia({ media: "screen" });
  await page.screenshot({
    fullPage: true,
    path: join(outputDirectory, "full-page.png"),
  });
  await page.pdf({
    format: "Letter",
    margin: { bottom: "0.5in", left: "0.5in", right: "0.5in", top: "0.5in" },
    path: join(outputDirectory, "rendered.pdf"),
    printBackground: true,
  });

  const finalUrl = page.url();
  const title = await page.title();
  const responses = (await Promise.all(responsePromises)).filter(Boolean);
  await context.close();
  await browser.close();

  try {
    const har = sanitizeHar(JSON.parse(await readFile(rawHar, "utf8")));
    await writeFile(
      join(outputDirectory, "network.har"),
      `${JSON.stringify(har, null, 2)}\n`,
    );
  } finally {
    await rm(rawHar, { force: true });
  }

  const artifactFiles = [
    "full-page.png",
    "network.har",
    "rendered.html",
    "rendered.pdf",
    "rendered.txt",
    "section-rendered.txt",
  ];
  const metadata = {
    artifacts: await hashesFor(outputDirectory, artifactFiles),
    capture: {
      completedAt: new Date().toISOString(),
      expectedText,
      expectationsChecked: options.expects.length,
      expectationsMet,
      expectationsSource: "section-rendered.txt",
      finalUrl,
      navigationError,
      renderError,
      requestedUrl: options.url,
      sectionSelector,
      startedAt: startedAt.toISOString(),
      title,
    },
    environment: {
      chromeExecutable: options.chrome,
      node: process.version,
      platform: `${process.platform}-${process.arch}`,
      playwright: JSON.parse(
        await readFile(
          new URL("../node_modules/playwright-core/package.json", import.meta.url),
          "utf8",
        ),
      ).version,
    },
    pageErrors,
    consoleMessages,
    responses,
  };
  await writeFile(
    join(outputDirectory, "metadata.json"),
    `${JSON.stringify(metadata, null, 2)}\n`,
  );

  return { expectationsMet, outputDirectory };
}

function usage() {
  return `Usage:
  npm run fetch -- <MUNICODE_URL> [options]

Options:
  --expect <text>    Require text in the rendered page; repeatable
  --output <path>    Artifact root (default: captures)
  --timeout <secs>   Navigation/render timeout (default: 120)
  --chrome <path>    Chrome/Chromium executable
  --headed           Show the browser window
`;
}

async function main() {
  try {
    const options = parseArgs(process.argv.slice(2));
    const result = await capture(options);
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

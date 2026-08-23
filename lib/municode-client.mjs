import { createHash } from "node:crypto";

const DEFAULT_BASE_URL = "https://library.municode.com";
const RETRYABLE_STATUS = new Set([429, 500, 502, 503, 504]);
const MAX_TOC_REQUESTS = 250;

export function parseSectionReference(section) {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(section);
  if (!match) {
    throw new Error(
      `Invalid section "${section}"; expected a value such as 20.376.015`,
    );
  }
  return {
    chapter: `${match[1]}.${match[2]}`,
    section,
    title: match[1],
  };
}

export class MunicodeClient {
  constructor({
    baseUrl = DEFAULT_BASE_URL,
    fetchImpl = globalThis.fetch,
    jurisdiction = "ca/mendocino_county",
    productName = "code of ordinances",
    requestDelayMs = 250,
    sleep = (milliseconds) =>
      new Promise((resolve) => setTimeout(resolve, milliseconds)),
  } = {}) {
    this.baseUrl = baseUrl;
    this.fetchImpl = fetchImpl;
    this.jurisdiction = jurisdiction;
    this.productName = productName;
    this.requestDelayMs = requestDelayMs;
    this.sleep = sleep;
    this.requestLog = [];
    this.responseArchive = [];
    this.publication = undefined;
  }

  async discoverPublication() {
    if (this.publication) return this.publication;

    const organization = await this.getJson(
      `/localapi/Organizations/GetByUrlEncodedNames/${this.jurisdiction}`,
    );
    const clientId = organization.ClientID;
    const viewModel = await this.getJson("/api/Products/name", {
      clientId,
      productName: this.productName,
    });
    const product = viewModel.Model;
    const publicationVersion = await this.getJson(
      `/localapi/PublicationVersion/GetViewModel/${clientId}/${encodeURIComponent(this.productName)}`,
    );
    const job = await this.getJson(`/api/Jobs/latest/${product.ProductID}`);
    if (
      job.IsLatest !== true ||
      publicationVersion.isLatest !== true ||
      job.Name !== publicationVersion.name
    ) {
      throw new Error(
        `MuniCode publication mismatch: job=${JSON.stringify(job)}, ` +
          `publicationVersion=${JSON.stringify(publicationVersion)}`,
      );
    }

    this.publication = {
      clientId,
      codifiedThrough: job.BannerText || null,
      jurisdiction: this.jurisdiction,
      job,
      productId: product.ProductID,
      productName: product.ProductName,
      publicationVersion,
    };
    return this.publication;
  }

  async root() {
    const publication = await this.discoverPublication();
    return this.getJson("/api/codesToc", {
      jobId: publication.job.Id,
      productId: publication.productId,
    });
  }

  async children(nodeId) {
    const publication = await this.discoverPublication();
    return this.getJson("/api/codesToc/children", {
      jobId: publication.job.Id,
      nodeId,
      productId: publication.productId,
    });
  }

  async content(nodeId, { groupChunks = false } = {}) {
    const publication = await this.discoverPublication();
    return this.getJson("/api/CodesContent", {
      groupChunks,
      jobId: publication.job.Id,
      nodeId,
      productId: publication.productId,
    });
  }

  async resolveSection(section, { division } = {}) {
    const reference = parseSectionReference(section);
    const root = await this.root();
    const titlePattern = new RegExp(`^Title ${reference.title}\\b`, "i");
    const titleMatches = root.Children.filter((node) =>
      titlePattern.test(node.Heading),
    ).map((node) => ({ lineage: [node], node }));
    if (titleMatches.length === 0) {
      for (const container of root.Children.filter((node) => node.HasChildren)) {
        const children = await this.children(container.Id);
        for (const node of children.filter((child) =>
          titlePattern.test(child.Heading),
        )) {
          titleMatches.push({
            lineage: [container, node],
            node,
          });
        }
      }
    }
    if (titleMatches.length !== 1) {
      throw new Error(
        `Expected one Title ${reference.title} in the TOC; found ` +
          `${titleMatches.length}`,
      );
    }
    const [{ lineage: titleLineage, node: title }] = titleMatches;

    let searchRoot = title;
    let initialLineage = titleLineage;
    if (division) {
      const titleChildren = await this.children(title.Id);
      const divisionPattern = new RegExp(
        `^DIVISION ${escapeRegex(division)}(?:\\s|\\b)`,
        "i",
      );
      const divisions = titleChildren.filter((node) =>
        divisionPattern.test(node.Heading),
      );
      if (divisions.length !== 1) {
        throw new Error(
          `Expected one Division ${division} under Title ${reference.title}; ` +
            `found ${divisions.length}`,
        );
      }
      [searchRoot] = divisions;
      initialLineage = [...titleLineage, searchRoot];
    }

    const chapterMatches = await this.findDescendants({
      initialLineage,
      matches: (node) =>
        new RegExp(
          `^CHAPTER ${escapeRegex(reference.chapter)}(?![\\d.])`,
          "i",
        ).test(node.Heading),
      maxDepth: 5,
      root: searchRoot,
      shouldDescend: (node) => !/^CHAPTER\b/i.test(node.Heading),
    });
    if (chapterMatches.length !== 1) {
      throw new Error(
        `Expected one Chapter ${reference.chapter} under Title ` +
          `${reference.title}${division ? ` Division ${division}` : ""}; ` +
          `found ${chapterMatches.length}`,
      );
    }
    const [{ node: chapter, lineage: chapterLineage }] = chapterMatches;

    const sectionMatches = await this.findDescendants({
      initialLineage: chapterLineage,
      matches: (node) =>
        new RegExp(
          `^Sec\\. ${escapeRegex(reference.section)}(?![\\d.])`,
          "i",
        ).test(node.Heading),
      maxDepth: 4,
      root: chapter,
      shouldDescend: (node) => !/^Sec\./i.test(node.Heading),
    });
    if (sectionMatches.length !== 1) {
      throw new Error(
        `Expected one Section ${reference.section} under ${chapter.Heading}; ` +
          `found ${sectionMatches.length}`,
      );
    }
    const [{ node: sectionNode, lineage }] = sectionMatches;

    return {
      division: division || null,
      lineage,
      node: sectionNode,
      reference,
    };
  }

  async findDescendants({
    initialLineage,
    matches,
    maxDepth,
    root,
    shouldDescend,
  }) {
    const queue = [{ depth: 0, lineage: initialLineage, node: root }];
    const results = [];
    let requestCount = 0;

    while (queue.length > 0) {
      const current = queue.shift();
      if (current.depth >= maxDepth || !current.node.HasChildren) continue;
      requestCount += 1;
      if (requestCount > MAX_TOC_REQUESTS) {
        throw new Error(
          `TOC traversal exceeded ${MAX_TOC_REQUESTS} child requests`,
        );
      }
      const children = await this.children(current.node.Id);
      for (const child of children) {
        const lineage = [...current.lineage, child];
        if (matches(child)) results.push({ lineage, node: child });
        if (child.HasChildren && shouldDescend(child)) {
          queue.push({
            depth: current.depth + 1,
            lineage,
            node: child,
          });
        }
      }
    }
    return results;
  }

  async getJson(path, query = undefined) {
    const url = new URL(path, this.baseUrl);
    for (const [name, value] of Object.entries(query || {})) {
      url.searchParams.set(name, String(value));
    }

    let lastError;
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      if (this.requestLog.length > 0 && this.requestDelayMs > 0) {
        await this.sleep(this.requestDelayMs);
      }
      const startedAt = new Date().toISOString();
      let response;
      try {
        response = await this.fetchImpl(url, {
          headers: {
            accept: "application/json",
            "user-agent": "mendo-codebook/1.0 (+public-record research)",
            "x-csrf": "1",
          },
          signal: AbortSignal.timeout(30_000),
        });
        const text = await response.text();
        const logEntry = {
          attempt,
          bodySha256: sha256(text),
          completedAt: new Date().toISOString(),
          contentType: response.headers.get("content-type"),
          method: "GET",
          responseUrl: response.url || url.toString(),
          startedAt,
          status: response.status,
          url: url.toString(),
        };
        this.requestLog.push(logEntry);

        if (response.ok) {
          const parsed = JSON.parse(text);
          this.responseArchive.push({
            body: parsed,
            request: logEntry,
          });
          return parsed;
        }
        const error = new Error(
          `MuniCode returned HTTP ${response.status} for ${url}`,
        );
        error.status = response.status;
        error.responseBody = text;
        if (!RETRYABLE_STATUS.has(response.status)) throw error;
        lastError = error;
      } catch (error) {
        if (!response) {
          this.requestLog.push({
            attempt,
            completedAt: new Date().toISOString(),
            error: error.message,
            method: "GET",
            startedAt,
            url: url.toString(),
          });
        }
        if (error.status && !RETRYABLE_STATUS.has(error.status)) throw error;
        lastError = error;
      }
      if (attempt < 4) {
        const retryAfter = Number(response?.headers.get("retry-after"));
        await this.sleep(
          Number.isFinite(retryAfter) && retryAfter > 0
            ? retryAfter * 1000
            : 250 * 2 ** (attempt - 1),
        );
      }
    }
    throw lastError;
  }
}

function sha256(content) {
  return createHash("sha256").update(content).digest("hex");
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

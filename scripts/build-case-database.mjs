#!/usr/bin/env node

import { readFile, mkdir, rm, stat } from "node:fs/promises";
import { resolve } from "node:path";
import Database from "better-sqlite3";
import { convert } from "html-to-text";
import { getDocument } from "pdfjs-dist/legacy/build/pdf.mjs";
import { parse } from "yaml";

const caseId = process.argv[2] || "UM_2025-0004";
const caseRoot = resolve("cases", caseId);
const outputPath = resolve("captures/cases", caseId, "casebook.sqlite");
const manifest = parse(await readFile(resolve(caseRoot, "manifest.yaml"), "utf8"));
const questions = parse(await readFile(resolve(caseRoot, "questions.yaml"), "utf8"));
const conditionVersions = parse(
  await readFile(resolve(caseRoot, "condition-versions.yaml"), "utf8"),
);
const publicRequestIndex = parse(
  await readFile(resolve(caseRoot, "public-request-index.yaml"), "utf8"),
);
const recordsRequests = parse(
  await readFile(resolve(caseRoot, "records-requests.yaml"), "utf8"),
);
const waterLaw = parse(await readFile(resolve(caseRoot, "water-law.yaml"), "utf8"));
const authorityChain = parse(
  await readFile(resolve(caseRoot, "authority-chain.yaml"), "utf8"),
);
const acquisitionLog = parse(
  await readFile(resolve(caseRoot, "acquisition-log.yaml"), "utf8"),
);

async function extractPdf(path) {
  const bytes = new Uint8Array(await readFile(path));
  const pdf = await getDocument({ data: bytes }).promise;
  const pages = [];
  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber);
    const content = await page.getTextContent();
    pages.push(content.items.map((item) => item.str).join(" "));
  }
  return pages;
}

await mkdir(resolve("captures/cases", caseId), { recursive: true });
await rm(outputPath, { force: true });
const db = new Database(outputPath);
db.exec(`
  PRAGMA foreign_keys = ON;
  CREATE TABLE cases (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    applicant TEXT,
    description TEXT
  );
  CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    publisher TEXT,
    document_date TEXT,
    published_at TEXT,
    document_id TEXT,
    url TEXT,
    attachment_url TEXT,
    status TEXT NOT NULL,
    capture_path TEXT,
    sha256 TEXT,
    bytes INTEGER,
    ocr_path TEXT,
    ocr_sha256 TEXT,
    note TEXT
  );
  CREATE TABLE acquisition_attempts (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    attempted_at TEXT,
    repository TEXT NOT NULL,
    method TEXT NOT NULL,
    query TEXT,
    url TEXT,
    status TEXT NOT NULL,
    http_status INTEGER,
    result TEXT,
    note TEXT
  );
  CREATE TABLE document_pages (
    document_id TEXT NOT NULL REFERENCES documents(id),
    page_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (document_id, page_number)
  );
  CREATE VIRTUAL TABLE document_search USING fts5(
    document_id UNINDEXED,
    page_number UNINDEXED,
    title,
    publisher,
    text,
    tokenize = 'porter unicode61'
  );
  CREATE TABLE transcript_segments (
    document_id TEXT NOT NULL REFERENCES documents(id),
    segment_index INTEGER NOT NULL,
    start_seconds REAL NOT NULL,
    end_seconds REAL NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (document_id, segment_index)
  );
  CREATE VIRTUAL TABLE transcript_search USING fts5(
    document_id UNINDEXED,
    segment_index UNINDEXED,
    start_seconds UNINDEXED,
    end_seconds UNINDEXED,
    title,
    publisher,
    text,
    tokenize = 'porter unicode61'
  );
  CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    event_date TEXT NOT NULL,
    description TEXT NOT NULL
  );
  CREATE TABLE event_sources (
    event_id INTEGER NOT NULL REFERENCES events(id),
    document_id TEXT NOT NULL REFERENCES documents(id),
    PRIMARY KEY (event_id, document_id)
  );
  CREATE TABLE meeting_cycles (
    id TEXT PRIMARY KEY,
    dates TEXT,
    title TEXT NOT NULL,
    forum TEXT,
    summary TEXT
  );
  CREATE TABLE cycle_sources (
    cycle_id TEXT NOT NULL REFERENCES meeting_cycles(id),
    document_id TEXT NOT NULL REFERENCES documents(id),
    PRIMARY KEY (cycle_id, document_id)
  );
  CREATE TABLE condition_families (
    id TEXT PRIMARY KEY,
    permit TEXT NOT NULL
  );
  CREATE TABLE condition_versions (
    id TEXT PRIMARY KEY,
    family_id TEXT NOT NULL REFERENCES condition_families(id),
    version_date TEXT,
    status TEXT NOT NULL,
    condition_count INTEGER,
    evidence TEXT,
    document_id TEXT REFERENCES documents(id),
    supersedes TEXT,
    note TEXT,
    warning TEXT
  );
  CREATE TABLE condition_changes (
    version_id TEXT NOT NULL REFERENCES condition_versions(id),
    item_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (version_id, item_number)
  );
  CREATE TABLE authorities (
    id TEXT PRIMARY KEY,
    citation TEXT NOT NULL,
    title TEXT NOT NULL,
    topic TEXT,
    url TEXT,
    effect TEXT,
    does_not_establish TEXT
  );
  CREATE TABLE boundaries (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT,
    authority TEXT,
    description TEXT
  );
  CREATE TABLE boundary_sources (
    boundary_id TEXT NOT NULL REFERENCES boundaries(id),
    document_id TEXT NOT NULL REFERENCES documents(id),
    PRIMARY KEY (boundary_id, document_id)
  );
  CREATE TABLE institutional_roles (
    actor TEXT PRIMARY KEY,
    can_authorize TEXT,
    cannot_establish_alone TEXT
  );
  CREATE TABLE authority_chain_actors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    powers TEXT NOT NULL,
    limits TEXT NOT NULL
  );
  CREATE TABLE authority_chain_actor_sources (
    actor_id TEXT NOT NULL REFERENCES authority_chain_actors(id),
    document_id TEXT NOT NULL REFERENCES documents(id),
    PRIMARY KEY (actor_id, document_id)
  );
  CREATE TABLE legal_instruments (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    effect TEXT NOT NULL,
    limits TEXT NOT NULL
  );
  CREATE TABLE legal_instrument_sources (
    instrument_id TEXT NOT NULL REFERENCES legal_instruments(id),
    document_id TEXT NOT NULL REFERENCES documents(id),
    PRIMARY KEY (instrument_id, document_id)
  );
  CREATE TABLE authority_relationships (
    id TEXT PRIMARY KEY,
    from_actor TEXT NOT NULL REFERENCES authority_chain_actors(id),
    to_actor TEXT NOT NULL REFERENCES authority_chain_actors(id),
    relationship TEXT NOT NULL,
    analysis TEXT NOT NULL
  );
  CREATE TABLE authority_relationship_sources (
    relationship_id TEXT NOT NULL REFERENCES authority_relationships(id),
    document_id TEXT NOT NULL REFERENCES documents(id),
    PRIMARY KEY (relationship_id, document_id)
  );
  CREATE TABLE authority_decision_steps (
    step INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    why TEXT NOT NULL
  );
  CREATE TABLE authority_unresolved (
    id INTEGER PRIMARY KEY,
    issue TEXT NOT NULL
  );
  CREATE TABLE questions (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    status TEXT NOT NULL,
    short_answer TEXT
  );
  CREATE TABLE claims (
    id INTEGER PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES questions(id),
    claim TEXT NOT NULL,
    confidence TEXT,
    document_id TEXT REFERENCES documents(id),
    locator TEXT
  );
  CREATE TABLE question_gaps (
    id INTEGER PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES questions(id),
    deciding_record TEXT NOT NULL
  );
  CREATE TABLE missing_records (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    why TEXT NOT NULL
  );
  CREATE TABLE record_requests (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    custodian TEXT NOT NULL,
    email TEXT,
    office TEXT,
    subject TEXT NOT NULL,
    basis_document_id TEXT REFERENCES documents(id),
    basis_note TEXT
  );
  CREATE TABLE request_items (
    request_id TEXT NOT NULL REFERENCES record_requests(id),
    item_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (request_id, item_number)
  );
  CREATE TABLE public_requests (
    id TEXT PRIMARY KEY,
    request_date TEXT,
    state TEXT,
    visibility TEXT,
    departments TEXT,
    url TEXT NOT NULL,
    request_text TEXT NOT NULL,
    disposition TEXT,
    relevance TEXT
  );
  CREATE TABLE public_request_documents (
    request_id TEXT NOT NULL REFERENCES public_requests(id),
    portal_document_id TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    document_id TEXT REFERENCES documents(id),
    PRIMARY KEY (request_id, portal_document_id)
  );
`);

db.prepare(`
  INSERT INTO cases (id, title, status, applicant, description)
  VALUES (?, ?, ?, ?, ?)
`).run(
  manifest.case.id,
  manifest.case.title,
  manifest.case.status,
  manifest.case.applicant,
  manifest.case.description,
);

const insertDocument = db.prepare(`
  INSERT INTO documents
    (id, title, publisher, document_date, published_at, document_id, url,
     attachment_url, status, capture_path, sha256, bytes, ocr_path, ocr_sha256,
     note)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);
const insertPage = db.prepare(`
  INSERT INTO document_pages (document_id, page_number, text) VALUES (?, ?, ?)
`);
const insertSearch = db.prepare(`
  INSERT INTO document_search (document_id, page_number, title, publisher, text)
  VALUES (?, ?, ?, ?, ?)
`);
const insertTranscriptSegment = db.prepare(`
  INSERT INTO transcript_segments
    (document_id, segment_index, start_seconds, end_seconds, text)
  VALUES (?, ?, ?, ?, ?)
`);
const insertTranscriptSearch = db.prepare(`
  INSERT INTO transcript_search
    (document_id, segment_index, start_seconds, end_seconds, title, publisher, text)
  VALUES (?, ?, ?, ?, ?, ?, ?)
`);

for (const source of manifest.sources) {
  insertDocument.run(
    source.id,
    source.title,
    source.publisher || null,
    source.document_date?.toString() || null,
    source.published_at?.toString() || null,
    source.document_id?.toString() || null,
    source.url || null,
    source.attachment_url || null,
    source.status,
    source.capture_path || null,
    source.sha256 || null,
    source.bytes || null,
    source.ocr?.path || null,
    source.ocr?.sha256 || null,
    source.note || null,
  );

  if (source.transcript?.path?.toLowerCase().endsWith(".json")) {
    const transcript = JSON.parse(
      await readFile(resolve(source.transcript.path), "utf8"),
    );
    for (const [index, segment] of (transcript.segments || []).entries()) {
      const text = String(segment.text || "").trim();
      if (!text) continue;
      insertTranscriptSegment.run(
        source.id,
        index,
        Number(segment.start),
        Number(segment.end),
        text,
      );
      insertTranscriptSearch.run(
        source.id,
        index,
        Number(segment.start),
        Number(segment.end),
        source.title,
        source.publisher || "",
        text,
      );
    }
  }

  if (source.capture_path?.toLowerCase().endsWith(".html")) {
    const html = await readFile(resolve(source.capture_path), "utf8");
    const text = convert(html, {
      selectors: [
        { selector: "script", format: "skip" },
        { selector: "style", format: "skip" },
        { selector: "nav", format: "skip" },
      ],
      wordwrap: false,
    }).trim();
    insertPage.run(source.id, 1, text);
    insertSearch.run(
      source.id,
      1,
      source.title,
      source.publisher || "",
      text,
    );
  }

  if (!source.capture_path?.toLowerCase().endsWith(".pdf")) continue;
  try {
    await stat(resolve(source.capture_path));
    let pages = await extractPdf(resolve(source.capture_path));
    if (source.ocr?.path) {
      const ocrPages = (await readFile(resolve(source.ocr.path), "utf8"))
        .split("\f")
        .map((text) => text.trim())
      if (ocrPages.length === pages.length) {
        pages = pages.map((text, index) => {
          const embeddedText = text.trim();
          const ocrText = ocrPages[index];
          return embeddedText.length < 200 && ocrText.length > embeddedText.length
            ? ocrText
            : text;
        });
      } else if (pages.every((text) => text.trim().length === 0)) {
        pages = ocrPages.filter(Boolean);
      }
    }
    pages.forEach((text, index) => {
      insertPage.run(source.id, index + 1, text);
      insertSearch.run(source.id, index + 1, source.title, source.publisher || "", text);
    });
  } catch (error) {
    console.warn(`Could not index ${source.id}: ${error.message}`);
  }
}

const insertEvent = db.prepare(`
  INSERT INTO events (event_date, description) VALUES (?, ?)
`);
const insertEventSource = db.prepare(`
  INSERT OR IGNORE INTO event_sources (event_id, document_id) VALUES (?, ?)
`);
for (const event of manifest.events) {
  const result = insertEvent.run(event.date.toString(), event.event);
  for (const sourceId of event.source_ids || []) {
    insertEventSource.run(Number(result.lastInsertRowid), sourceId);
  }
}

const insertCycle = db.prepare(`
  INSERT INTO meeting_cycles (id, dates, title, forum, summary) VALUES (?, ?, ?, ?, ?)
`);
const insertCycleSource = db.prepare(`
  INSERT OR IGNORE INTO cycle_sources (cycle_id, document_id) VALUES (?, ?)
`);
for (const cycle of manifest.meeting_cycles) {
  insertCycle.run(cycle.id, cycle.dates, cycle.title, cycle.forum, cycle.summary);
  for (const sourceId of cycle.source_ids || []) {
    insertCycleSource.run(cycle.id, sourceId);
  }
}

const insertConditionFamily = db.prepare(`
  INSERT INTO condition_families (id, permit) VALUES (?, ?)
`);
const insertConditionVersion = db.prepare(`
  INSERT INTO condition_versions
    (id, family_id, version_date, status, condition_count, evidence, document_id,
     supersedes, note, warning)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);
const insertConditionChange = db.prepare(`
  INSERT INTO condition_changes (version_id, item_number, description)
  VALUES (?, ?, ?)
`);
for (const family of conditionVersions.logical_families) {
  insertConditionFamily.run(family.id, family.permit);
  for (const version of family.versions) {
    insertConditionVersion.run(
      version.id,
      family.id,
      version.date?.toString() || null,
      version.status,
      version.condition_count ?? null,
      version.evidence || null,
      version.source_id || null,
      version.supersedes || null,
      version.note || null,
      version.warning || null,
    );
    const changes = version.changes || version.changes_from_previous ||
      version.changes_from_adopted_2024 || [];
    changes.forEach((change, index) => {
      insertConditionChange.run(version.id, index + 1, change);
    });
  }
}

const insertAuthority = db.prepare(`
  INSERT INTO authorities
    (id, citation, title, topic, url, effect, does_not_establish)
  VALUES (?, ?, ?, ?, ?, ?, ?)
`);
for (const authority of waterLaw.authorities) {
  insertAuthority.run(
    authority.id,
    authority.citation,
    authority.title,
    authority.topic,
    authority.url,
    authority.effect,
    authority.does_not_establish || null,
  );
}

const insertBoundary = db.prepare(`
  INSERT INTO boundaries (id, name, kind, status, authority, description)
  VALUES (?, ?, ?, ?, ?, ?)
`);
const insertBoundarySource = db.prepare(`
  INSERT OR IGNORE INTO boundary_sources (boundary_id, document_id) VALUES (?, ?)
`);
for (const boundary of waterLaw.boundaries) {
  insertBoundary.run(
    boundary.id,
    boundary.name,
    boundary.kind,
    boundary.status,
    boundary.authority,
    boundary.description || null,
  );
  for (const sourceId of boundary.source_ids || []) {
    insertBoundarySource.run(boundary.id, sourceId);
  }
}

const insertRole = db.prepare(`
  INSERT INTO institutional_roles (actor, can_authorize, cannot_establish_alone)
  VALUES (?, ?, ?)
`);
for (const role of waterLaw.institutional_roles) {
  insertRole.run(role.actor, role.can_authorize, role.cannot_establish_alone);
}

const insertChainActor = db.prepare(`
  INSERT INTO authority_chain_actors (id, name, role, powers, limits)
  VALUES (?, ?, ?, ?, ?)
`);
const insertChainActorSource = db.prepare(`
  INSERT INTO authority_chain_actor_sources (actor_id, document_id) VALUES (?, ?)
`);
for (const actor of authorityChain.actors) {
  insertChainActor.run(
    actor.id,
    actor.name,
    actor.role,
    actor.powers.join("\n"),
    actor.limits.join("\n"),
  );
  for (const documentId of actor.source_ids) {
    insertChainActorSource.run(actor.id, documentId);
  }
}

const insertInstrument = db.prepare(`
  INSERT INTO legal_instruments (id, title, kind, effect, limits)
  VALUES (?, ?, ?, ?, ?)
`);
const insertInstrumentSource = db.prepare(`
  INSERT INTO legal_instrument_sources (instrument_id, document_id) VALUES (?, ?)
`);
for (const instrument of authorityChain.instruments) {
  insertInstrument.run(
    instrument.id,
    instrument.title,
    instrument.kind,
    instrument.effect,
    instrument.limits,
  );
  for (const documentId of instrument.source_ids) {
    insertInstrumentSource.run(instrument.id, documentId);
  }
}

const insertAuthorityRelationship = db.prepare(`
  INSERT INTO authority_relationships
    (id, from_actor, to_actor, relationship, analysis)
  VALUES (?, ?, ?, ?, ?)
`);
const insertAuthorityRelationshipSource = db.prepare(`
  INSERT INTO authority_relationship_sources (relationship_id, document_id)
  VALUES (?, ?)
`);
for (const relationship of authorityChain.relationships) {
  insertAuthorityRelationship.run(
    relationship.id,
    relationship.from_actor,
    relationship.to_actor,
    relationship.relationship,
    relationship.analysis,
  );
  for (const documentId of relationship.source_ids) {
    insertAuthorityRelationshipSource.run(relationship.id, documentId);
  }
}

const insertDecisionStep = db.prepare(`
  INSERT INTO authority_decision_steps (step, question, why) VALUES (?, ?, ?)
`);
for (const step of authorityChain.decision_chain) {
  insertDecisionStep.run(step.step, step.question, step.why);
}
const insertAuthorityUnresolved = db.prepare(`
  INSERT INTO authority_unresolved (issue) VALUES (?)
`);
for (const issue of authorityChain.unresolved) {
  insertAuthorityUnresolved.run(issue);
}

const insertQuestion = db.prepare(`
  INSERT INTO questions (id, question, status, short_answer) VALUES (?, ?, ?, ?)
`);
const insertClaim = db.prepare(`
  INSERT INTO claims (question_id, claim, confidence, document_id, locator)
  VALUES (?, ?, ?, ?, ?)
`);
const insertQuestionGap = db.prepare(`
  INSERT INTO question_gaps (question_id, deciding_record) VALUES (?, ?)
`);
for (const question of questions.questions) {
  insertQuestion.run(question.id, question.question, question.status, question.short_answer);
  for (const finding of question.findings || []) {
    const locator = finding.timestamp
      ? `timestamp ${finding.timestamp}`
      : finding.pages
        ? `pages ${finding.pages}`
        : null;
    insertClaim.run(
      question.id,
      finding.claim,
      finding.confidence,
      finding.source_id || null,
      locator,
    );
  }
  for (const unresolved of question.unresolved || []) {
    insertQuestionGap.run(question.id, unresolved);
  }
}

const insertMissing = db.prepare(`
  INSERT INTO missing_records (id, title, why) VALUES (?, ?, ?)
`);
for (const record of waterLaw.priority_missing_records) {
  insertMissing.run(record.id, record.title, record.why);
}

const insertRequest = db.prepare(`
  INSERT INTO record_requests
    (id, status, custodian, email, office, subject, basis_document_id, basis_note)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?)
`);
const insertRequestItem = db.prepare(`
  INSERT INTO request_items (request_id, item_number, description)
  VALUES (?, ?, ?)
`);
for (const request of recordsRequests.requests) {
  insertRequest.run(
    request.id,
    request.status,
    request.custodian,
    request.email || null,
    request.office || null,
    request.subject,
    request.basis?.source_id || null,
    request.basis?.note || null,
  );
  request.requested_records.forEach((item, index) => {
    insertRequestItem.run(request.id, index + 1, item);
  });
}

const insertPublicRequest = db.prepare(`
  INSERT INTO public_requests
    (id, request_date, state, visibility, departments, url, request_text,
     disposition, relevance)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
`);
const insertPublicRequestDocument = db.prepare(`
  INSERT INTO public_request_documents
    (request_id, portal_document_id, title, url, document_id)
  VALUES (?, ?, ?, ?, ?)
`);
for (const request of publicRequestIndex.requests) {
  insertPublicRequest.run(
    request.id,
    request.request_date?.toString() || null,
    request.state || null,
    request.visibility || null,
    (request.departments || []).join("; "),
    request.url,
    request.request_text,
    request.disposition || null,
    request.relevance || null,
  );
  for (const document of request.documents || []) {
    insertPublicRequestDocument.run(
      request.id,
      document.portal_document_id.toString(),
      document.title,
      document.url,
      document.source_id || null,
    );
  }
}

const insertAcquisitionAttempt = db.prepare(`
  INSERT INTO acquisition_attempts
    (id, target_id, attempted_at, repository, method, query, url, status,
     http_status, result, note)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);
for (const attempt of acquisitionLog.attempts) {
  insertAcquisitionAttempt.run(
    attempt.id,
    attempt.target_id,
    attempt.attempted_at?.toString() || null,
    attempt.repository,
    attempt.method,
    attempt.query || null,
    attempt.url || null,
    attempt.status,
    attempt.http_status || null,
    attempt.result || null,
    attempt.note || null,
  );
}

db.exec("PRAGMA optimize");
const counts = Object.fromEntries(
  ["documents", "document_pages", "events", "meeting_cycles", "condition_versions", "authorities", "boundaries", "authority_chain_actors", "legal_instruments", "authority_relationships", "questions", "record_requests", "public_requests", "acquisition_attempts"]
    .map((table) => [table, db.prepare(`SELECT count(*) AS count FROM ${table}`).get().count]),
);
db.close();
console.log(`${outputPath}\n${JSON.stringify(counts)}`);

"""Typed messages shared by roles, deterministic tools, and approval ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class Confidence(StrEnum):
    VERIFIED = "verified"
    SUPPORTED_INTERPRETATION = "supported_interpretation"
    DISPUTED = "disputed"
    UNRESOLVED = "unresolved"
    REJECTED = "rejected"


class DispositionKind(StrEnum):
    ANSWER_READY = "answer_ready"
    NO_CHANGE = "no_change"
    MORE_RESEARCH = "more_research"
    REGISTRATION_APPROVAL = "registration_approval"
    KNOWLEDGE_CHANGE_APPROVAL = "knowledge_change_approval"
    REQUEST_DRAFT_APPROVAL = "request_draft_approval"
    BLOCKED = "blocked"


class ApprovalKind(StrEnum):
    DOCUMENT_REGISTRATION = "document_registration"
    KNOWLEDGE_PROMOTION = "knowledge_promotion"
    SUPERSESSION = "supersession"
    PUBLICATION = "publication"
    EXTERNAL_COMMUNICATION = "external_communication"


@dataclass(frozen=True)
class CaseQuestion:
    case_id: str
    question: str
    asked_by: str = "cio"


@dataclass(frozen=True)
class MonitorObservation:
    monitor_id: str
    observed_at: str
    summary: str
    candidate_urls: tuple[str, ...] = ()
    prior_fingerprint: str | None = None
    current_fingerprint: str | None = None
    change_count: int | None = None


@dataclass(frozen=True)
class EvidenceLocator:
    document_id: str
    page: int | None = None
    section: str | None = None
    timestamp: str | None = None
    field: str | None = None

    def is_precise(self) -> bool:
        return any((self.page, self.section, self.timestamp, self.field))


@dataclass(frozen=True)
class CorpusHit:
    document_id: str
    title: str
    publisher: str
    page: int | None
    excerpt: str
    rank: float
    timestamp: str | None = None


@dataclass(frozen=True)
class AcquisitionCandidate:
    target_id: str
    url: str
    issuing_body: str
    expected_title: str
    cited_by: str | None = None
    expected_date: str | None = None
    expected_document_id: str | None = None


@dataclass(frozen=True)
class StagedDownload:
    candidate: AcquisitionCandidate
    status: str
    attempted_at: str
    http_status: int | None = None
    staging_path: str | None = None
    final_url: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class ValidatedRecord:
    candidate: AcquisitionCandidate
    staging_path: str
    mime_type: str
    byte_count: int
    sha256: str
    duplicate_of: str | None = None
    page_count: int | None = None
    ocr_page_count: int | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Claim:
    text: str
    confidence: Confidence
    locators: tuple[EvidenceLocator, ...]
    does_not_establish: str
    source_version_status: str | None = None


@dataclass(frozen=True)
class EvidenceGap:
    description: str
    deciding_record: str
    likely_custodian: str | None = None
    search_before_request: tuple[str, ...] = ()


@dataclass(frozen=True)
class InstitutionalRuleProposal:
    actor: str
    action: str
    trigger: str
    procedure: str
    geography: str
    temporal_scope: str
    effect: str
    does_not_establish: str
    locators: tuple[EvidenceLocator, ...]


@dataclass(frozen=True)
class WatchProposal:
    agency: str
    repository: str
    reason: str
    identifiers: tuple[str, ...]


@dataclass(frozen=True)
class RecordRequestDraft:
    custodian: str
    subject: str
    requested_records: tuple[str, ...]
    rationale: str
    basis_locators: tuple[EvidenceLocator, ...]


@dataclass(frozen=True)
class Analysis:
    short_answer: str
    claims: tuple[Claim, ...]
    answer_claim_indices: tuple[int, ...] = ()
    gaps: tuple[EvidenceGap, ...] = ()
    rules: tuple[InstitutionalRuleProposal, ...] = ()
    watches: tuple[WatchProposal, ...] = ()
    request_drafts: tuple[RecordRequestDraft, ...] = ()


@dataclass(frozen=True)
class SkepticFinding:
    severity: Literal["error", "warning", "note"]
    code: str
    message: str
    claim_index: int | None = None


@dataclass(frozen=True)
class SkepticReview:
    accepted: bool
    findings: tuple[SkepticFinding, ...] = ()
    targeted_gaps: tuple[EvidenceGap, ...] = ()


@dataclass(frozen=True)
class ApprovalRequest:
    kind: ApprovalKind
    summary: str
    proposed_paths: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    diff: str | None = None


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    feedback: str = ""


@dataclass(frozen=True)
class ApprovalBundle:
    requests: tuple[ApprovalRequest, ...]
    work: EvidenceWork


@dataclass(frozen=True)
class RunDisposition:
    kind: DispositionKind
    summary: str
    analysis: Analysis | None = None
    review: SkepticReview | None = None
    pending_approvals: tuple[ApprovalRequest, ...] = ()
    gaps: tuple[EvidenceGap, ...] = ()


@dataclass
class RunBudget:
    max_research_rounds: int = 2
    research_rounds: int = 0
    tool_calls: int = 0
    downloads: int = 0

    def can_research(self) -> bool:
        return self.research_rounds < self.max_research_rounds

    def record_research_round(self) -> None:
        if not self.can_research():
            raise RuntimeError("Research-round budget exhausted")
        self.research_rounds += 1


@dataclass
class RunEnvelope:
    run_id: str
    input: CaseQuestion | MonitorObservation
    skill_hashes: dict[str, str] = field(default_factory=dict)
    corpus_hits: list[CorpusHit] = field(default_factory=list)
    staged_downloads: list[StagedDownload] = field(default_factory=list)
    staged_records: list[ValidatedRecord] = field(default_factory=list)
    budget: RunBudget = field(default_factory=RunBudget)


@dataclass
class EvidenceWork:
    envelope: RunEnvelope
    gaps: list[EvidenceGap] = field(default_factory=list)
    analysis: Analysis | None = None
    review: SkepticReview | None = None
    review_rounds: int = 0

"""Versioned contracts stored in the implementation-neutral Archive."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Reject unknown fields so schema drift cannot pass silently."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class StoredObject(StrictModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)
    media_type: str = Field(min_length=1)
    original_filename: str = Field(min_length=1)
    archive_path: str = Field(pattern=r"^objects/sha256/[0-9a-f]{2}/[0-9a-f]{64}$")


class SourceProvenance(StrictModel):
    url: str | None = None
    custodian: str | None = None
    retrieved_at: datetime

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
        return value


class IngestMetadata(StrictModel):
    record_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    record_title: str = Field(min_length=1)
    collections: list[str] = Field(min_length=1)
    source_url: str | None = None
    custodian: str | None = None
    retrieved_at: datetime
    media_type: str | None = None

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
        return value

    @field_validator("collections")
    @classmethod
    def normalize_collections(cls, values: list[str]) -> list[str]:
        normalized = sorted(set(values))
        if any(not value or "/" in value or value in {".", ".."} for value in normalized):
            raise ValueError("collection IDs must be nonempty path segments")
        return normalized


class Producer(StrictModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)


class ArchiveIdentity(StrictModel):
    schema_uri: Literal["mendo-archive/v1"] = Field(
        default="mendo-archive/v1",
        alias="schema",
        serialization_alias="schema",
    )
    archive_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    birthplace: str = Field(min_length=1)
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_created_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value


class ObjectStoredEvent(StrictModel):
    schema_uri: Literal["mendo-corpus-event/v1"] = Field(
        default="mendo-corpus-event/v1",
        alias="schema",
        serialization_alias="schema",
    )
    event_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    event_type: Literal["object_stored"] = "object_stored"
    occurred_at: datetime
    record_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    record_title: str = Field(min_length=1)
    collections: list[str] = Field(min_length=1)
    object: StoredObject
    source: SourceProvenance
    producer: Producer

    @field_validator("occurred_at")
    @classmethod
    def require_occurred_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value

    @field_validator("collections")
    @classmethod
    def normalize_collections(cls, values: list[str]) -> list[str]:
        return IngestMetadata.normalize_collections(values)


class CaptureSnapshotEntry(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)
    mode: int = Field(ge=0, le=0o777)
    modified_at: datetime

    @field_validator("path")
    @classmethod
    def require_safe_snapshot_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or path.is_absolute()
            or ".." in path.parts
            or "." in path.parts
            or path.as_posix() != value
        ):
            raise ValueError("snapshot paths must be normalized relative paths")
        return value

    @field_validator("modified_at")
    @classmethod
    def require_modified_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("modified_at must include a timezone")
        return value


class CaptureSnapshot(StrictModel):
    schema_uri: Literal["mendo-capture-snapshot/v1"] = Field(
        default="mendo-capture-snapshot/v1",
        alias="schema",
        serialization_alias="schema",
    )
    snapshot_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    created_at: datetime
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_label: str = Field(min_length=1)
    includes: list[str] = Field(min_length=1)
    entries: list[CaptureSnapshotEntry]

    @field_validator("created_at")
    @classmethod
    def require_snapshot_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value

    @field_validator("includes")
    @classmethod
    def require_safe_includes(cls, values: list[str]) -> list[str]:
        normalized = sorted(set(values))
        for value in normalized:
            CaptureSnapshotEntry.require_safe_snapshot_path(value)
        return normalized

    @model_validator(mode="after")
    def require_unique_snapshot_paths(self) -> "CaptureSnapshot":
        paths = [entry.path for entry in self.entries]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ValueError("snapshot entries must have unique sorted paths")
        return self


class ReleaseEntry(StrictModel):
    source_path: str
    destination_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)

    @field_validator("source_path", "destination_path")
    @classmethod
    def require_safe_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or path.is_absolute()
            or ".." in path.parts
            or "." in path.parts
        ):
            raise ValueError("release paths must be normalized relative paths")
        return path.as_posix()


class CorpusRelease(StrictModel):
    schema_uri: Literal["mendo-corpus-release/v1"] = Field(
        default="mendo-corpus-release/v1",
        alias="schema",
        serialization_alias="schema",
    )
    release_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    archive_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    created_at: datetime
    event_count: int = Field(ge=0)
    record_count: int = Field(ge=0)
    object_count: int = Field(ge=0)
    entries: list[ReleaseEntry]

    @field_validator("created_at")
    @classmethod
    def require_created_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value

    @model_validator(mode="after")
    def require_unique_destinations(self) -> "CorpusRelease":
        destinations = [entry.destination_path for entry in self.entries]
        if len(destinations) != len(set(destinations)):
            raise ValueError("release destination paths must be unique")
        if "release.json" in destinations:
            raise ValueError("release.json is reserved for the release manifest")
        return self


class ReleaseChannel(StrictModel):
    schema_uri: Literal["mendo-release-channel/v1"] = Field(
        default="mendo-release-channel/v1",
        alias="schema",
        serialization_alias="schema",
    )
    channel: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    release_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def require_updated_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("updated_at must include a timezone")
        return value


class StagingReleaseReceipt(StrictModel):
    schema_uri: Literal["mendo-staging-release-receipt/v1"] = Field(
        default="mendo-staging-release-receipt/v1",
        alias="schema",
        serialization_alias="schema",
    )
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_lock_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    python_version: str = Field(pattern=r"^3\.[0-9]+\.[0-9]+$")
    archive_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    release_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    channel: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verified_at: datetime
    verified_file_count: int = Field(ge=1)
    verified_bytes: int = Field(ge=0)
    materialized_path: str = Field(min_length=1)

    @field_validator("verified_at")
    @classmethod
    def require_verified_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("verified_at must include a timezone")
        return value

    @field_validator("materialized_path")
    @classmethod
    def require_absolute_materialized_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.is_absolute() or path.as_posix() != value:
            raise ValueError("materialized_path must be a normalized absolute path")
        return value


class SignedStagingReleaseReceipt(StrictModel):
    schema_uri: Literal["mendo-signed-staging-release-receipt/v1"] = Field(
        default="mendo-signed-staging-release-receipt/v1",
        alias="schema",
        serialization_alias="schema",
    )
    signature_algorithm: Literal["ed25519"] = "ed25519"
    key_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    receipt: StagingReleaseReceipt
    signature: str = Field(pattern=r"^[A-Za-z0-9+/]{86}==$")


class ProductionPromotionCandidate(StrictModel):
    schema_uri: Literal["mendo-production-promotion-candidate/v1"] = Field(
        default="mendo-production-promotion-candidate/v1",
        alias="schema",
        serialization_alias="schema",
    )
    disposition: Literal["production_candidate"] = "production_candidate"
    receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    receipt: SignedStagingReleaseReceipt
    image: str = Field(
        pattern=r"^ghcr\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$"
    )
    image_index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    image_platforms: list[Literal["linux/amd64", "linux/arm64"]]
    promoted_at: datetime
    promoted_by: str = Field(min_length=1)
    source_repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_ref: str = Field(pattern=r"^refs/heads/[A-Za-z0-9._/-]+$")
    workflow_run_id: str = Field(pattern=r"^[0-9]+$")

    @field_validator("image_platforms")
    @classmethod
    def require_both_platforms(
        cls,
        values: list[Literal["linux/amd64", "linux/arm64"]],
    ) -> list[Literal["linux/amd64", "linux/arm64"]]:
        normalized = sorted(set(values))
        if normalized != ["linux/amd64", "linux/arm64"]:
            raise ValueError("promotion requires linux/amd64 and linux/arm64")
        return normalized

    @field_validator("image")
    @classmethod
    def require_normalized_image_path(cls, value: str) -> str:
        reference = value.removeprefix("ghcr.io/").split("@", 1)[0]
        path = PurePosixPath(reference)
        if path.as_posix() != reference or any(
            part in {".", ".."} for part in path.parts
        ):
            raise ValueError("image repository path must be normalized")
        return value

    @field_validator("promoted_at")
    @classmethod
    def require_promoted_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("promoted_at must include a timezone")
        return value


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

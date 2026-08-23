"""Versioned contracts stored in the implementation-neutral Archive."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

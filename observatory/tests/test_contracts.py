from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from mendo_observatory.contracts import IngestMetadata


def test_ingest_metadata_normalizes_collection_membership() -> None:
    metadata = IngestMetadata(
        record_id="ordinance-3857",
        record_title="Ordinance 3857",
        collections=["ordinances", "case-1", "ordinances"],
        retrieved_at=datetime.fromisoformat("1993-11-09T12:00:00+00:00"),
    )

    assert metadata.collections == ["case-1", "ordinances"]


@pytest.mark.parametrize("collection", ["", ".", "..", "cases/one"])
def test_ingest_metadata_rejects_unsafe_collection_ids(collection: str) -> None:
    with pytest.raises(ValidationError, match="collection IDs"):
        IngestMetadata(
            record_id="record",
            record_title="Record",
            collections=[collection],
            retrieved_at=datetime.fromisoformat("2026-08-22T12:00:00+00:00"),
        )


def test_ingest_metadata_rejects_naive_retrieval_time() -> None:
    with pytest.raises(ValidationError, match="must include a timezone"):
        IngestMetadata(
            record_id="record",
            record_title="Record",
            collections=["case-1"],
            retrieved_at=datetime(2026, 8, 22, 12, 0),
        )


def test_ingest_metadata_rejects_path_like_record_id() -> None:
    with pytest.raises(ValidationError, match="record_id"):
        IngestMetadata(
            record_id="../record",
            record_title="Record",
            collections=["case-1"],
            retrieved_at=datetime.fromisoformat("2026-08-22T12:00:00+00:00"),
        )

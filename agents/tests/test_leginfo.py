from __future__ import annotations

import pytest

from mendo_agents.leginfo import (
    LeginfoIdentityError,
    LeginfoRecord,
    validate_leginfo_identity,
)


def test_leginfo_record_constructs_only_official_structured_url() -> None:
    record = LeginfoRecord(
        target_id="wat-35420-35429",
        title="Water Code Article 2",
        law_code="WAT",
        query=(
            ("division", "13."),
            ("title", ""),
            ("part", "5."),
            ("chapter", "2."),
            ("article", "2."),
        ),
        expected_markers=("35425.",),
    )

    assert record.url == (
        "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?"
        "lawCode=WAT&division=13.&title=&part=5.&chapter=2.&article=2."
    )


def test_leginfo_identity_requires_all_expected_markers() -> None:
    record = LeginfoRecord(
        target_id="wat-35420-35429",
        title="Water Code Article 2",
        law_code="WAT",
        query=(("article", "2."),),
        expected_markers=("ARTICLE 2. Water Distribution", "35425.", "35428."),
    )
    content = (
        b"<html><body><h1>ARTICLE 2. Water Distribution</h1>"
        b"<p>35425. Surplus water</p></body></html>"
    )

    with pytest.raises(LeginfoIdentityError, match="35428"):
        validate_leginfo_identity(content, record)


def test_leginfo_identity_ignores_script_markers() -> None:
    record = LeginfoRecord(
        target_id="wat-35420-35429",
        title="Water Code Article 2",
        law_code="WAT",
        query=(("article", "2."),),
        expected_markers=("35425.",),
    )

    with pytest.raises(LeginfoIdentityError, match="35425"):
        validate_leginfo_identity(
            b"<html><script>35425.</script><body>No statute</body></html>",
            record,
        )

from __future__ import annotations

from pathlib import Path

from mendo_agents.acquisition import PublicRecordFetcher
from mendo_agents.models import AcquisitionCandidate


def test_fetcher_rejects_non_https_and_unlisted_hosts(tmp_path: Path) -> None:
    fetcher = PublicRecordFetcher({"records.example.gov"})

    insecure = fetcher.fetch(
        AcquisitionCandidate(
            target_id="insecure",
            url="http://records.example.gov/file.pdf",
            issuing_body="Example",
            expected_title="Example",
        ),
        tmp_path,
    )
    unlisted = fetcher.fetch(
        AcquisitionCandidate(
            target_id="unlisted",
            url="https://untrusted.example/file.pdf",
            issuing_body="Example",
            expected_title="Example",
        ),
        tmp_path,
    )

    assert insecure.status == "rejected_policy"
    assert unlisted.status == "rejected_policy"
    assert not list(tmp_path.glob("*.pdf"))
    assert len(list(tmp_path.glob("*.fetch.json"))) == 2


def test_same_url_basename_uses_immutable_candidate_paths(
    tmp_path: Path, monkeypatch
) -> None:
    class Downloader:
        def __init__(self):
            self.count = 0

        def __call__(self, url):
            self.count += 1
            return 200, url, f"document-{self.count}".encode()

    fetcher = PublicRecordFetcher({"records.example.gov"})
    monkeypatch.setattr(fetcher, "_check_url", lambda url: None)
    monkeypatch.setattr(fetcher, "_download", Downloader())
    first = fetcher.fetch(
        AcquisitionCandidate(
            target_id="first",
            url="https://records.example.gov/a/doc.pdf",
            issuing_body="Example",
            expected_title="First",
        ),
        tmp_path,
    )
    second = fetcher.fetch(
        AcquisitionCandidate(
            target_id="second",
            url="https://records.example.gov/b/doc.pdf",
            issuing_body="Example",
            expected_title="Second",
        ),
        tmp_path,
    )

    assert first.staging_path != second.staging_path
    assert Path(first.staging_path).read_bytes() == b"document-1"
    assert Path(second.staging_path).read_bytes() == b"document-2"

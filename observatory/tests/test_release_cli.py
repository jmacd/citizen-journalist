from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from mendo_observatory import release_cli
from mendo_observatory.release import MaterializationResult, ReleaseResult
from mendo_observatory.remote import PushResult


class FakeBuilder:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.create_arguments: dict[str, object] | None = None
        self.materialize_arguments: dict[str, object] | None = None

    def create(
        self,
        *,
        channel: str | None,
        reuse_unchanged: bool,
    ) -> ReleaseResult:
        self.create_arguments = {
            "channel": channel,
            "reuse_unchanged": reuse_unchanged,
        }
        return SimpleNamespace(
            release=SimpleNamespace(
                release_id="release",
                event_count=1,
                record_count=1,
                object_count=1,
            ),
            manifest_path=Path("/release/manifest.json"),
            manifest_sha256="a" * 64,
            channel_path=Path("/channels/staging.json"),
            reused=True,
        )

    def materialize(
        self,
        destination: Path,
        *,
        release_id: str | None,
        channel: str | None,
    ) -> MaterializationResult:
        self.materialize_arguments = {
            "release_id": release_id,
            "channel": channel,
        }
        return MaterializationResult(
            archive_id="archive",
            release_id="release",
            manifest_sha256="a" * 64,
            destination=destination,
            file_count=1,
            materialized_bytes=10,
        )


class FakeRemoteStore:
    instance: "FakeRemoteStore | None" = None

    def __init__(self) -> None:
        self.push_arguments: dict[str, object] | None = None
        self.materialize_arguments: dict[str, object] | None = None

    @classmethod
    def from_boto3(cls, **_: object) -> "FakeRemoteStore":
        cls.instance = cls()
        return cls.instance

    def push(
        self,
        builder: FakeBuilder,
        *,
        release_id: str | None,
        channel: str | None,
        verify_reused: bool,
    ) -> PushResult:
        self.push_arguments = {
            "builder": builder,
            "release_id": release_id,
            "channel": channel,
            "verify_reused": verify_reused,
        }
        return PushResult(
            archive_id="archive",
            release_id="release",
            uploaded_count=1,
            reused_count=0,
            verified_reused_count=0,
            channel_key="channel",
        )

    def materialize(
        self,
        destination: Path,
        *,
        archive_id: str,
        release_id: str | None,
        channel: str | None,
        expected_manifest_sha256: str | None,
    ) -> MaterializationResult:
        self.materialize_arguments = {
            "archive_id": archive_id,
            "release_id": release_id,
            "channel": channel,
            "expected_manifest_sha256": expected_manifest_sha256,
        }
        return MaterializationResult(
            archive_id=archive_id,
            release_id="release",
            manifest_sha256="a" * 64,
            destination=destination,
            file_count=1,
            materialized_bytes=10,
        )


def test_push_s3_routes_verify_reused(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(release_cli, "ReleaseBuilder", FakeBuilder)
    monkeypatch.setattr(release_cli, "S3ReleaseStore", FakeRemoteStore)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "mendo-release",
            "push-s3",
            "--root",
            str(tmp_path),
            "--bucket",
            "bucket",
            "--channel",
            "staging",
            "--verify-reused",
        ],
    )

    release_cli.main()

    assert FakeRemoteStore.instance is not None
    assert FakeRemoteStore.instance.push_arguments is not None
    assert FakeRemoteStore.instance.push_arguments["verify_reused"] is True


def test_create_routes_reuse_unchanged(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    builders: list[FakeBuilder] = []

    def make_builder(root: Path) -> FakeBuilder:
        builder = FakeBuilder(root)
        builders.append(builder)
        return builder

    monkeypatch.setattr(release_cli, "ReleaseBuilder", make_builder)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "mendo-release",
            "create",
            "--root",
            str(tmp_path),
            "--channel",
            "staging",
            "--reuse-unchanged",
        ],
    )

    release_cli.main()

    assert builders[0].create_arguments == {
        "channel": "staging",
        "reuse_unchanged": True,
    }
    assert '"reused": true' in capsys.readouterr().out


def test_materialize_s3_routes_expected_manifest_hash(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_cli, "S3ReleaseStore", FakeRemoteStore)
    expected_hash = "a" * 64
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "mendo-release",
            "materialize-s3",
            "--destination",
            str(tmp_path / "materialized"),
            "--archive-id",
            "00000000-0000-4000-8000-000000000000",
            "--bucket",
            "bucket",
            "--release-id",
            "00000000-0000-4000-8000-000000000001",
            "--expected-manifest-sha256",
            expected_hash,
        ],
    )

    release_cli.main()

    assert FakeRemoteStore.instance is not None
    assert FakeRemoteStore.instance.materialize_arguments is not None
    assert (
        FakeRemoteStore.instance.materialize_arguments[
            "expected_manifest_sha256"
        ]
        == expected_hash
    )


def test_local_materialize_does_not_receive_remote_options(
    monkeypatch, tmp_path: Path
) -> None:
    builders: list[FakeBuilder] = []

    def make_builder(root: Path) -> FakeBuilder:
        builder = FakeBuilder(root)
        builders.append(builder)
        return builder

    monkeypatch.setattr(release_cli, "ReleaseBuilder", make_builder)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "mendo-release",
            "materialize",
            "--root",
            str(tmp_path),
            "--destination",
            str(tmp_path / "materialized"),
            "--channel",
            "staging",
        ],
    )

    release_cli.main()

    assert builders[0].materialize_arguments == {
        "release_id": None,
        "channel": "staging",
    }

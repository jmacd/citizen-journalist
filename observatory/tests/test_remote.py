from __future__ import annotations

import io
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from mendo_observatory import ArchiveStore, ReleaseBuilder, S3ReleaseStore
from mendo_observatory.errors import IntegrityError, InvalidEventError


class FakeS3Client:
    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        self.objects: dict[str, tuple[bytes, dict[str, str]]] = {}
        self.operations: list[tuple[str, str]] = []

    def head_bucket(self, *, Bucket: str) -> dict[str, object]:
        assert Bucket == self.bucket
        return {}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        assert Bucket == self.bucket
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}},
                "HeadObject",
            )
        payload, metadata = self.objects[Key]
        return {"ContentLength": len(payload), "Metadata": metadata.copy()}

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        *,
        ExtraArgs: dict[str, object],
    ) -> None:
        assert bucket == self.bucket
        metadata = dict(ExtraArgs["Metadata"])
        self.objects[key] = (Path(filename).read_bytes(), metadata)
        self.operations.append(("upload", key))

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: dict[str, str],
    ) -> dict[str, object]:
        assert Bucket == self.bucket
        assert ContentType == "application/json"
        self.objects[Key] = (bytes(Body), Metadata.copy())
        self.operations.append(("put", Key))
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        assert Bucket == self.bucket
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}},
                "GetObject",
            )
        return {"Body": io.BytesIO(self.objects[Key][0])}

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        assert bucket == self.bucket
        if key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}},
                "GetObject",
            )
        Path(filename).write_bytes(self.objects[key][0])
        self.operations.append(("download", key))

    def create_bucket(self, **arguments: object) -> dict[str, object]:
        assert arguments["Bucket"] == self.bucket
        self.operations.append(("create_bucket", self.bucket))
        return {}


class FailingS3Client(FakeS3Client):
    def __init__(self, bucket: str, *, fail_after: int) -> None:
        super().__init__(bucket)
        self.fail_after = fail_after

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        *,
        ExtraArgs: dict[str, object],
    ) -> None:
        upload_count = len(
            [operation for operation in self.operations if operation[0] == "upload"]
        )
        if upload_count >= self.fail_after:
            raise RuntimeError("injected upload failure")
        super().upload_file(filename, bucket, key, ExtraArgs=ExtraArgs)


def seed_release(root: Path) -> tuple[ReleaseBuilder, str]:
    root.parent.mkdir(parents=True, exist_ok=True)
    source = root.parent / "record.pdf"
    source.write_bytes(b"remote release fixture")
    archive = ArchiveStore(root)
    archive.initialize(birthplace="test")
    archive.ingest_file(
        source,
        record_id="record-1",
        record_title="Record One",
        collections=["case-1"],
    )
    builder = ReleaseBuilder(root)
    release = builder.create(channel="private")
    return builder, release.release.archive_id


def test_ensures_missing_bucket_and_reuses_existing(tmp_path: Path) -> None:
    class MissingBucketClient(FakeS3Client):
        exists = False

        def head_bucket(self, *, Bucket: str) -> dict[str, object]:
            if not self.exists:
                raise ClientError(
                    {"Error": {"Code": "404", "Message": "Not Found"}},
                    "HeadBucket",
                )
            return super().head_bucket(Bucket=Bucket)

        def create_bucket(self, **arguments: object) -> dict[str, object]:
            self.exists = True
            return super().create_bucket(**arguments)

    client = MissingBucketClient("mendo-releases")
    store = S3ReleaseStore(client, bucket="mendo-releases")

    assert store.ensure_bucket() is True
    assert store.ensure_bucket() is False
    assert client.operations == [("create_bucket", "mendo-releases")]


def test_pushes_release_then_publishes_channel_last(tmp_path: Path) -> None:
    builder, archive_id = seed_release(tmp_path / "archive")
    client = FakeS3Client("mendo-releases")
    store = S3ReleaseStore(client, bucket="mendo-releases", prefix="observatory")

    first = store.push(builder, channel="private")

    assert first.uploaded_count == len(
        builder.load_release(channel="private").entries
    ) + 1
    assert first.reused_count == 0
    assert first.channel_key is not None
    assert client.operations[-1] == ("put", first.channel_key)
    assert first.channel_key.startswith(
        f"observatory/archives/{archive_id}/channels/"
    )
    assert all("observatory/observatory/" not in key for _, key in client.operations)

    second = store.push(builder, channel="private")
    assert second.uploaded_count == 0
    assert second.reused_count == first.uploaded_count
    assert second.verified_reused_count == 0

    verified = store.push(builder, channel="private", verify_reused=True)
    assert verified.uploaded_count == 0
    assert verified.verified_reused_count == first.uploaded_count


def test_materializes_release_from_remote_channel(tmp_path: Path) -> None:
    builder, archive_id = seed_release(tmp_path / "archive")
    client = FakeS3Client("mendo-releases")
    store = S3ReleaseStore(client, bucket="mendo-releases")
    pushed = store.push(builder, channel="private")
    destination = tmp_path / "remote-materialized"

    result = store.materialize(
        destination,
        archive_id=archive_id,
        channel="private",
    )

    assert result.release_id == pushed.release_id
    assert (destination / "release.json").is_file()
    assert (destination / "catalog" / "records.parquet").is_file()
    assert list((destination / "objects" / "sha256").glob("*/*"))


def test_remote_tampering_blocks_materialization(tmp_path: Path) -> None:
    builder, archive_id = seed_release(tmp_path / "archive")
    client = FakeS3Client("mendo-releases")
    store = S3ReleaseStore(client, bucket="mendo-releases")
    store.push(builder, channel="private")
    object_key = next(key for key in client.objects if "/objects/sha256/" in key)
    _, metadata = client.objects[object_key]
    client.objects[object_key] = (b"tampered remote bytes", metadata)
    destination = tmp_path / "remote-materialized"

    with pytest.raises(IntegrityError, match="failed verification"):
        store.materialize(
            destination,
            archive_id=archive_id,
            channel="private",
        )

    assert not destination.exists()


def test_remote_namespaces_distinct_archives(tmp_path: Path) -> None:
    first_builder, first_archive_id = seed_release(tmp_path / "first" / "archive")
    second_builder, second_archive_id = seed_release(tmp_path / "second" / "archive")
    client = FakeS3Client("mendo-releases")
    store = S3ReleaseStore(client, bucket="mendo-releases")

    store.push(first_builder, channel="private")
    store.push(second_builder, channel="private")

    keys = set(client.objects)
    assert any(f"archives/{first_archive_id}/" in key for key in keys)
    assert any(f"archives/{second_archive_id}/" in key for key in keys)


def test_remote_immutable_key_conflict_fails_loudly(tmp_path: Path) -> None:
    builder, _ = seed_release(tmp_path / "archive")
    release = builder.create()
    client = FakeS3Client("mendo-releases")
    store = S3ReleaseStore(client, bucket="mendo-releases")
    store.push(builder, release_id=release.release.release_id)
    object_key = next(key for key in client.objects if "/objects/sha256/" in key)
    client.objects[object_key] = (b"different", {"sha256": "0" * 64})

    with pytest.raises(IntegrityError, match="different data"):
        store.push(builder, release_id=release.release.release_id)


def test_failed_entry_upload_never_publishes_channel(tmp_path: Path) -> None:
    builder, _ = seed_release(tmp_path / "archive")
    client = FailingS3Client("mendo-releases", fail_after=1)
    store = S3ReleaseStore(client, bucket="mendo-releases")

    with pytest.raises(RuntimeError, match="injected upload failure"):
        store.push(builder, channel="private")

    assert not any("/channels/" in key for key in client.objects)


def test_failed_entry_upload_can_be_retried_without_new_release(
    tmp_path: Path,
) -> None:
    builder, _ = seed_release(tmp_path / "archive")
    release_id = builder.load_release(channel="private").release_id
    client = FailingS3Client("mendo-releases", fail_after=1)
    store = S3ReleaseStore(client, bucket="mendo-releases")

    with pytest.raises(RuntimeError, match="injected upload failure"):
        store.push(builder, channel="private")

    first_uploaded_key = client.operations[0][1]
    reused_release = builder.create(channel="private", reuse_unchanged=True)
    assert reused_release.reused is True
    assert reused_release.release.release_id == release_id

    client.fail_after = 100
    result = store.push(builder, channel="private", verify_reused=True)

    assert result.release_id == release_id
    assert result.reused_count == 1
    assert result.verified_reused_count == 1
    assert result.uploaded_count > 0
    assert result.channel_key is not None
    assert ("download", first_uploaded_key) in client.operations
    assert client.operations[-1] == ("put", result.channel_key)


def test_release_id_materialization_requires_manifest_hash(tmp_path: Path) -> None:
    builder, archive_id = seed_release(tmp_path / "archive")
    release = builder.create()
    client = FakeS3Client("mendo-releases")
    store = S3ReleaseStore(client, bucket="mendo-releases")
    pushed = store.push(builder, release_id=release.release.release_id)

    with pytest.raises(InvalidEventError, match="requires"):
        store.materialize(
            tmp_path / "without-anchor",
            archive_id=archive_id,
            release_id=pushed.release_id,
        )

    result = store.materialize(
        tmp_path / "with-anchor",
        archive_id=archive_id,
        release_id=pushed.release_id,
        expected_manifest_sha256=release.manifest_sha256,
    )
    assert result.release_id == pushed.release_id

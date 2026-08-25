"""S3-compatible transport for immutable corpus releases."""

from __future__ import annotations

import os
import tempfile
import uuid
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from botocore.exceptions import ClientError
from pydantic import ValidationError

from .contracts import CorpusRelease, ReleaseChannel
from .errors import IntegrityError, InvalidEventError
from .release import (
    CHANNEL_PATTERN,
    MaterializationResult,
    ReleaseBuilder,
)
from .storage import ensure_directory, hash_file, sync_directory, write_create_only


@dataclass(frozen=True)
class PushResult:
    archive_id: str
    release_id: str
    uploaded_count: int
    reused_count: int
    verified_reused_count: int
    channel_key: str | None


class S3ReleaseStore:
    """Move release artifacts without changing their local semantics."""

    def __init__(
        self,
        client: Any,
        *,
        bucket: str,
        prefix: str = "",
    ) -> None:
        if not bucket:
            raise InvalidEventError("S3 bucket must not be empty")
        normalized_prefix = PurePosixPath(prefix.strip("/"))
        if ".." in normalized_prefix.parts:
            raise InvalidEventError(f"invalid S3 prefix: {prefix!r}")
        self.client = client
        self.bucket = bucket
        self.prefix = "" if str(normalized_prefix) == "." else normalized_prefix.as_posix()

    @classmethod
    def from_boto3(
        cls,
        *,
        bucket: str,
        endpoint_url: str | None = None,
        region_name: str = "us-east-1",
        prefix: str = "",
    ) -> "S3ReleaseStore":
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
        )
        return cls(client, bucket=bucket, prefix=prefix)

    def push(
        self,
        builder: ReleaseBuilder,
        *,
        release_id: str | None = None,
        channel: str | None = None,
        verify_reused: bool = False,
    ) -> PushResult:
        self.client.head_bucket(Bucket=self.bucket)
        release = builder.load_release(release_id=release_id, channel=channel)
        base = self._archive_base(release.archive_id)
        uploaded_count = 0
        reused_count = 0
        verified_reused_count = 0

        for entry in release.entries:
            source = builder.root / entry.source_path
            key = self._entry_key(base, release.release_id, entry.destination_path)
            uploaded = self._ensure_remote_file(
                source,
                key,
                expected_sha256=entry.sha256,
                expected_bytes=entry.bytes,
                verify_existing_body=verify_reused,
            )
            uploaded_count += int(uploaded)
            reused_count += int(not uploaded)
            verified_reused_count += int(not uploaded and verify_reused)

        manifest_path = (
            builder.root / "releases" / release.release_id / "manifest.json"
        )
        manifest_sha256, manifest_bytes = hash_file(manifest_path)
        manifest_key = self._key(
            base,
            "releases",
            release.release_id,
            "manifest.json",
        )
        uploaded = self._ensure_remote_file(
            manifest_path,
            manifest_key,
            expected_sha256=manifest_sha256,
            expected_bytes=manifest_bytes,
            verify_existing_body=verify_reused,
        )
        uploaded_count += int(uploaded)
        reused_count += int(not uploaded)
        verified_reused_count += int(not uploaded and verify_reused)

        channel_key = None
        if channel is not None:
            channel_path = builder.root / "channels" / f"{channel}.json"
            try:
                pointer_payload = channel_path.read_bytes()
                pointer = ReleaseChannel.model_validate_json(pointer_payload)
            except (OSError, ValidationError, ValueError) as error:
                raise InvalidEventError(
                    f"invalid local release channel {channel_path}: {error}"
                ) from error
            if (
                pointer.channel != channel
                or pointer.release_id != release.release_id
                or pointer.manifest_sha256 != manifest_sha256
            ):
                raise IntegrityError(
                    f"local release channel does not identify the pushed manifest: "
                    f"{channel_path}"
                )
            channel_key = self._key(base, "channels", f"{channel}.json")
            channel_sha256 = self._hash_bytes(pointer_payload)
            self.client.put_object(
                Bucket=self.bucket,
                Key=channel_key,
                Body=pointer_payload,
                ContentType="application/json",
                Metadata={"sha256": channel_sha256},
            )
            published = self.client.head_object(Bucket=self.bucket, Key=channel_key)
            if (
                published.get("ContentLength") != len(pointer_payload)
                or (published.get("Metadata") or {}).get("sha256")
                != channel_sha256
            ):
                raise IntegrityError(
                    f"remote channel upload failed verification: "
                    f"s3://{self.bucket}/{channel_key}"
                )

        return PushResult(
            archive_id=release.archive_id,
            release_id=release.release_id,
            uploaded_count=uploaded_count,
            reused_count=reused_count,
            verified_reused_count=verified_reused_count,
            channel_key=channel_key,
        )

    def ensure_bucket(self, *, region_name: str = "us-east-1") -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return False
        except ClientError as error:
            if not self._is_not_found(error):
                raise

        arguments: dict[str, object] = {"Bucket": self.bucket}
        if region_name != "us-east-1":
            arguments["CreateBucketConfiguration"] = {
                "LocationConstraint": region_name
            }
        self.client.create_bucket(**arguments)
        self.client.head_bucket(Bucket=self.bucket)
        return True

    def materialize(
        self,
        destination: Path,
        *,
        archive_id: str,
        release_id: str | None = None,
        channel: str | None = None,
        expected_manifest_sha256: str | None = None,
    ) -> MaterializationResult:
        archive_id = self._validate_uuid(archive_id, "archive ID")
        if (release_id is None) == (channel is None):
            raise InvalidEventError("specify exactly one of release_id or channel")
        self.client.head_bucket(Bucket=self.bucket)
        base = self._archive_base(archive_id)
        if channel is not None:
            if not CHANNEL_PATTERN.fullmatch(channel):
                raise InvalidEventError(f"invalid release channel: {channel!r}")
            channel_key = self._key(base, "channels", f"{channel}.json")
            pointer_payload = self._get_bytes(channel_key)
            try:
                pointer = ReleaseChannel.model_validate_json(pointer_payload)
            except (ValidationError, ValueError) as error:
                raise InvalidEventError(
                    f"invalid remote release channel {channel_key}: {error}"
                ) from error
            if pointer.channel != channel:
                raise InvalidEventError(
                    f"remote channel name mismatch: {pointer.channel!r}"
                )
            release_id = pointer.release_id
            expected_manifest_sha256 = pointer.manifest_sha256
        else:
            release_id = self._validate_uuid(str(release_id), "release ID")
            if (
                expected_manifest_sha256 is None
                or len(expected_manifest_sha256) != 64
                or any(character not in "0123456789abcdef" for character in expected_manifest_sha256)
            ):
                raise InvalidEventError(
                    "release-ID materialization requires a lowercase "
                    "expected_manifest_sha256"
                )

        manifest_key = self._key(base, "releases", str(release_id), "manifest.json")
        manifest_payload = self._get_bytes(manifest_key)
        actual_manifest_sha256 = self._hash_bytes(manifest_payload)
        if (
            expected_manifest_sha256 is not None
            and actual_manifest_sha256 != expected_manifest_sha256
        ):
            raise IntegrityError(
                f"remote release manifest hash mismatch: s3://{self.bucket}/{manifest_key}"
            )
        try:
            release = CorpusRelease.model_validate_json(manifest_payload)
        except (ValidationError, ValueError) as error:
            raise InvalidEventError(
                f"invalid remote release manifest {manifest_key}: {error}"
            ) from error
        if release.archive_id != archive_id or release.release_id != release_id:
            raise IntegrityError(
                f"remote release identity mismatch: s3://{self.bucket}/{manifest_key}"
            )
        object_entries = [
            entry
            for entry in release.entries
            if entry.destination_path.startswith("objects/sha256/")
        ]
        if len(object_entries) != release.object_count:
            raise IntegrityError(
                f"remote release object count mismatch: expected {release.object_count}, "
                f"found {len(object_entries)}"
            )

        destination = destination.absolute()
        if os.path.lexists(destination):
            raise InvalidEventError(
                f"materialization destination already exists: {destination}"
            )
        ensure_directory(destination.parent)
        materialized_bytes = 0
        with tempfile.TemporaryDirectory(
            prefix=f".{destination.name}-", dir=destination.parent
        ) as temporary_name:
            temporary_directory = Path(temporary_name)
            for entry in release.entries:
                key = self._entry_key(base, release.release_id, entry.destination_path)
                target = temporary_directory / entry.destination_path
                ensure_directory(target.parent)
                self.client.download_file(self.bucket, key, str(target))
                actual_sha256, actual_bytes = hash_file(target)
                if actual_sha256 != entry.sha256 or actual_bytes != entry.bytes:
                    raise IntegrityError(
                        f"downloaded release entry failed verification: "
                        f"s3://{self.bucket}/{key}"
                    )
                with target.open("r+b") as copied_file:
                    os.fsync(copied_file.fileno())
                os.chmod(target, 0o440)
                materialized_bytes += actual_bytes

            release_path = temporary_directory / "release.json"
            write_create_only(release_path, manifest_payload, file_mode=0o440)
            for directory in sorted(
                (path for path in temporary_directory.rglob("*") if path.is_dir()),
                reverse=True,
            ):
                sync_directory(directory)
            sync_directory(temporary_directory)
            if os.path.lexists(destination):
                raise InvalidEventError(
                    f"materialization destination appeared during download: {destination}"
                )
            os.replace(temporary_directory, destination)
            sync_directory(destination.parent)

        return MaterializationResult(
            archive_id=release.archive_id,
            release_id=release.release_id,
            manifest_sha256=actual_manifest_sha256,
            destination=destination,
            file_count=len(release.entries),
            materialized_bytes=materialized_bytes,
        )

    def _ensure_remote_file(
        self,
        source: Path,
        key: str,
        *,
        expected_sha256: str,
        expected_bytes: int,
        verify_existing_body: bool,
    ) -> bool:
        actual_sha256, actual_bytes = hash_file(source)
        if actual_sha256 != expected_sha256 or actual_bytes != expected_bytes:
            raise IntegrityError(f"local release file failed verification: {source}")
        try:
            existing = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if not self._is_not_found(error):
                raise
        else:
            metadata = existing.get("Metadata") or {}
            if (
                existing.get("ContentLength") != expected_bytes
                or metadata.get("sha256") != expected_sha256
            ):
                raise IntegrityError(
                    f"remote immutable key contains different data: "
                    f"s3://{self.bucket}/{key}"
                )
            if verify_existing_body:
                with tempfile.TemporaryDirectory(prefix="mendo-s3-verify-") as directory:
                    downloaded = Path(directory) / "object"
                    self.client.download_file(self.bucket, key, str(downloaded))
                    remote_sha256, remote_bytes = hash_file(downloaded)
                    if (
                        remote_sha256 != expected_sha256
                        or remote_bytes != expected_bytes
                    ):
                        raise IntegrityError(
                            f"remote immutable key failed full verification: "
                            f"s3://{self.bucket}/{key}"
                        )
            return False

        self.client.upload_file(
            str(source),
            self.bucket,
            key,
            ExtraArgs={
                "Metadata": {"sha256": expected_sha256},
                "ContentType": "application/octet-stream",
            },
        )
        uploaded = self.client.head_object(Bucket=self.bucket, Key=key)
        metadata = uploaded.get("Metadata") or {}
        if (
            uploaded.get("ContentLength") != expected_bytes
            or metadata.get("sha256") != expected_sha256
        ):
            raise IntegrityError(
                f"remote upload failed verification: s3://{self.bucket}/{key}"
            )
        return True

    def _get_bytes(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if self._is_not_found(error):
                raise IntegrityError(
                    f"remote release file is missing: s3://{self.bucket}/{key}"
                ) from error
            raise
        body = response["Body"]
        with closing(body):
            return body.read()

    def _archive_base(self, archive_id: str) -> str:
        return f"archives/{self._validate_uuid(archive_id, 'archive ID')}"

    def _entry_key(self, base: str, release_id: str, destination_path: str) -> str:
        if destination_path.startswith("objects/sha256/"):
            return self._key(base, destination_path)
        return self._key(
            base,
            "releases",
            release_id,
            "files",
            destination_path,
        )

    def _key(self, *parts: str) -> str:
        clean = [part.strip("/") for part in parts if part.strip("/")]
        if self.prefix:
            clean.insert(0, self.prefix)
        return "/".join(clean)

    @staticmethod
    def _validate_uuid(value: str, label: str) -> str:
        try:
            parsed = uuid.UUID(value)
        except ValueError as error:
            raise InvalidEventError(f"invalid {label}: {value!r}") from error
        if str(parsed) != value:
            raise InvalidEventError(f"{label} is not canonical: {value!r}")
        return value

    @staticmethod
    def _is_not_found(error: ClientError) -> bool:
        code = str(error.response.get("Error", {}).get("Code", ""))
        return code in {"404", "NoSuchKey", "NotFound"}

    @staticmethod
    def _hash_bytes(payload: bytes) -> str:
        import hashlib

        return hashlib.sha256(payload).hexdigest()

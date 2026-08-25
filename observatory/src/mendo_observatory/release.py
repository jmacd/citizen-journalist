"""Immutable corpus release creation and clean-directory materialization."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq
from pydantic import ValidationError

from .contracts import (
    CorpusRelease,
    ReleaseChannel,
    ReleaseEntry,
    StrictModel,
    utc_now,
)
from .corpus import CorpusBuilder
from .errors import IntegrityError, InvalidEventError
from .storage import (
    atomic_replace,
    ensure_directory,
    hash_file,
    install_create_only,
    sync_directory,
    write_create_only,
)

CHANNEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class ReleaseResult:
    release: CorpusRelease
    manifest_path: Path
    manifest_sha256: str
    channel_path: Path | None
    reused: bool = False


@dataclass(frozen=True)
class MaterializationResult:
    archive_id: str
    release_id: str
    manifest_sha256: str
    destination: Path
    file_count: int
    materialized_bytes: int


def serialize_model(
    model: StrictModel,
) -> bytes:
    return (
        json.dumps(
            model.model_dump(mode="json", by_alias=True),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


class ReleaseBuilder:
    def __init__(self, archive_root: Path, *, file_mode: int = 0o640) -> None:
        self.root = archive_root.resolve()
        self.file_mode = file_mode
        self.corpus = CorpusBuilder(self.root)

    def create(
        self,
        *,
        channel: str | None = None,
        reuse_unchanged: bool = False,
    ) -> ReleaseResult:
        if channel is not None:
            self._validate_channel(channel)
        elif reuse_unchanged:
            raise InvalidEventError(
                "reuse_unchanged requires a channel to identify the prior release"
            )
        identity = self.corpus.load_identity()
        build = self.corpus.build_catalogs()
        if reuse_unchanged and channel is not None:
            existing = self._reuse_if_unchanged(
                channel=channel,
                archive_id=identity.archive_id,
                event_count=build.event_count,
                record_count=build.record_count,
                object_count=build.object_count,
                entries=self._current_entries(build.catalog_paths),
            )
            if existing is not None:
                return existing

        release_id = str(uuid.uuid4())
        releases_directory = self.root / "releases"
        ensure_directory(releases_directory)
        release_directory = releases_directory / release_id
        release_directory.mkdir(mode=0o750, exist_ok=False)
        sync_directory(releases_directory)

        entries: list[ReleaseEntry] = []
        entries.append(self._entry(self.root / "archive.json", "archive.json"))
        for name, catalog_path in sorted(build.catalog_paths.items()):
            frozen_path = release_directory / "catalog" / f"{name}.parquet"
            self._copy_create_only(catalog_path, frozen_path)
            entries.append(
                self._entry(
                    frozen_path,
                    f"catalog/{name}.parquet",
                )
            )

        frozen_objects_catalog = release_directory / "catalog" / "objects.parquet"
        object_rows = pq.read_table(frozen_objects_catalog).to_pylist()
        for row in sorted(object_rows, key=lambda value: value["sha256"]):
            source_path = self.root / row["archive_path"]
            entry = self._entry(source_path, row["archive_path"])
            if entry.sha256 != row["sha256"] or entry.bytes != row["bytes"]:
                raise IntegrityError(
                    f"object changed after catalog verification: {source_path}"
                )
            entries.append(entry)

        release = CorpusRelease(
            release_id=release_id,
            archive_id=identity.archive_id,
            created_at=utc_now(),
            event_count=build.event_count,
            record_count=build.record_count,
            object_count=build.object_count,
            entries=sorted(entries, key=lambda entry: entry.destination_path),
        )
        manifest_path = release_directory / "manifest.json"
        manifest_payload = serialize_model(release)
        write_create_only(
            manifest_path,
            manifest_payload,
            file_mode=0o440,
        )
        manifest_sha256, _ = hash_file(manifest_path)

        channel_path = None
        if channel is not None:
            pointer = ReleaseChannel(
                channel=channel,
                release_id=release_id,
                manifest_sha256=manifest_sha256,
                updated_at=utc_now(),
            )
            channel_path = self.root / "channels" / f"{channel}.json"
            atomic_replace(
                channel_path,
                serialize_model(pointer),
                file_mode=self.file_mode,
            )

        return ReleaseResult(
            release=release,
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
            channel_path=channel_path,
        )

    def _current_entries(
        self,
        catalog_paths: dict[str, Path],
    ) -> list[ReleaseEntry]:
        entries = [self._entry(self.root / "archive.json", "archive.json")]
        for name, catalog_path in sorted(catalog_paths.items()):
            entries.append(self._entry(catalog_path, f"catalog/{name}.parquet"))

        object_rows = pq.read_table(catalog_paths["objects"]).to_pylist()
        for row in sorted(object_rows, key=lambda value: value["sha256"]):
            source_path = self.root / row["archive_path"]
            entry = self._entry(source_path, row["archive_path"])
            if entry.sha256 != row["sha256"] or entry.bytes != row["bytes"]:
                raise IntegrityError(
                    f"object changed after catalog verification: {source_path}"
                )
            entries.append(entry)
        return entries

    def _reuse_if_unchanged(
        self,
        *,
        channel: str,
        archive_id: str,
        event_count: int,
        record_count: int,
        object_count: int,
        entries: list[ReleaseEntry],
    ) -> ReleaseResult | None:
        channel_path = self.root / "channels" / f"{channel}.json"
        if not os.path.lexists(channel_path):
            return None

        release = self.load_release(channel=channel)
        expected = [
            (entry.destination_path, entry.sha256, entry.bytes)
            for entry in sorted(entries, key=lambda value: value.destination_path)
        ]
        existing = [
            (entry.destination_path, entry.sha256, entry.bytes)
            for entry in sorted(
                release.entries,
                key=lambda value: value.destination_path,
            )
        ]
        if (
            release.archive_id != archive_id
            or release.event_count != event_count
            or release.record_count != record_count
            or release.object_count != object_count
            or existing != expected
        ):
            return None

        for entry in release.entries:
            source = self.root / entry.source_path
            actual_sha256, actual_bytes = hash_file(source)
            if actual_sha256 != entry.sha256 or actual_bytes != entry.bytes:
                raise IntegrityError(
                    f"existing release source failed verification: {source}"
                )

        manifest_path = self.root / "releases" / release.release_id / "manifest.json"
        manifest_sha256, _ = hash_file(manifest_path)
        return ReleaseResult(
            release=release,
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
            channel_path=channel_path,
            reused=True,
        )

    def load_release(
        self,
        *,
        release_id: str | None = None,
        channel: str | None = None,
    ) -> CorpusRelease:
        if (release_id is None) == (channel is None):
            raise InvalidEventError("specify exactly one of release_id or channel")
        expected_manifest_sha256 = None
        if channel is not None:
            self._validate_channel(channel)
            channel_path = self.root / "channels" / f"{channel}.json"
            try:
                pointer = ReleaseChannel.model_validate_json(channel_path.read_bytes())
            except (OSError, ValidationError, ValueError) as error:
                raise InvalidEventError(
                    f"invalid release channel {channel_path}: {error}"
                ) from error
            if pointer.channel != channel:
                raise InvalidEventError(
                    f"release channel name mismatch: expected {channel}, "
                    f"found {pointer.channel}"
                )
            release_id = pointer.release_id
            expected_manifest_sha256 = pointer.manifest_sha256
        else:
            release_id = self._validate_release_id(str(release_id))

        manifest_path = self.root / "releases" / str(release_id) / "manifest.json"
        try:
            payload = manifest_path.read_bytes()
            release = CorpusRelease.model_validate_json(payload)
        except (OSError, ValidationError, ValueError) as error:
            raise InvalidEventError(f"invalid release manifest {manifest_path}: {error}") from error
        if release.release_id != release_id:
            raise InvalidEventError(
                f"release ID mismatch: expected {release_id}, found {release.release_id}"
            )
        actual_manifest_sha256, _ = hash_file(manifest_path)
        if (
            expected_manifest_sha256 is not None
            and actual_manifest_sha256 != expected_manifest_sha256
        ):
            raise IntegrityError(
                f"release channel manifest hash mismatch: {manifest_path}"
            )
        return release

    def materialize(
        self,
        destination: Path,
        *,
        release_id: str | None = None,
        channel: str | None = None,
    ) -> MaterializationResult:
        release = self.load_release(release_id=release_id, channel=channel)
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
                source = self.root / entry.source_path
                actual_sha256, actual_bytes = hash_file(source)
                if actual_sha256 != entry.sha256 or actual_bytes != entry.bytes:
                    raise IntegrityError(f"release source failed verification: {source}")
                target = temporary_directory / entry.destination_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                with target.open("r+b") as copied_file:
                    os.fsync(copied_file.fileno())
                os.chmod(target, 0o440)
                copied_sha256, copied_bytes = hash_file(target)
                if copied_sha256 != entry.sha256 or copied_bytes != entry.bytes:
                    raise IntegrityError(f"materialized file failed verification: {target}")
                materialized_bytes += copied_bytes

            release_path = temporary_directory / "release.json"
            write_create_only(release_path, serialize_model(release), file_mode=0o440)
            os.chmod(release_path, 0o440)
            for directory in sorted(
                (path for path in temporary_directory.rglob("*") if path.is_dir()),
                reverse=True,
            ):
                sync_directory(directory)
            sync_directory(temporary_directory)
            if os.path.lexists(destination):
                raise InvalidEventError(
                    f"materialization destination appeared during build: {destination}"
                )
            os.replace(temporary_directory, destination)
            sync_directory(destination.parent)

        return MaterializationResult(
            archive_id=release.archive_id,
            release_id=release.release_id,
            manifest_sha256=hash_file(
                self.root / "releases" / release.release_id / "manifest.json"
            )[0],
            destination=destination,
            file_count=len(release.entries),
            materialized_bytes=materialized_bytes,
        )

    def _entry(self, source_path: Path, destination_path: str) -> ReleaseEntry:
        digest, byte_count = hash_file(source_path)
        return ReleaseEntry(
            source_path=source_path.relative_to(self.root).as_posix(),
            destination_path=destination_path,
            sha256=digest,
            bytes=byte_count,
        )

    def _copy_create_only(self, source: Path, destination: Path) -> None:
        ensure_directory(destination.parent)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}-", dir=destination.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with source.open("rb") as input_file, os.fdopen(descriptor, "wb") as output_file:
                os.fchmod(output_file.fileno(), 0o440)
                shutil.copyfileobj(input_file, output_file)
                output_file.flush()
                os.fsync(output_file.fileno())
            if not install_create_only(temporary_path, destination):
                expected = hash_file(temporary_path)
                try:
                    actual = hash_file(destination)
                except OSError as error:
                    raise IntegrityError(
                        f"frozen release file exists but cannot be verified: {destination}"
                    ) from error
                if actual != expected:
                    raise IntegrityError(
                        f"frozen release file contains different data: {destination}"
                    )
        finally:
            temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _validate_channel(channel: str) -> str:
        if not CHANNEL_PATTERN.fullmatch(channel):
            raise InvalidEventError(f"invalid release channel: {channel!r}")
        return channel

    @staticmethod
    def _validate_release_id(release_id: str) -> str:
        try:
            parsed = uuid.UUID(release_id)
        except ValueError as error:
            raise InvalidEventError(f"invalid release ID: {release_id!r}") from error
        canonical = str(parsed)
        if canonical != release_id:
            raise InvalidEventError(f"release ID is not canonical: {release_id!r}")
        return canonical

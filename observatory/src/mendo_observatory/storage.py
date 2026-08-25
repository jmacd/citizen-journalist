"""Durable local filesystem operations shared by Archive and Corpus."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from .errors import ArchiveWriteError

BUFFER_SIZE = 1024 * 1024


def ensure_directory(directory: Path, *, mode: int = 0o750) -> None:
    missing: list[Path] = []
    current = directory
    while not current.exists():
        missing.append(current)
        current = current.parent
    if not current.is_dir():
        raise ArchiveWriteError(f"directory parent is not a directory: {current}")
    for path in reversed(missing):
        try:
            path.mkdir(mode=mode)
        except FileExistsError:
            if not path.is_dir():
                raise ArchiveWriteError(f"directory path is not a directory: {path}")
        sync_directory(path.parent)


def sync_directory(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def install_create_only(temporary_path: Path, final_path: Path) -> bool:
    try:
        os.link(temporary_path, final_path)
    except FileExistsError:
        return False
    except OSError as error:
        raise ArchiveWriteError(f"cannot install file {final_path}: {error}") from error
    sync_directory(final_path.parent)
    return True


def write_create_only(path: Path, payload: bytes, *, file_mode: int = 0o640) -> None:
    ensure_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as destination:
            os.fchmod(destination.fileno(), file_mode)
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        if not install_create_only(temporary_path, path):
            try:
                existing_payload = path.read_bytes()
            except OSError as error:
                raise ArchiveWriteError(
                    f"file exists but cannot be verified: {path}: {error}"
                ) from error
            if existing_payload != payload:
                raise ArchiveWriteError(f"create-only file contains different data: {path}")
    finally:
        temporary_path.unlink(missing_ok=True)


def atomic_replace(path: Path, payload: bytes, *, file_mode: int = 0o640) -> None:
    ensure_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as destination:
            os.fchmod(destination.fileno(), file_mode)
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary_path, path)
        sync_directory(path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    byte_count = 0
    with path.open("rb") as source:
        while chunk := source.read(BUFFER_SIZE):
            digest.update(chunk)
            byte_count += len(chunk)
    return digest.hexdigest(), byte_count

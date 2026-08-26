#!/usr/bin/env python3
"""Package accepted local evidence with consistent SQLite snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

INCLUDES = (
    Path("captures"),
    Path("cases/UM_2025-0004"),
    Path("web/casebook-data.js"),
)
TRACKED_INPUTS = (
    "cases/UM_2025-0004",
    "web/casebook-data.js",
)
SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}


def run_git(source_dir: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_dir), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def backup_sqlite(source: Path, destination: Path) -> None:
    source_uri = f"file:{source.as_posix()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as input_database:
        with sqlite3.connect(destination) as output_database:
            input_database.backup(output_database)
            result = output_database.execute(
                "PRAGMA integrity_check"
            ).fetchone()
            if result is None or result[0] != "ok":
                raise ValueError(
                    f"SQLite backup failed integrity check: {source}"
                )


def source_files(source_dir: Path) -> list[tuple[Path, Path]]:
    files: dict[str, tuple[Path, Path]] = {}
    for include in INCLUDES:
        source = (source_dir / include).resolve(strict=True)
        source.relative_to(source_dir)
        paths = [source] if source.is_file() else sorted(
            path for path in source.rglob("*") if path.is_file()
        )
        for path in paths:
            if path.is_symlink():
                raise ValueError(f"snapshot input contains a symlink: {path}")
            relative = path.relative_to(source_dir)
            files[relative.as_posix()] = (relative, path)
    return [files[key] for key in sorted(files)]


def main() -> None:
    query = json.load(sys.stdin)
    source_dir = Path(query["source_dir"]).resolve()
    output_path = Path(query["output_path"]).resolve()
    revision = query["revision"]
    if run_git(source_dir, "rev-parse", "--show-toplevel") != str(source_dir):
        raise ValueError(f"source_dir is not the repository root: {source_dir}")
    if run_git(source_dir, "rev-parse", "HEAD") != revision:
        raise ValueError(
            "accepted workspace source does not match observatory_revision"
        )
    dirty = run_git(
        source_dir, "status", "--porcelain", "--", *TRACKED_INPUTS
    )
    if dirty:
        raise ValueError(
            "accepted tracked inputs contain uncommitted changes:\n" + dirty
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_tar = output_path.with_suffix(".tmp")
    try:
        with tempfile.TemporaryDirectory(
            prefix="accepted-workspace-"
        ) as temporary:
            staging = Path(temporary)
            files = source_files(source_dir)
            for relative, source in files:
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if source.suffix.lower() in SQLITE_SUFFIXES:
                    backup_sqlite(source, destination)
                    shutil.copystat(source, destination)
                else:
                    shutil.copy2(source, destination)

            checksums = []
            staged_files = sorted(
                path
                for path in staging.rglob("*")
                if path.is_file()
            )
            for path in staged_files:
                relative = path.relative_to(staging).as_posix()
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                checksums.append(f"{digest}  {relative}\n")
            (staging / "SHA256SUMS").write_text(
                "".join(checksums), encoding="utf-8"
            )

            with tarfile.open(temporary_tar, "w") as archive:
                for path in sorted(staging.rglob("*")):
                    archive.add(
                        path,
                        arcname=path.relative_to(staging),
                        recursive=False,
                    )
        digest = hashlib.sha256(temporary_tar.read_bytes()).hexdigest()
        os.replace(temporary_tar, output_path)
    finally:
        temporary_tar.unlink(missing_ok=True)
    json.dump(
        {
            "archive_path": str(output_path),
            "sha256": digest,
            "file_count": str(len(files)),
        },
        sys.stdout,
    )


if __name__ == "__main__":
    try:
        main()
    except (
        KeyError,
        OSError,
        sqlite3.Error,
        subprocess.CalledProcessError,
        ValueError,
    ) as error:
        print(f"package-accepted-workspace: {error}", file=sys.stderr)
        raise SystemExit(1) from error

#!/usr/bin/env python3
"""Build the exact committed source archive consumed by watershop."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEPLOYMENT_PATHS = (
    "observatory/pyproject.toml",
    "observatory/requirements.runtime.lock",
    "observatory/src",
)
DIRTY_PATHS = (
    "observatory",
    "deploy/watershop",
    "terraform/watershop",
    ".github/workflows",
)


def run_git(source_dir: Path, *args: str, capture: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_dir), *args],
        check=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,
        text=capture,
    )
    return result.stdout.strip() if capture else ""


def main() -> None:
    query = json.load(sys.stdin)
    source_dir = Path(query["source_dir"]).resolve()
    output_path = Path(query["output_path"]).resolve()
    revision = query["revision"]

    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision must be a complete lowercase Git SHA")
    if run_git(source_dir, "rev-parse", "--show-toplevel") != str(source_dir):
        raise ValueError(f"source_dir is not the repository root: {source_dir}")
    if run_git(source_dir, "rev-parse", f"{revision}^{{commit}}") != revision:
        raise ValueError("observatory_revision does not identify a commit")

    dirty = run_git(source_dir, "status", "--porcelain", "--", *DIRTY_PATHS)
    if dirty:
        raise ValueError(
            "deployment inputs contain uncommitted changes:\n" + dirty
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".tmp")
    try:
        run_git(
            source_dir,
            "archive",
            "--format=tar",
            f"--output={temporary_path}",
            revision,
            *DEPLOYMENT_PATHS,
            capture=False,
        )
        digest = hashlib.sha256(temporary_path.read_bytes()).hexdigest()
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    json.dump(
        {"archive_path": str(output_path), "sha256": digest},
        sys.stdout,
    )


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"package-observatory: {error}", file=sys.stderr)
        raise SystemExit(1) from error

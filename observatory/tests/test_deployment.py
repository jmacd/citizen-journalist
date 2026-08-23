from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WATERSHOP = REPO_ROOT / "deploy" / "watershop"


def test_watershop_scripts_are_executable_and_parse() -> None:
    scripts = [
        WATERSHOP / "install-staging.sh",
        WATERSHOP / "scripts" / "run-corpus-staging.sh",
        WATERSHOP / "scripts" / "smoke-corpus-staging.sh",
    ]

    for script in scripts:
        assert os.access(script, os.X_OK), f"{script} is not executable"
    subprocess.run(["bash", "-n", *(str(script) for script in scripts)], check=True)


def test_staging_units_require_staging_archive_identity() -> None:
    for unit in (
        "mendo-corpus-staging.service",
        "mendo-corpus-smoke.service",
    ):
        text = (WATERSHOP / "systemd" / unit).read_text(encoding="utf-8")
        assert "ConditionPathExists" not in text
        assert "ExecStart=" in text


def test_staging_configuration_requires_digest_and_isolated_prefix() -> None:
    environment = (WATERSHOP / "staging.env.example").read_text(encoding="utf-8")
    runner = (WATERSHOP / "scripts" / "run-corpus-staging.sh").read_text(
        encoding="utf-8"
    )

    assert "MENDO_IMAGE=" in environment
    assert "@sha256:REPLACE_ME" in environment
    assert "MENDO_ARCHIVE_ROOT=/home/shared/observatory/staging/archive" in environment
    assert "MENDO_STAGING_ARCHIVE_ID=REPLACE_ME" in environment
    assert "MENDO_S3_PREFIX=staging" in environment
    assert 'if [[ "${MENDO_IMAGE}" != *@sha256:* ]]' in runner
    assert '!= "/home/shared/observatory/staging/archive"' in runner
    assert "MENDO_STAGING_ARCHIVE_ID" in runner
    assert "--pull=always" not in runner


def test_observatory_image_workflow_builds_arm_and_x86() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "observatory-image.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    build_step = next(
        step
        for step in workflow["jobs"]["build"]["steps"]
        if step.get("id") == "build"
    )

    assert build_step["with"]["platforms"] == "linux/amd64,linux/arm64"
    assert build_step["with"]["push"] is True
    assert build_step["with"]["provenance"] == "mode=max"
    assert build_step["with"]["sbom"] is True


def test_runtime_image_uses_production_lock_and_nonroot_user() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile.observatory").read_text(encoding="utf-8")

    assert "FROM python:3.14-slim@sha256:" in dockerfile
    assert "requirements.runtime.lock" in dockerfile
    assert "requirements.lock /tmp/requirements.lock" not in dockerfile
    assert "USER observatory" in dockerfile

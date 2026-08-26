from __future__ import annotations

import os
import json
import subprocess
import tarfile
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


def test_staging_configuration_requires_native_runtime_and_isolated_prefix() -> None:
    environment = (WATERSHOP / "staging.env.example").read_text(encoding="utf-8")
    runner = (WATERSHOP / "scripts" / "run-corpus-staging.sh").read_text(
        encoding="utf-8"
    )

    assert "MENDO_OBSERVATORY_BIN=/home/jmacd/observatory/venv/bin" in environment
    assert "MENDO_SOURCE_REVISION=" in environment
    assert "MENDO_SOURCE_SHA256=" in environment
    assert "MENDO_RUNTIME_LOCK_SHA256=" in environment
    assert "MENDO_PYTHON_VERSION=3.11" in environment
    assert "MENDO_ARCHIVE_ROOT=/home/citizen/journalist/archive" in environment
    assert "MENDO_STAGING_ARCHIVE_ID=REPLACE_ME" in environment
    assert "MENDO_RUN_ROOT=/home/jmacd/observatory/run" in environment
    assert "MENDO_STAGING_RECEIPT_KEY_ID=" not in environment
    assert "MENDO_STAGING_RECEIPT_PRIVATE_KEY=" not in environment
    assert "MENDO_S3_PREFIX=staging" in environment
    assert "${MENDO_OBSERVATORY_BIN}/mendo-release" in runner
    assert '!= "/home/citizen/journalist/archive"' in runner
    assert "MENDO_STAGING_ARCHIVE_ID" in runner
    assert 'MENDO_RUN_ROOT="${MENDO_RUN_ROOT:-${HOME}/observatory/run}"' in runner
    assert "command -v flock" in runner
    assert "flock -n 9" in runner
    assert "exit 75" in runner
    assert "check_runtime_marker mendo-source-revision" in runner
    assert "check_runtime_marker mendo-source.sha256" in runner
    assert "check_runtime_marker mendo-runtime-lock.sha256" in runner
    assert '"${MENDO_PYTHON_VERSION}".*' in runner
    assert "--reuse-unchanged" in runner
    assert "podman" not in runner

    smoke = (WATERSHOP / "scripts" / "smoke-corpus-staging.sh").read_text(
        encoding="utf-8"
    )
    assert '"${MENDO_OBSERVATORY_BIN}/mendo-release" receipt' in smoke
    assert "staging-receipts" in smoke
    assert "--source-revision" in smoke
    assert "--source-sha256" in smoke
    assert "--runtime-lock-sha256" in smoke
    assert "--expected-archive-id" in smoke
    assert "--expected-release-id" in smoke
    assert "--expected-manifest-sha256" in smoke
    assert "check_runtime_marker mendo-source-revision" in smoke
    assert "check_runtime_marker mendo-source.sha256" in smoke
    assert "check_runtime_marker mendo-runtime-lock.sha256" in smoke
    assert "flock -n 9" in smoke
    assert "podman" not in smoke

    installer = (WATERSHOP / "install-staging.sh").read_text(encoding="utf-8")
    assert "provision staging with terraform/watershop" in installer
    assert "staging.env.example" not in installer
    assert "receipt.env" in installer

    staging_unit = (
        WATERSHOP / "systemd" / "mendo-corpus-staging.service"
    ).read_text(encoding="utf-8")
    smoke_unit = (WATERSHOP / "systemd" / "mendo-corpus-smoke.service").read_text(
        encoding="utf-8"
    )
    assert "receipt.env" not in staging_unit
    assert "EnvironmentFile=/home/jmacd/observatory/env/receipt.env" in smoke_unit


def test_watershop_terraform_is_repository_local() -> None:
    terraform_root = REPO_ROOT / "terraform" / "watershop"
    main = (terraform_root / "main.tf").read_text(encoding="utf-8")
    documentation = (terraform_root / "README.md").read_text(encoding="utf-8")

    assert "tls_private_key" in main
    assert "random_uuid" in main
    assert "package-observatory.py" in main
    assert "caspar.water" not in main
    assert "does not import" in documentation


def test_source_packager_archives_committed_deployment_inputs(tmp_path: Path) -> None:
    repository = tmp_path / "source"
    (repository / "observatory" / "src" / "example").mkdir(parents=True)
    (repository / "deploy" / "watershop").mkdir(parents=True)
    (repository / ".github" / "workflows").mkdir(parents=True)
    (repository / "observatory" / "pyproject.toml").write_text(
        "[build-system]\n", encoding="utf-8"
    )
    (repository / "observatory" / "requirements.runtime.lock").write_text(
        "example==1\n", encoding="utf-8"
    )
    (repository / "observatory" / "src" / "example" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(repository), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "Test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "fixture"], check=True)
    revision = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    archive = tmp_path / "observatory-source.tar"
    packager = REPO_ROOT / "terraform" / "watershop" / "package-observatory.py"
    result = subprocess.run(
        [str(packager)],
        input=json.dumps(
            {
                "source_dir": str(repository),
                "revision": revision,
                "output_path": str(archive),
            }
        ),
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["archive_path"] == str(archive)
    assert len(payload["sha256"]) == 64
    with tarfile.open(archive) as source_archive:
        assert "observatory/pyproject.toml" in source_archive.getnames()

    (repository / "observatory" / "pyproject.toml").write_text(
        "[build-system]\nrequires=[]\n", encoding="utf-8"
    )
    rejected = subprocess.run(
        [str(packager)],
        input=json.dumps(
            {
                "source_dir": str(repository),
                "revision": revision,
                "output_path": str(archive),
            }
        ),
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "uncommitted changes" in rejected.stderr


def test_accepted_workspace_packager_uses_sqlite_backup_and_inventory() -> None:
    packager = (
        REPO_ROOT
        / "terraform"
        / "watershop"
        / "package-accepted-workspace.py"
    ).read_text(encoding="utf-8")

    assert "input_database.backup(output_database)" in packager
    assert "PRAGMA integrity_check" in packager
    assert "SHA256SUMS" in packager
    assert "captures" in packager
    assert "cases/UM_2025-0004" in packager


def test_observatory_image_workflow_builds_arm_and_x86() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "observatory-image.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    build_step = next(
        step
        for step in workflow["jobs"]["build"]["steps"]
        if step.get("id") == "build"
    )

    assert workflow["jobs"]["build"]["needs"] == "test"
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["build"]["permissions"]["packages"] == "write"
    assert workflow["jobs"]["test"]["steps"][-1]["run"] == (
        "python -m pytest observatory/tests"
    )
    setup_python = next(
        step
        for step in workflow["jobs"]["test"]["steps"]
        if step.get("uses", "").startswith("actions/setup-python")
    )
    assert setup_python["with"]["python-version"] == "3.14.7"
    assert build_step["with"]["platforms"] == "linux/amd64,linux/arm64"
    assert build_step["with"]["push"] is True
    assert build_step["with"]["provenance"] == "mode=max"
    assert build_step["with"]["sbom"] is True
    assert "GITHUB_STEP_SUMMARY" in workflow["jobs"]["build"]["steps"][-1]["run"]


def test_runtime_image_uses_production_lock_and_nonroot_user() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile.observatory").read_text(encoding="utf-8")

    assert "FROM python:3.14-slim@sha256:" in dockerfile
    assert "requirements.runtime.lock" in dockerfile
    assert "requirements.lock /tmp/requirements.lock" not in dockerfile
    assert "USER observatory" in dockerfile


def test_promotion_workflow_never_rebuilds_or_deploys() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "observatory-promote.yml"
    text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    job = workflow["jobs"]["promote"]

    assert job["environment"] == "production"
    assert workflow["permissions"] == {
        "contents": "read",
        "packages": "read",
    }
    assert "mendo-promote validate-receipt" in text
    assert "docker buildx imagetools inspect" in text
    assert "--image-index" in text
    assert "production_image" in text
    assert "--image-revision" in text
    assert "--expected-image-repository" in text
    assert "MENDO_STAGING_RECEIPT_PUBLIC_KEY" in text
    assert "secrets.MENDO_STAGING_RECEIPT" not in text
    assert "github.event.repository.default_branch" in text
    assert "image-index.json" in text
    assert "actions/upload-artifact@v4" in text
    assert "docker buildx build" not in text
    assert "az containerapp" not in text

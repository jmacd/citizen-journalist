#!/usr/bin/env bash
set -euo pipefail

required=(
  MENDO_IMAGE
  MENDO_ARCHIVE_ROOT
  MENDO_STAGING_ARCHIVE_ID
  MENDO_RELEASE_WORK_ROOT
  MENDO_S3_ENDPOINT
  MENDO_S3_BUCKET
  MENDO_S3_REGION
  MENDO_RELEASE_CHANNEL
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "required environment variable is unset: ${name}" >&2
    exit 2
  fi
done

if [[ "${MENDO_IMAGE}" != *@sha256:* ]]; then
  echo "MENDO_IMAGE must be pinned by digest" >&2
  exit 2
fi
canonical_archive_root=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${MENDO_ARCHIVE_ROOT}")
if [[ "${canonical_archive_root}" != "/home/shared/observatory/staging/archive" ]]; then
  echo "staging archive root is not the dedicated staging path: ${canonical_archive_root}" >&2
  exit 2
fi
if [[ ! -f "${MENDO_ARCHIVE_ROOT}/archive.json" ]]; then
  echo "archive identity is unavailable: ${MENDO_ARCHIVE_ROOT}/archive.json" >&2
  exit 2
fi

archive_id=$(
  python3 -c \
    'import json,sys; print(json.load(open(sys.argv[1]))["archive_id"])' \
    "${MENDO_ARCHIVE_ROOT}/archive.json"
)
if [[ "${archive_id}" != "${MENDO_STAGING_ARCHIVE_ID}" ]]; then
  echo "staging archive identity does not match configured archive ID" >&2
  exit 2
fi
mkdir -p "${MENDO_RELEASE_WORK_ROOT}"
destination=$(
  mktemp -d "${MENDO_RELEASE_WORK_ROOT}/.staging-smoke-XXXXXXXX"
)
rmdir "${destination}"
container_destination="/work/$(basename "${destination}")"

prefix_args=()
if [[ -n "${MENDO_S3_PREFIX:-}" ]]; then
  prefix_args=(--prefix "${MENDO_S3_PREFIX}")
fi

podman run --rm \
  --name mendo-corpus-smoke \
  --network=host \
  --userns=keep-id \
  --user "$(id -u):$(id -g)" \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=1g \
  --cap-drop=all \
  --security-opt=no-new-privileges \
  --env AWS_ACCESS_KEY_ID \
  --env AWS_SECRET_ACCESS_KEY \
  --volume "${MENDO_RELEASE_WORK_ROOT}:/work:rw" \
  "${MENDO_IMAGE}" \
  mendo-release materialize-s3 \
    --archive-id "${archive_id}" \
    --channel "${MENDO_RELEASE_CHANNEL}" \
    --destination "${container_destination}" \
    --bucket "${MENDO_S3_BUCKET}" \
    --endpoint-url "${MENDO_S3_ENDPOINT}" \
    --region "${MENDO_S3_REGION}" \
    "${prefix_args[@]}"

printf 'staging corpus materialized at %s\n' "${destination}"

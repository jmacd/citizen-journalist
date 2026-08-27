#!/usr/bin/env bash
set -euo pipefail

MENDO_RUN_ROOT="${MENDO_RUN_ROOT:-${HOME}/observatory/run}"

required=(
  MENDO_OBSERVATORY_BIN
  MENDO_SOURCE_REVISION
  MENDO_SOURCE_SHA256
  MENDO_RUNTIME_LOCK_SHA256
  MENDO_PYTHON_VERSION
  MENDO_ARCHIVE_ROOT
  MENDO_STAGING_ARCHIVE_ID
  MENDO_RELEASE_WORK_ROOT
  MENDO_RUN_ROOT
  MENDO_S3_ENDPOINT
  MENDO_S3_BUCKET
  MENDO_S3_REGION
  MENDO_RELEASE_CHANNEL
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  MENDO_STAGING_RECEIPT_KEY_ID
  MENDO_STAGING_RECEIPT_PRIVATE_KEY
)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "required environment variable is unset: ${name}" >&2
    exit 2
  fi
done

if [[ ! -x "${MENDO_OBSERVATORY_BIN}/mendo-release" ]]; then
  echo "mendo-release is unavailable: ${MENDO_OBSERVATORY_BIN}/mendo-release" >&2
  exit 2
fi
check_runtime_marker() {
  local name=$1
  local expected=$2
  local path="${MENDO_OBSERVATORY_BIN}/../${name}"
  if [[ ! -f "${path}" ]]; then
    echo "runtime marker is unavailable: ${path}" >&2
    exit 2
  fi
  local actual
  actual=$(<"${path}")
  if [[ "${actual}" != "${expected}" ]]; then
    echo "runtime marker ${name} is ${actual}, expected ${expected}" >&2
    exit 2
  fi
}
check_runtime_marker mendo-source-revision "${MENDO_SOURCE_REVISION}"
check_runtime_marker mendo-source.sha256 "${MENDO_SOURCE_SHA256}"
check_runtime_marker mendo-runtime-lock.sha256 "${MENDO_RUNTIME_LOCK_SHA256}"
actual_python_version=$(
  "${MENDO_OBSERVATORY_BIN}/python" -c 'import platform; print(platform.python_version())'
)
if [[ "${actual_python_version}" != "${MENDO_PYTHON_VERSION}".* ]]; then
  echo "runtime Python is ${actual_python_version}, expected ${MENDO_PYTHON_VERSION}.x" >&2
  exit 2
fi
canonical_archive_root=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${MENDO_ARCHIVE_ROOT}")
if [[ "${canonical_archive_root}" != "/home/citizen/journalist/archive" ]]; then
  echo "archive root is not the dedicated Citizen Journalist NFS path: ${canonical_archive_root}" >&2
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
canonical_run_root=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${MENDO_RUN_ROOT}")
if [[ "${canonical_run_root}" != "/home/jmacd/observatory/run" ]]; then
  echo "staging run root is not the dedicated runtime path: ${canonical_run_root}" >&2
  exit 2
fi
if [[ ! -d "${MENDO_RUN_ROOT}" ]]; then
  echo "staging run root is unavailable: ${MENDO_RUN_ROOT}" >&2
  exit 2
fi
if ! command -v flock >/dev/null 2>&1; then
  echo "required command is unavailable: flock" >&2
  exit 2
fi
exec 9>"${MENDO_RUN_ROOT}/corpus-staging.lock"
if ! flock -n 9; then
  echo "another staging operation holds ${MENDO_RUN_ROOT}/corpus-staging.lock" >&2
  exit 75
fi
mkdir -p "${MENDO_RELEASE_WORK_ROOT}"
destination=$(
  mktemp -d "${MENDO_RELEASE_WORK_ROOT}/.staging-smoke-XXXXXXXX"
)
rmdir "${destination}"
prefix_args=()
if [[ -n "${MENDO_S3_PREFIX:-}" ]]; then
  prefix_args=(--prefix "${MENDO_S3_PREFIX}")
fi

materialization_result=$(mktemp "${MENDO_RUN_ROOT}/.staging-materialization-XXXXXXXX")
receipt_temp=$(mktemp "${MENDO_RUN_ROOT}/.staging-receipt-XXXXXXXX")
trap 'rm -f "${materialization_result}" "${receipt_temp}"' EXIT

"${MENDO_OBSERVATORY_BIN}/mendo-release" materialize-s3 \
  --archive-id "${archive_id}" \
  --channel "${MENDO_RELEASE_CHANNEL}" \
  --destination "${destination}" \
  --bucket "${MENDO_S3_BUCKET}" \
  --endpoint-url "${MENDO_S3_ENDPOINT}" \
  --region "${MENDO_S3_REGION}" \
  "${prefix_args[@]}" \
  > "${materialization_result}"

read -r result_archive_id result_release_id result_manifest_sha256 < <(
  python3 -c \
    'import json,sys
d=json.load(open(sys.argv[1]))
print(d["archive_id"], d["release_id"], d["manifest_sha256"])' \
    "${materialization_result}"
)
if [[ "${result_archive_id}" != "${archive_id}" ]]; then
  echo "materialized archive identity does not match staging archive" >&2
  exit 1
fi

"${MENDO_OBSERVATORY_BIN}/mendo-release" receipt \
  --materialized-root "${destination}" \
  --materialized-path "${destination}" \
  --source-revision "${MENDO_SOURCE_REVISION}" \
  --source-sha256 "${MENDO_SOURCE_SHA256}" \
  --runtime-lock-sha256 "${MENDO_RUNTIME_LOCK_SHA256}" \
  --python-version "${actual_python_version}" \
  --channel "${MENDO_RELEASE_CHANNEL}" \
  --expected-archive-id "${result_archive_id}" \
  --expected-release-id "${result_release_id}" \
  --expected-manifest-sha256 "${result_manifest_sha256}" \
  > "${receipt_temp}"

receipt_name=$(
  python3 -c \
    'import hashlib,json,re,sys
p=sys.argv[1]
d=json.load(open(p))
r=d["receipt"]["release_id"]
if not re.fullmatch(r"[0-9a-f-]{36}",r): raise SystemExit("invalid receipt release ID")
b=open(p,"rb").read()
print(f"{r}-{hashlib.sha256(b).hexdigest()}.json")' \
    "${receipt_temp}"
)
receipt_directory="${MENDO_RUN_ROOT}/staging-receipts"
mkdir -p "${receipt_directory}"
chmod 0440 "${receipt_temp}"
receipt_path="${receipt_directory}/${receipt_name}"
if ! ln "${receipt_temp}" "${receipt_path}"; then
  echo "cannot install staging receipt: ${receipt_path}" >&2
  exit 1
fi
rm -f "${materialization_result}" "${receipt_temp}"
trap - EXIT

printf 'staging corpus materialized at %s\n' "${destination}"
printf 'verified staging receipt written to %s\n' "${receipt_path}"

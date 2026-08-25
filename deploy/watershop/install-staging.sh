#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/../.." && pwd)
target_root="${HOME}/observatory"
unit_root="${HOME}/.config/systemd/user"

install -d -m 0750 \
  "${target_root}/bin" \
  "${target_root}/env" \
  "${target_root}/releases" \
  "${target_root}/run" \
  "${target_root}/work" \
  "${unit_root}"

install -m 0755 \
  "${repo_root}/deploy/watershop/scripts/run-corpus-staging.sh" \
  "${target_root}/bin/run-corpus-staging.sh"
install -m 0755 \
  "${repo_root}/deploy/watershop/scripts/smoke-corpus-staging.sh" \
  "${target_root}/bin/smoke-corpus-staging.sh"
install -m 0644 \
  "${repo_root}/deploy/watershop/systemd/mendo-corpus-staging.service" \
  "${unit_root}/mendo-corpus-staging.service"
install -m 0644 \
  "${repo_root}/deploy/watershop/systemd/mendo-corpus-smoke.service" \
  "${unit_root}/mendo-corpus-smoke.service"

environment_file="${target_root}/env/staging.env"
receipt_environment_file="${target_root}/env/receipt.env"
if [[ ! -f "${environment_file}" ]]; then
  echo "${environment_file} is absent; provision staging with terraform/watershop" >&2
  exit 2
fi
if [[ ! -f "${receipt_environment_file}" ]]; then
  echo "${receipt_environment_file} is absent; provision staging with terraform/watershop" >&2
  exit 2
fi
if [[ ! -x "${target_root}/venv/bin/mendo-release" ]]; then
  echo "${target_root}/venv is absent; provision staging with terraform/watershop" >&2
  exit 2
fi
chmod 0600 "${environment_file}"
chmod 0600 "${receipt_environment_file}"

systemctl --user daemon-reload
printf 'installed manual staging units; start with:\n'
printf '  systemctl --user start mendo-corpus-staging.service\n'
printf '  systemctl --user start mendo-corpus-smoke.service\n'

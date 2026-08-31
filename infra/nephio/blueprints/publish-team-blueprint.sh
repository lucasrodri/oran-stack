#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_DIR="${1:-${SCRIPT_DIR}/../../../packages/nephio/r4-simple-mon}"
REPOSITORY="team-blueprints"
WORKSPACE="${2:-v4}"
REVISION_NAME="${REPOSITORY}.r4-simple-mon.${WORKSPACE}"
BASE_REVISION="${REPOSITORY}.r4-simple-mon.v3"

if [[ ! -f "${SOURCE_DIR}/Kptfile" ]] || \
   [[ ! -f "${SOURCE_DIR}/Kustomization" ]] || \
   [[ ! -f "${SOURCE_DIR}/xAppBase.py" ]]; then
  printf 'Blueprint source not found or incomplete: %s\n' "${SOURCE_DIR}" >&2
  exit 1
fi

if kubectl get packagerevision.porch.kpt.dev "${REVISION_NAME}" \
    --namespace=default >/dev/null 2>&1; then
  lifecycle=$(kubectl get packagerevision.porch.kpt.dev "${REVISION_NAME}" \
    --namespace=default --output=jsonpath='{.spec.lifecycle}')
  if [[ "${lifecycle}" == "Published" ]]; then
    printf '%s is already Published\n' "${REVISION_NAME}"
    exit 0
  fi
else
  if [[ "${WORKSPACE}" == "v1" ]]; then
    porchctl rpkg init r4-simple-mon \
      --repository="${REPOSITORY}" \
      --workspace="${WORKSPACE}" \
      --namespace=default
  else
    porchctl rpkg copy "${BASE_REVISION}" \
      --workspace="${WORKSPACE}" \
      --namespace=default
  fi
fi

work_dir=$(mktemp -d)
trap 'rm -r "${work_dir}"' EXIT

porchctl rpkg pull --namespace=default \
  "${REVISION_NAME}" "${work_dir}/package"
cp -a "${SOURCE_DIR}/." "${work_dir}/package/"
# Porch packages are configuration-as-data and accept text resources only.
# Keep local Python/macOS build metadata out of the temporary package copy.
find "${work_dir}/package" -type d -name __pycache__ -prune \
  -exec rm -r -- {} +
find "${work_dir}/package" -type f \( -name '*.pyc' -o -name '._*' \) \
  -delete
porchctl rpkg push --namespace=default \
  "${REVISION_NAME}" "${work_dir}/package"
porchctl rpkg propose --namespace=default "${REVISION_NAME}"
kubectl wait packagerevision.porch.kpt.dev/"${REVISION_NAME}" \
  --namespace=default \
  --for=jsonpath='{.spec.lifecycle}'=Proposed \
  --timeout=180s
porchctl rpkg approve --namespace=default "${REVISION_NAME}"
kubectl wait packagerevision.porch.kpt.dev/"${REVISION_NAME}" \
  --namespace=default \
  --for=jsonpath='{.spec.lifecycle}'=Published \
  --timeout=180s

porchctl rpkg get --namespace=default "${REVISION_NAME}"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_DIR="${1:-${SCRIPT_DIR}/../../../packages/nephio/cic-lab-smoke}"
REVISION_NAME="cic.cic-lab-smoke.v1"
PORCHCTL="${PORCHCTL:-porchctl}"

if [[ ! -f "${SOURCE_DIR}/Kptfile" ]]; then
  printf 'Package source not found: %s\n' "${SOURCE_DIR}" >&2
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
  "${PORCHCTL}" rpkg init cic-lab-smoke \
    --repository=cic \
    --workspace=v1 \
    --namespace=default
fi

work_dir=$(mktemp -d)
trap 'rm -r "${work_dir}"' EXIT

"${PORCHCTL}" rpkg pull --namespace=default "${REVISION_NAME}" "${work_dir}/package"
install -m 0644 "${SOURCE_DIR}/Kptfile" "${work_dir}/package/Kptfile"
install -m 0644 "${SOURCE_DIR}/Kustomization" \
  "${work_dir}/package/Kustomization"
install -m 0644 "${SOURCE_DIR}/smoke-configmap.yaml" \
  "${work_dir}/package/smoke-configmap.yaml"
"${PORCHCTL}" rpkg push --namespace=default "${REVISION_NAME}" "${work_dir}/package"

"${PORCHCTL}" rpkg propose --namespace=default "${REVISION_NAME}"
kubectl wait packagerevision.porch.kpt.dev/"${REVISION_NAME}" \
  --namespace=default \
  --for=jsonpath='{.spec.lifecycle}'=Proposed \
  --timeout=120s
"${PORCHCTL}" rpkg approve --namespace=default "${REVISION_NAME}"
kubectl wait packagerevision.porch.kpt.dev/"${REVISION_NAME}" \
  --namespace=default \
  --for=jsonpath='{.spec.lifecycle}'=Published \
  --timeout=120s

"${PORCHCTL}" rpkg get --namespace=default "${REVISION_NAME}"

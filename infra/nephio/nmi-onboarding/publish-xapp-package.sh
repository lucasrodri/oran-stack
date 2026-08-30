#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_DIR="${1:-${SCRIPT_DIR}/../../../packages/nephio/r4-simple-mon}"
REVISION_NAME="nmi.r4-simple-mon.v1"

if [[ ! -f "${SOURCE_DIR}/Kptfile" ]] || \
   [[ ! -f "${SOURCE_DIR}/xAppBase.py" ]]; then
  printf 'r4-simple-mon package source not found: %s\n' "${SOURCE_DIR}" >&2
  exit 1
fi

expected_hash=48ca48a2289e1badde94164c3e9d2029e82994c85bc9f8b8928666bb354d129b
actual_hash=$(sha256sum "${SOURCE_DIR}/xAppBase.py" | awk '{print $1}')
if [[ "${actual_hash}" != "${expected_hash}" ]]; then
  printf 'Unexpected xAppBase.py hash: %s\n' "${actual_hash}" >&2
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
  porchctl rpkg init r4-simple-mon \
    --repository=nmi \
    --workspace=v1 \
    --namespace=default
fi

work_dir=$(mktemp -d)
trap 'rm -r "${work_dir}"' EXIT

porchctl rpkg pull --namespace=default \
  "${REVISION_NAME}" "${work_dir}/package"
cp -a "${SOURCE_DIR}/." "${work_dir}/package/"
porchctl rpkg push --namespace=default \
  "${REVISION_NAME}" "${work_dir}/package"
porchctl rpkg propose --namespace=default "${REVISION_NAME}"
kubectl wait packagerevision.porch.kpt.dev/"${REVISION_NAME}" \
  --namespace=default \
  --for=jsonpath='{.spec.lifecycle}'=Proposed \
  --timeout=120s
porchctl rpkg approve --namespace=default "${REVISION_NAME}"
kubectl wait packagerevision.porch.kpt.dev/"${REVISION_NAME}" \
  --namespace=default \
  --for=jsonpath='{.spec.lifecycle}'=Published \
  --timeout=120s

porchctl rpkg get --namespace=default "${REVISION_NAME}"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE_REVISION="nmi.r4-simple-mon.v1"
DEMO_ID="${DEMO_ID:-$(date -u +%Y%m%d%H%M%S)}"
work_dirs=()

cleanup() {
  local directory
  for directory in "${work_dirs[@]}"; do
    [[ ! -d "${directory}" ]] || rm -r "${directory}"
  done
}
trap cleanup EXIT

publish_copy() {
  local workspace="$1"
  local revision_label="$2"
  local demo_state="$3"
  local revision_name="nmi.r4-simple-mon.${workspace}"
  local work_dir

  porchctl rpkg copy "${BASE_REVISION}" \
    --workspace="${workspace}" \
    --namespace=default
  work_dir=$(mktemp -d)
  work_dirs+=("${work_dir}")
  porchctl rpkg pull --namespace=default \
    "${revision_name}" "${work_dir}/package"
  sed -i \
    "s/package-revision: v1/package-revision: ${revision_label}/g; s/demo-state: baseline/demo-state: ${demo_state}/g; s/value: v1$/value: ${revision_label}/; s/value: baseline$/value: ${demo_state}/" \
    "${work_dir}/package/deployment.yaml"
  porchctl rpkg push --namespace=default \
    "${revision_name}" "${work_dir}/package"
  porchctl rpkg propose --namespace=default "${revision_name}"
  kubectl wait packagerevision.porch.kpt.dev/"${revision_name}" \
    --namespace=default \
    --for=jsonpath='{.spec.lifecycle}'=Proposed \
    --timeout=120s
  porchctl rpkg approve --namespace=default "${revision_name}"
  kubectl wait packagerevision.porch.kpt.dev/"${revision_name}" \
    --namespace=default \
    --for=jsonpath='{.spec.lifecycle}'=Published \
    --timeout=120s
  rm -r "${work_dir}"
}

reconcile_latest() {
  local old_revision new_revision applied

  old_revision=$(kubectl get gitrepository nmi \
    --namespace=flux-system \
    --output=jsonpath='{.status.artifact.revision}')
  kubectl annotate gitrepository nmi --namespace=flux-system \
    reconcile.fluxcd.io/requestedAt="$(date +%s)" --overwrite >/dev/null

  new_revision="${old_revision}"
  for _ in $(seq 1 36); do
    new_revision=$(kubectl get gitrepository nmi \
      --namespace=flux-system \
      --output=jsonpath='{.status.artifact.revision}')
    [[ -n "${new_revision}" && "${new_revision}" != "${old_revision}" ]] && break
    sleep 5
  done
  [[ -n "${new_revision}" && "${new_revision}" != "${old_revision}" ]]

  kubectl annotate kustomization r4-simple-mon --namespace=flux-system \
    reconcile.fluxcd.io/requestedAt="$(date +%s)" --overwrite >/dev/null
  applied=""
  for _ in $(seq 1 60); do
    applied=$(kubectl get kustomization r4-simple-mon \
      --namespace=flux-system \
      --output=jsonpath='{.status.lastAppliedRevision}')
    [[ "${applied}" == "${new_revision}" ]] && break
    sleep 5
  done
  [[ "${applied}" == "${new_revision}" ]]
  printf 'Flux applied %s\n' "${new_revision}"
}

kubectl get packagerevision.porch.kpt.dev "${BASE_REVISION}" \
  --namespace=default >/dev/null

update_label="${DEMO_ID}-update"
publish_copy "demo-${DEMO_ID}-update" "${update_label}" tuned
reconcile_latest
"${SCRIPT_DIR}/verify-xapp-package.sh" "${update_label}" tuned

rollback_label="${DEMO_ID}-rollback"
# The rollback starts from v1, not from the tuned package. Git history still
# advances, while the desired behavior returns to the known-good baseline.
publish_copy "demo-${DEMO_ID}-rollback" "${rollback_label}" baseline
reconcile_latest
"${SCRIPT_DIR}/verify-xapp-package.sh" "${rollback_label}" baseline

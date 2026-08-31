#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_DIR="${1:-${SCRIPT_DIR}/../../../packages/nephio/r4-simple-mon}"

kubectl apply --filename="${SCRIPT_DIR}/../workload-clusters.yaml"
kubectl apply --filename="${SCRIPT_DIR}/repository.yaml"
kubectl wait repository.infra.nephio.org/team-blueprints \
  --for=jsonpath='{.status.conditions[0].status}'=True \
  --timeout=180s
kubectl wait token.infra.nephio.org/team-blueprints-access-token-porch \
  --namespace=default \
  --for=jsonpath='{.status.conditions[0].status}'=True \
  --timeout=180s

kubectl apply --filename="${SCRIPT_DIR}/porch-repository.yaml"
kubectl wait repository.config.porch.kpt.dev/team-blueprints \
  --namespace=default \
  --for=condition=Ready \
  --timeout=180s

"${SCRIPT_DIR}/publish-team-blueprint.sh" "${SOURCE_DIR}" v4
nmi_previous=$(kubectl get packagevariant simple-mon-nmi --namespace=default \
  --output=jsonpath='{.status.downstreamTargets[-1].name}' 2>/dev/null || true)
cic_previous=$(kubectl get packagevariant simple-mon-cic-arm64 --namespace=default \
  --output=jsonpath='{.status.downstreamTargets[-1].name}' 2>/dev/null || true)
nmi_generation_before=$(kubectl get packagevariant simple-mon-nmi --namespace=default \
  --output=jsonpath='{.metadata.generation}' 2>/dev/null || printf '0')
cic_generation_before=$(kubectl get packagevariant simple-mon-cic-arm64 --namespace=default \
  --output=jsonpath='{.metadata.generation}' 2>/dev/null || printf '0')
kubectl apply --filename="${SCRIPT_DIR}/simple-mon-nmi-variant.yaml"
kubectl apply --filename="${SCRIPT_DIR}/simple-mon-cic-variant.yaml"
nmi_generation_after=$(kubectl get packagevariant simple-mon-nmi --namespace=default \
  --output=jsonpath='{.metadata.generation}')
cic_generation_after=$(kubectl get packagevariant simple-mon-cic-arm64 --namespace=default \
  --output=jsonpath='{.metadata.generation}')

approve_and_wait_for_variant() {
  local package_variant="$1"
  local previous_revision="$2"
  local label="$3"
  local require_new_revision="$4"
  local revision=""
  local lifecycle=""

  for attempt in $(seq 1 90); do
    revision=$(kubectl get packagevariant "${package_variant}" \
      --namespace=default \
      --output=jsonpath='{.status.downstreamTargets[-1].name}' 2>/dev/null || true)

    # The Ready condition can remain true while the controller creates an edit
    # revision. Give it a bounded window to replace the previous target.
    if [[ -z "${revision}" ]] || \
       [[ "${require_new_revision}" == "true" && \
          "${revision}" == "${previous_revision}" ]]; then
      sleep 2
      continue
    fi

    lifecycle=$(kubectl get packagerevision.porch.kpt.dev "${revision}" \
      --namespace=default --output=jsonpath='{.spec.lifecycle}')
    if [[ "${lifecycle}" == "Draft" ]]; then
      porchctl rpkg propose --namespace=default "${revision}"
      kubectl wait packagerevision.porch.kpt.dev/"${revision}" \
        --namespace=default \
        --for=jsonpath='{.spec.lifecycle}'=Proposed \
        --timeout=180s
      lifecycle="Proposed"
    fi
    if [[ "${lifecycle}" == "Proposed" ]]; then
      porchctl rpkg approve --namespace=default "${revision}"
    fi

    kubectl wait packagerevision.porch.kpt.dev/"${revision}" \
      --namespace=default \
      --for=jsonpath='{.spec.lifecycle}'=Published \
      --timeout=180s
    printf 'Published %s variant: %s\n' "${label}" "${revision}"
    return
  done

  printf 'Timed out waiting for the %s PackageVariant to publish\n' \
    "${label}" >&2
  return 1
}

if (( nmi_generation_after > nmi_generation_before )); then
  nmi_require_new=true
else
  nmi_require_new=false
fi
if (( cic_generation_after > cic_generation_before )); then
  cic_require_new=true
else
  cic_require_new=false
fi

approve_and_wait_for_variant simple-mon-nmi "${nmi_previous}" NMI \
  "${nmi_require_new}" || {
  kubectl get packagevariant simple-mon-nmi --namespace=default --output=yaml >&2
  exit 1
}
approve_and_wait_for_variant simple-mon-cic-arm64 "${cic_previous}" CIC \
  "${cic_require_new}" || {
  kubectl get packagevariant simple-mon-cic-arm64 --namespace=default --output=yaml >&2
  exit 1
}

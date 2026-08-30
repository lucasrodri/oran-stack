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

"${SCRIPT_DIR}/publish-team-blueprint.sh" "${SOURCE_DIR}"
kubectl apply --filename="${SCRIPT_DIR}/simple-mon-nmi-variant.yaml"

for _ in $(seq 1 90); do
  revision=$(kubectl get packagerevisions.porch.kpt.dev \
    --namespace=default --output=json | jq -r '
      [.items[] |
       select(.spec.repository == "nmi") |
       select(.spec.packageName == "r4-simple-mon-nmi") |
       select(.spec.lifecycle == "Published")] |
       sort_by(.spec.revision) | last | .metadata.name // empty')
  if [[ -n "${revision}" ]]; then
    printf 'Published NMI variant: %s\n' "${revision}"
    exit 0
  fi
  sleep 2
done

printf 'Timed out waiting for the NMI PackageVariant to publish\n' >&2
kubectl get packagevariant simple-mon-nmi --namespace=default --output=yaml >&2
exit 1

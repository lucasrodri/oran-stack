#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_DIR="${1:-${SCRIPT_DIR}/../../../packages/nephio/nmi-lab-smoke}"

kubectl apply --filename="${SCRIPT_DIR}/repository.yaml"
kubectl wait repository.infra.nephio.org/nmi \
  --for=jsonpath='{.status.conditions[0].status}'=True \
  --timeout=120s
kubectl wait token.infra.nephio.org/nmi-access-token-porch \
  --namespace=default \
  --for=jsonpath='{.status.conditions[0].status}'=True \
  --timeout=120s
kubectl wait token.infra.nephio.org/nmi-access-token-flux \
  --namespace=flux-system \
  --for=jsonpath='{.status.conditions[0].status}'=True \
  --timeout=120s

kubectl apply --filename="${SCRIPT_DIR}/porch-repository.yaml"
kubectl wait repository.config.porch.kpt.dev/nmi \
  --namespace=default \
  --for=condition=Ready \
  --timeout=120s

kubectl apply --filename="${SCRIPT_DIR}/workload-rbac.yaml"
"${SCRIPT_DIR}/publish-smoke-package.sh" "${SOURCE_DIR}"
kubectl apply --filename="${SCRIPT_DIR}/flux-sync.yaml"

kubectl wait gitrepository.source.toolkit.fluxcd.io/nmi \
  --namespace=flux-system \
  --for=condition=Ready \
  --timeout=180s
kubectl wait kustomization.kustomize.toolkit.fluxcd.io/nmi-lab-smoke \
  --namespace=flux-system \
  --for=condition=Ready \
  --timeout=180s

kubectl get gitrepository,kustomization --namespace=flux-system
kubectl get configmap nephio-delivery-smoke \
  --namespace=nephio-lab \
  --output=jsonpath='{.data.message}{" | revision="}{.data.revision}{"\n"}'

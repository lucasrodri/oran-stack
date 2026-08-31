#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_DIR="${1:-${SCRIPT_DIR}/../../../packages/nephio/cic-lab-smoke}"

kubectl apply --filename="${SCRIPT_DIR}/gitea-nodeport.yaml"
kubectl apply --filename="${SCRIPT_DIR}/nmi-ric-nodeports.yaml"
kubectl apply --filename="${SCRIPT_DIR}/repository.yaml"
kubectl wait repository.infra.nephio.org/cic \
  --for=jsonpath='{.status.conditions[0].status}'=True \
  --timeout=120s
kubectl wait token.infra.nephio.org/cic-access-token-porch \
  --namespace=default \
  --for=jsonpath='{.status.conditions[0].status}'=True \
  --timeout=120s

kubectl apply --filename="${SCRIPT_DIR}/porch-repository.yaml"
kubectl wait repository.config.porch.kpt.dev/cic \
  --namespace=default \
  --for=condition=Ready \
  --timeout=120s

"${SCRIPT_DIR}/publish-smoke-package.sh" "${SOURCE_DIR}"

kubectl get repository.infra.nephio.org/cic
kubectl get repository.config.porch.kpt.dev/cic --namespace=default
kubectl get packagerevision.porch.kpt.dev/cic.cic-lab-smoke.v1 \
  --namespace=default
kubectl get service gitea-lab --namespace=gitea

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

"${SCRIPT_DIR}/install-flux-arm64.sh"
kubectl apply --filename="${SCRIPT_DIR}/workload-rbac.yaml"
kubectl apply --filename="${SCRIPT_DIR}/flux-sync.yaml"
kubectl apply --filename="${SCRIPT_DIR}/cic-xapp-rbac.yaml"
kubectl apply --filename="${SCRIPT_DIR}/cic-rmr-return-bridge.yaml"
kubectl apply --filename="${SCRIPT_DIR}/cic-xapp-flux-sync.yaml"

kubectl wait gitrepository.source.toolkit.fluxcd.io/cic \
  --namespace=flux-system \
  --for=condition=Ready \
  --timeout=180s
kubectl wait kustomization.kustomize.toolkit.fluxcd.io/cic-lab-smoke \
  --namespace=flux-system \
  --for=condition=Ready \
  --timeout=180s
kubectl wait kustomization.kustomize.toolkit.fluxcd.io/r4-simple-mon-cic \
  --namespace=flux-system \
  --for=condition=Ready \
  --timeout=300s

kubectl get gitrepository,kustomization --namespace=flux-system
kubectl get configmap nephio-delivery-smoke \
  --namespace=nephio-lab \
  --output=jsonpath='{.data.message}{" | site="}{.data.site}{" | architecture="}{.data.architecture}{" | revision="}{.data.revision}{"\n"}'
"${SCRIPT_DIR}/verify-cic-xapp.sh"

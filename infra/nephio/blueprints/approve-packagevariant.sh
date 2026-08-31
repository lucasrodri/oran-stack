#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
  printf 'Usage: %s <PackageVariant-name>\n' "$0" >&2
  exit 2
fi

variant=$1
revision=""
for _ in $(seq 1 60); do
  revision=$(kubectl get packagevariant.config.porch.kpt.dev "${variant}" \
    --namespace=default \
    --output=jsonpath='{.status.downstreamTargets[-1].name}' 2>/dev/null || true)
  [[ -n "${revision}" ]] && break
  sleep 2
done

if [[ -z "${revision}" ]]; then
  printf 'PackageVariant %s did not produce a downstream revision\n' "${variant}" >&2
  kubectl get packagevariant.config.porch.kpt.dev "${variant}" \
    --namespace=default --output=yaml >&2 || true
  exit 1
fi

lifecycle=$(kubectl get packagerevision.porch.kpt.dev "${revision}" \
  --namespace=default --output=jsonpath='{.spec.lifecycle}')
if [[ "${lifecycle}" == Draft ]]; then
  porchctl rpkg propose --namespace=default "${revision}"
  kubectl wait packagerevision.porch.kpt.dev/"${revision}" \
    --namespace=default \
    --for=jsonpath='{.spec.lifecycle}'=Proposed \
    --timeout=180s
  lifecycle=Proposed
fi
if [[ "${lifecycle}" == Proposed ]]; then
  porchctl rpkg approve --namespace=default "${revision}"
fi

kubectl wait packagerevision.porch.kpt.dev/"${revision}" \
  --namespace=default \
  --for=jsonpath='{.spec.lifecycle}'=Published \
  --timeout=180s
porchctl rpkg get --namespace=default "${revision}"

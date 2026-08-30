#!/usr/bin/env bash
set -euo pipefail

FLUX_VERSION="v2.7.5"
FLUX_ARCHIVE_SHA256="89d3ebb47ee5f7a0def33217e8dcb885e0bec41d01d0e23fc84e9aba0416c24e"

case "$(uname -m)" in
  aarch64|arm64) ;;
  *)
    printf 'This installer is intentionally pinned to Linux ARM64; found %s\n' \
      "$(uname -m)" >&2
    exit 1
    ;;
esac

work_dir=$(mktemp -d)
trap 'rm -r "${work_dir}"' EXIT

archive="${work_dir}/flux.tar.gz"
curl --fail --silent --show-error --location \
  "https://github.com/fluxcd/flux2/releases/download/${FLUX_VERSION}/flux_${FLUX_VERSION#v}_linux_arm64.tar.gz" \
  --output "${archive}"
printf '%s  %s\n' "${FLUX_ARCHIVE_SHA256}" "${archive}" | sha256sum --check --status
tar --extract --gzip --file="${archive}" --directory="${work_dir}" flux

"${work_dir}/flux" install \
  --version="${FLUX_VERSION}" \
  --namespace=flux-system \
  --components=source-controller,kustomize-controller \
  --network-policy=false

kubectl wait deployment/source-controller \
  --namespace=flux-system --for=condition=Available --timeout=300s
kubectl wait deployment/kustomize-controller \
  --namespace=flux-system --for=condition=Available --timeout=300s
kubectl get deployments --namespace=flux-system

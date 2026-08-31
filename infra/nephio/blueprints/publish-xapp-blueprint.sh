#!/usr/bin/env bash
set -euo pipefail

if (( $# < 1 || $# > 4 )); then
  printf 'Usage: %s <package> [source-dir] [workspace] [base-revision]\n' "$0" >&2
  exit 2
fi

package_name=$1
if [[ ! "${package_name}" =~ ^[a-z][a-z0-9-]{2,30}$ ]]; then
  printf 'Invalid package name: %s\n' "${package_name}" >&2
  exit 2
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source_dir=${2:-${script_dir}/../../../packages/nephio/${package_name}}
workspace=${3:-v1}
base_revision=${4:-}
repository=team-blueprints
revision_name="${repository}.${package_name}.${workspace}"

for required in Kptfile Kustomization xAppBase.py; do
  if [[ ! -f "${source_dir}/${required}" ]]; then
    printf 'Blueprint is incomplete; missing %s/%s\n' "${source_dir}" "${required}" >&2
    exit 1
  fi
done

if kubectl get packagerevision.porch.kpt.dev "${revision_name}" \
    --namespace=default >/dev/null 2>&1; then
  lifecycle=$(kubectl get packagerevision.porch.kpt.dev "${revision_name}" \
    --namespace=default --output=jsonpath='{.spec.lifecycle}')
  if [[ "${lifecycle}" == Published ]]; then
    printf '%s is already Published\n' "${revision_name}"
    exit 0
  fi
else
  if [[ -n "${base_revision}" ]]; then
    porchctl rpkg copy "${base_revision}" \
      --workspace="${workspace}" \
      --namespace=default
  else
    porchctl rpkg init "${package_name}" \
      --repository="${repository}" \
      --workspace="${workspace}" \
      --namespace=default
  fi
fi

work_dir=$(mktemp -d)
trap 'rm -r "${work_dir}"' EXIT

porchctl rpkg pull --namespace=default \
  "${revision_name}" "${work_dir}/package"
cp -a "${source_dir}/." "${work_dir}/package/"
find "${work_dir}/package" -type d -name __pycache__ -prune \
  -exec rm -r -- {} +
find "${work_dir}/package" -type f \( -name '*.pyc' -o -name '._*' \) \
  -delete
porchctl rpkg push --namespace=default \
  "${revision_name}" "${work_dir}/package"
porchctl rpkg propose --namespace=default "${revision_name}"
kubectl wait packagerevision.porch.kpt.dev/"${revision_name}" \
  --namespace=default \
  --for=jsonpath='{.spec.lifecycle}'=Proposed \
  --timeout=180s
porchctl rpkg approve --namespace=default "${revision_name}"
kubectl wait packagerevision.porch.kpt.dev/"${revision_name}" \
  --namespace=default \
  --for=jsonpath='{.spec.lifecycle}'=Published \
  --timeout=180s

porchctl rpkg get --namespace=default "${revision_name}"

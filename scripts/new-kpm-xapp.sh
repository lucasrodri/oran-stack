#!/usr/bin/env bash
set -euo pipefail

if (( $# < 1 || $# > 3 )); then
  printf 'Usage: %s <dns-safe-xapp-name> [KPM-metric] [report-period-ms]\n' "$0" >&2
  exit 2
fi

xapp_name=$1
metric=${2:-DRB.UEThpDl}
report_period=${3:-2000}

if [[ ! "${xapp_name}" =~ ^[a-z][a-z0-9-]{2,30}$ ]]; then
  printf 'Invalid xApp name: use 3-31 lowercase DNS-safe characters\n' >&2
  exit 2
fi
if [[ ! "${metric}" =~ ^[A-Za-z0-9._-]+$ ]]; then
  printf 'Invalid KPM metric: %s\n' "${metric}" >&2
  exit 2
fi
if [[ ! "${report_period}" =~ ^[0-9]+$ ]] ||
    (( report_period < 100 || report_period > 60000 )); then
  printf 'Invalid report period: use an integer from 100 to 60000 ms\n' >&2
  exit 2
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/.." && pwd)
output_root=${XAPP_SCAFFOLD_ROOT:-${repo_root}}
script_name=${xapp_name//-/_}_xapp.py

python_target="${output_root}/xapps/python/${script_name}"
package_target="${output_root}/packages/nephio/${xapp_name}"
variant_target="${output_root}/infra/nephio/blueprints/${xapp_name}-nmi-variant.yaml"
rbac_target="${output_root}/infra/nephio/nmi-onboarding/${xapp_name}-rbac.yaml"
flux_target="${output_root}/infra/nephio/nmi-onboarding/${xapp_name}-flux-sync.yaml"

for target in "${python_target}" "${package_target}" "${variant_target}" \
  "${rbac_target}" "${flux_target}"; do
  if [[ -e "${target}" ]]; then
    printf 'Refusing to overwrite existing target: %s\n' "${target}" >&2
    exit 1
  fi
done

mkdir -p \
  "$(dirname -- "${python_target}")" \
  "$(dirname -- "${package_target}")" \
  "$(dirname -- "${variant_target}")" \
  "$(dirname -- "${rbac_target}")"

cp "${repo_root}/xapps/templates/kpm-monitor/student_kpm_xapp.py.tpl" \
  "${python_target}"
cp -a "${repo_root}/packages/nephio/r4-simple-mon" "${package_target}"
# Local validation may leave Python bytecode beside the blueprint sources.
# Nephio packages contain configuration-as-data only; keep generated binary
# metadata out before the text substitution pass.
find "${package_target}" -type d -name __pycache__ -prune \
  -exec rm -r -- {} +
find "${package_target}" -type f \( -name '*.pyc' -o -name '._*' \) \
  -delete
cp "${repo_root}/infra/nephio/blueprints/simple-mon-nmi-variant.yaml" \
  "${variant_target}"
cp "${repo_root}/infra/nephio/nmi-onboarding/xapp-rbac.yaml" "${rbac_target}"
cp "${repo_root}/infra/nephio/nmi-onboarding/xapp-flux-sync.yaml" \
  "${flux_target}"

generated_files=(
  "${python_target}"
  "${variant_target}"
  "${rbac_target}"
  "${flux_target}"
)
while IFS= read -r -d '' file; do
  generated_files+=("${file}")
done < <(find "${package_target}" -type f -print0)

for file in "${generated_files[@]}"; do
  sed -i.bak \
    -e "s/r4-simple-mon/${xapp_name}/g" \
    -e "s/simple-mon-nmi/${xapp_name}-nmi/g" \
    -e "s/kpm_mon_xapp.py/${script_name}/g" \
    -e "s/DRB\.UEThpDl/${metric}/g" \
    -e "s/__REPORT_PERIOD__/${report_period}/g" \
    -e "s/oran\.unb\.br\/kpm-report-period: \"1000\"/oran.unb.br\/kpm-report-period: \"${report_period}\"/g" \
    -e "s/__XAPP_NAME__/${xapp_name}/g" \
    "${file}"
  rm "${file}.bak"
done

# A new Team Blueprint starts at v1. The exact multiarch image digest is known
# only after the generated Python file is committed and GitHub Actions runs.
sed -i.bak \
  -e 's/workspaceName: v[0-9][0-9]*/workspaceName: v1/' \
  -e 's#oran.unb.br/xapp-image: .*#oran.unb.br/xapp-image: REPLACE_WITH_MULTIARCH_IMAGE_DIGEST#' \
  "${variant_target}"
rm "${variant_target}.bak"
sed -i.bak \
  -e 's#oran.unb.br/xapp-image: .*#oran.unb.br/xapp-image: REPLACE_WITH_MULTIARCH_IMAGE_DIGEST#' \
  "${package_target}/workload-cluster.yaml"
rm "${package_target}/workload-cluster.yaml.bak"

chmod 0755 "${python_target}"

printf 'Created xApp scaffold %s\n' "${xapp_name}"
printf '  code:     %s\n' "${python_target}"
printf '  blueprint:%s\n' "${package_target}"
printf '  variant:  %s\n' "${variant_target}"
printf '  RBAC:     %s\n' "${rbac_target}"
printf '  Flux:     %s\n' "${flux_target}"
printf '  KPM:      %s every %s ms\n' "${metric}" "${report_period}"
printf 'Next: implement the callback, commit/push, then replace REPLACE_WITH_MULTIARCH_IMAGE_DIGEST.\n'

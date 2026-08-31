#!/usr/bin/env bash
set -euo pipefail

kubectl wait kustomization.kustomize.toolkit.fluxcd.io/r4-simple-mon-cic \
  --namespace=flux-system \
  --for=condition=Ready \
  --timeout=300s
kubectl rollout status deployment/r4-simple-mon \
  --namespace=ricxapp \
  --timeout=300s

pod=$(kubectl get pods --namespace=ricxapp \
  --selector=app=r4-simple-mon \
  --output=jsonpath='{.items[0].metadata.name}')
node=$(kubectl get pod "${pod}" --namespace=ricxapp \
  --output=jsonpath='{.spec.nodeName}')
architecture=$(kubectl exec --namespace=ricxapp "${pod}" -c xapp -- uname -m)
image_id=$(kubectl get pod "${pod}" --namespace=ricxapp \
  --output=jsonpath='{.status.containerStatuses[?(@.name=="xapp")].imageID}')
rmr_flags=$(kubectl get deployment r4-simple-mon --namespace=ricxapp \
  --output=jsonpath='{.spec.template.spec.containers[?(@.name=="xapp")].env[?(@.name=="RMR_FLAGS")].value}')

if [[ "${node}" != "cic-k8s-w01" ]]; then
  printf 'Unexpected CIC xApp node: %s\n' "${node}" >&2
  exit 1
fi
if [[ "${architecture}" != "aarch64" ]]; then
  printf 'Expected native aarch64 runtime, got: %s\n' "${architecture}" >&2
  exit 1
fi
if [[ "${rmr_flags}" != "0" ]]; then
  printf 'Expected the dynamic RMR route collector (RMR_FLAGS=0), got: %s\n' \
    "${rmr_flags}" >&2
  exit 1
fi

metrics=""
for attempt in $(seq 1 30); do
  metrics=$(curl --fail --silent --show-error \
    http://192.168.0.211:30691/metrics)
  if grep -Eq '^oran_xapp_active_subscriptions 1(\.0)?$' <<<"${metrics}" && \
     grep -Eq '^oran_xapp_kpm_indications_total [1-9][0-9]*(\.0)?$' \
       <<<"${metrics}"; then
    break
  fi
  sleep 5
done
grep -Eq '^oran_xapp_active_subscriptions 1(\.0)?$' <<<"${metrics}"
grep -Eq '^oran_xapp_kpm_indications_total [1-9][0-9]*(\.0)?$' <<<"${metrics}"

printf 'CIC xApp pod=%s node=%s architecture=%s rmr_flags=%s\n' \
  "${pod}" "${node}" "${architecture}" "${rmr_flags}"
printf 'imageID=%s\n' "${image_id}"
grep -E '^(oran_xapp_rmr_indications_total|oran_xapp_kpm_indications_total|oran_xapp_active_subscriptions|oran_xapp_kpm_measurement)' \
  <<<"${metrics}"

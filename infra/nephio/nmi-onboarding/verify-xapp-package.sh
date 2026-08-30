#!/usr/bin/env bash
set -euo pipefail

expected_revision="${1:-}"
expected_state="${2:-}"

kubectl wait kustomization/r4-simple-mon \
  --namespace=flux-system \
  --for=condition=Ready \
  --timeout=300s
kubectl rollout status deployment/r4-simple-mon \
  --namespace=ricxapp \
  --timeout=300s

actual_revision=$(kubectl get deployment r4-simple-mon \
  --namespace=ricxapp \
  --output=jsonpath='{.metadata.annotations.nephio\.org/package-revision}')
actual_state=$(kubectl get deployment r4-simple-mon \
  --namespace=ricxapp \
  --output=jsonpath='{.metadata.annotations.nephio\.org/demo-state}')

if [[ -n "${expected_revision}" && "${actual_revision}" != "${expected_revision}" ]]; then
  printf 'Expected revision %s, found %s\n' \
    "${expected_revision}" "${actual_revision}" >&2
  exit 1
fi
if [[ -n "${expected_state}" && "${actual_state}" != "${expected_state}" ]]; then
  printf 'Expected state %s, found %s\n' \
    "${expected_state}" "${actual_state}" >&2
  exit 1
fi

timeout 120 sh -c \
  "kubectl logs -f --namespace=ricxapp deployment/r4-simple-mon -c xapp --pod-running-timeout=60s | grep -m1 'RIC Indication Received'"

metrics=$(kubectl exec --namespace=ricxapp deployment/r4-simple-mon -c xapp -- \
  sh -c 'wget -qO- http://127.0.0.1:8091/metrics')
kpm_total=$(awk '/^oran_xapp_kpm_indications_total / {print $2}' <<<"${metrics}")
active_subscriptions=$(awk '/^oran_xapp_active_subscriptions / {print $2}' <<<"${metrics}")
if [[ -z "${kpm_total}" || "${kpm_total}" -lt 1 ]]; then
  printf 'No decoded KPM indication was observed\n' >&2
  exit 1
fi
if [[ "${active_subscriptions}" != 1 ]]; then
  printf 'Expected one active subscription, found %s\n' \
    "${active_subscriptions:-none}" >&2
  exit 1
fi

printf 'revision=%s state=%s\n' "${actual_revision}" "${actual_state}"
grep -E \
  '^(oran_xapp_rmr_indications_total|oran_xapp_kpm_indications_total|oran_xapp_active_subscriptions)' \
  <<<"${metrics}"

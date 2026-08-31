#!/usr/bin/env bash
set -euo pipefail

# Recreate only stateless monitoring xApps after a DU/E2 association restart so
# they establish fresh E2 subscriptions. RIC platform and E2Term stay online.

XAPP_NAMESPACE="${XAPP_NAMESPACE:-ricxapp}"
E2MGR_URL="${E2MGR_URL:-http://127.0.0.1:30380/v1/nodeb/states}"
XAPP_DEPLOYMENTS="${XAPP_DEPLOYMENTS:-r4-simple-mon kpm-load-watch}"

kubectl_args=()
if [[ -n "${KUBECONFIG:-}" ]]; then
  kubectl_args+=(--kubeconfig "${KUBECONFIG}")
fi

kctl() {
  kubectl "${kubectl_args[@]}" "$@"
}

echo "Aguardando o O-DU reaparecer no inventário E2..."
connected=0
for _ in $(seq 1 36); do
  if curl -fsS --max-time 3 "${E2MGR_URL}" 2>/dev/null | \
      grep -q 'gnbd_001_001_00019b_e2'; then
    connected=1
    break
  fi
  sleep 5
done
if (( connected != 1 )); then
  echo "Falha: O-DU não reapareceu no E2Mgr em 180 segundos." >&2
  exit 1
fi

for deployment in ${XAPP_DEPLOYMENTS}; do
  if kctl -n "${XAPP_NAMESPACE}" get "deployment/${deployment}" >/dev/null 2>&1; then
    echo "Renovando assinatura E2 de ${deployment}..."
    kctl -n "${XAPP_NAMESPACE}" rollout restart "deployment/${deployment}"
    kctl -n "${XAPP_NAMESPACE}" rollout status \
      "deployment/${deployment}" --timeout=180s
  fi
done

echo "KPM_XAPPS_REFRESHED"

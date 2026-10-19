#!/usr/bin/env bash
set -euo pipefail

# Recover the stateless Near-RT RIC routing inventory and renew all laboratory
# KPM subscriptions after a power, network or multi-node cluster outage.

RIC_NAMESPACE="${RIC_NAMESPACE:-near-rt-ric}"
XAPP_NAMESPACE="${XAPP_NAMESPACE:-ricxapp}"
XAPP_DEPLOYMENTS="${XAPP_DEPLOYMENTS:-r4-simple-mon kpm-load-watch kpm-mon-tmt}"
E2MGR_URL="${E2MGR_URL:-http://127.0.0.1:30380/v1/nodeb/states}"
APPMGR_URL="${APPMGR_URL:-http://127.0.0.1:30080/ric/v1/xapps}"
E2_NODE_ID="${E2_NODE_ID:-gnbd_001_001_00019b_e2}"
RESET_APPMGR="${RESET_APPMGR:-0}"

kubectl_args=()
if [[ -n "${KUBECONFIG:-}" ]]; then
  kubectl_args+=(--kubeconfig "${KUBECONFIG}")
fi

kctl() {
  kubectl "${kubectl_args[@]}" "$@"
}

wait_for_e2() {
  for _ in $(seq 1 36); do
    if curl -fsS --max-time 3 "${E2MGR_URL}" 2>/dev/null | \
        grep -F "${E2_NODE_ID}" | grep -Fq 'CONNECTED'; then
      return 0
    fi
    sleep 5
  done
  return 1
}

restart_xapps() {
  local deployment
  for deployment in ${XAPP_DEPLOYMENTS}; do
    if kctl -n "${XAPP_NAMESPACE}" get "deployment/${deployment}" >/dev/null 2>&1; then
      kctl -n "${XAPP_NAMESPACE}" rollout restart "deployment/${deployment}"
      kctl -n "${XAPP_NAMESPACE}" rollout status \
        "deployment/${deployment}" --timeout=180s
    fi
  done
}

echo "1/6 Verificando o E2 node ${E2_NODE_ID}..."
if ! wait_for_e2; then
  echo "Falha: o O-DU não está CONNECTED no E2Mgr." >&2
  echo "Recupere primeiro a RAN com scripts/recover-ran-zmq.sh." >&2
  exit 1
fi

if [[ "${RESET_APPMGR}" == "1" ]]; then
  echo "2/6 Limpando o inventário volátil do AppMgr..."
  kctl -n "${RIC_NAMESPACE}" rollout restart deployment/ric-appmgr
  kctl -n "${RIC_NAMESPACE}" rollout status deployment/ric-appmgr --timeout=180s
else
  echo "2/6 Preservando o inventário do AppMgr (RESET_APPMGR=${RESET_APPMGR})."
fi

echo "3/6 Reiniciando as xApps para registrar os endpoints no AppMgr..."
restart_xapps

echo "4/6 Conferindo o inventário do AppMgr..."
inventory="$(curl -fsS --max-time 5 "${APPMGR_URL}")"
for deployment in ${XAPP_DEPLOYMENTS}; do
  if kctl -n "${XAPP_NAMESPACE}" get "deployment/${deployment}" >/dev/null 2>&1 && \
      ! grep -Fq "\"name\":\"${deployment}\"" <<<"${inventory}"; then
    echo "Falha: ${deployment} não apareceu no AppMgr." >&2
    exit 1
  fi
done

echo "5/6 Reiniciando o RTMgr para carregar o inventário atual..."
kctl -n "${RIC_NAMESPACE}" rollout restart deployment/ric-rtmgr
kctl -n "${RIC_NAMESPACE}" rollout status deployment/ric-rtmgr --timeout=180s

echo "6/6 Renovando as subscriptions E2 com a tabela de rotas pronta..."
restart_xapps
sleep 15

for deployment in ${XAPP_DEPLOYMENTS}; do
  if ! kctl -n "${XAPP_NAMESPACE}" exec "deployment/${deployment}" -c xapp -- \
      curl -fsS http://127.0.0.1:8091/metrics 2>/dev/null | \
      grep -Fq 'oran_xapp_active_subscriptions 1'; then
    echo "Falha: ${deployment} não possui exatamente uma subscription ativa." >&2
    exit 1
  fi
done

echo "RIC_KPM_RECOVERED"

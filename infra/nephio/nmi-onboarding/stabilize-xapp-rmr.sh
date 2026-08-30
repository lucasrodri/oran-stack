#!/usr/bin/env bash
set -euo pipefail

XAPP_NAMESPACE="${XAPP_NAMESPACE:-ricxapp}"
RIC_NAMESPACE="${RIC_NAMESPACE:-near-rt-ric}"
XAPP_DEPLOYMENT="${XAPP_DEPLOYMENT:-r4-simple-mon}"
RTMGR_DEPLOYMENT="${RTMGR_DEPLOYMENT:-ric-rtmgr}"
XAPP_ENDPOINT="service-ricxapp-r4-simple-mon-rmr.ricxapp:4561"

# RTMgr learns xApps from AppMgr at startup. On the first Helm-to-Flux adoption,
# republish the complete RMR table before recreating the xApp process. Never
# restart E2Term here: doing so drops the SCTP association with the O-DU.
kubectl rollout restart deployment/"${RTMGR_DEPLOYMENT}" \
  --namespace="${RIC_NAMESPACE}"
kubectl rollout status deployment/"${RTMGR_DEPLOYMENT}" \
  --namespace="${RIC_NAMESPACE}" \
  --timeout=300s

route_ready=false
for _ in $(seq 1 36); do
  if kubectl logs --namespace="${RIC_NAMESPACE}" \
      deployment/"${RTMGR_DEPLOYMENT}" -c rtmgr --since=5m | \
      grep -Fq "Update Routes to Endpoint: ${XAPP_ENDPOINT} successful"; then
    route_ready=true
    break
  fi
  sleep 5
done
if [[ "${route_ready}" != true ]]; then
  printf 'RTMgr did not push the xApp route within 180 seconds\n' >&2
  exit 1
fi

delete_latest_rest_subscription() {
  local rest_subscription_id submgr_ip status

  rest_subscription_id=$(kubectl logs --namespace="${XAPP_NAMESPACE}" \
    deployment/"${XAPP_DEPLOYMENT}" -c xapp --since=15m | \
    sed -nE \
      's/.*Successfully subscribed with Subscription ID:[[:space:]]+([^[:space:]]+).*/\1/p' | \
    tail -1 || true)

  if [[ -z "${rest_subscription_id}" ]]; then
    return
  fi

  submgr_ip=$(kubectl get service ric-submgr \
    --namespace="${RIC_NAMESPACE}" \
    --output=jsonpath='{.spec.clusterIP}')
  status=$(curl -sS -o /dev/null -w '%{http_code}' -X DELETE \
    "http://${submgr_ip}:8088/ric/v1/subscriptions/${rest_subscription_id}")
  if [[ "${status}" != 204 && "${status}" != 404 ]]; then
    printf 'Subscription delete returned HTTP %s\n' "${status}" >&2
    exit 1
  fi
}

recreate_xapp_process() {
  local pod

  delete_latest_rest_subscription
  pod=$(kubectl get pods --namespace="${XAPP_NAMESPACE}" \
    --selector=app=r4-simple-mon \
    --output=jsonpath='{.items[0].metadata.name}')
  kubectl delete pod "${pod}" --namespace="${XAPP_NAMESPACE}" --wait=true
  kubectl wait pod --namespace="${XAPP_NAMESPACE}" \
    --selector=app=r4-simple-mon \
    --for=condition=Ready \
    --timeout=300s
}

wait_for_kpm_indication() {
  local timeout_seconds="${1}"

  timeout "${timeout_seconds}" sh -c \
    "kubectl logs -f --namespace='${XAPP_NAMESPACE}' deployment/'${XAPP_DEPLOYMENT}' -c xapp --pod-running-timeout=60s | grep -m1 'RIC Indication Received'"
}

recreate_xapp_process
if ! wait_for_kpm_indication 75; then
  # In this lab RTMgr can publish the subscription-specific route only after
  # the first recreated process registers. One bounded second cycle lets the
  # next process consume that route without touching E2Term or SCTP.
  printf 'No KPM indication in the first cycle; retrying the xApp once\n' >&2
  recreate_xapp_process
  wait_for_kpm_indication 120
fi

kubectl exec --namespace="${XAPP_NAMESPACE}" \
  deployment/"${XAPP_DEPLOYMENT}" -c xapp -- \
  sh -c 'wget -qO- http://127.0.0.1:8091/metrics | grep -E "^(oran_xapp_rmr_indications_total|oran_xapp_kpm_indications_total|oran_xapp_active_subscriptions)"'

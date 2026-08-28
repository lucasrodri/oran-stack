#!/usr/bin/env bash
set -euo pipefail

KUBECONFIG_PATH="${KUBECONFIG:-$(pwd)/kubeconfig}"
NAMESPACE="${RAN_NAMESPACE:-ran}"

echo "Stopping the UE so no stale ZMQ endpoint remains..."
kubectl --kubeconfig="${KUBECONFIG_PATH}" -n "${NAMESPACE}" \
  scale deployment/srsue --replicas=0
kubectl --kubeconfig="${KUBECONFIG_PATH}" -n "${NAMESPACE}" \
  wait --for=delete pod -l app=srsue --timeout=120s

echo "Restarting the DU and waiting for F1/cell readiness..."
kubectl --kubeconfig="${KUBECONFIG_PATH}" -n "${NAMESPACE}" \
  rollout restart deployment/ocudu-du
kubectl --kubeconfig="${KUBECONFIG_PATH}" -n "${NAMESPACE}" \
  rollout status deployment/ocudu-du --timeout=180s

echo "Starting the UE against the current DU endpoint..."
kubectl --kubeconfig="${KUBECONFIG_PATH}" -n "${NAMESPACE}" \
  scale deployment/srsue --replicas=1
kubectl --kubeconfig="${KUBECONFIG_PATH}" -n "${NAMESPACE}" \
  rollout status deployment/srsue --timeout=180s

for _ in $(seq 1 36); do
  logs="$(kubectl --kubeconfig="${KUBECONFIG_PATH}" -n "${NAMESPACE}" \
    logs deployment/srsue -c srsue --tail=400 2>/dev/null || true)"
  if grep -q 'PDU Session Establishment successful' <<<"${logs}"; then
    grep 'PDU Session Establishment successful' <<<"${logs}" | tail -1
    exit 0
  fi
  sleep 5
done

echo "UE did not establish a PDU session within 180 seconds." >&2
exit 1

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
  # Normal lab logging is intentionally set to warning, so successful NAS
  # events are not expected in stdout. The PDU interface is the authoritative
  # functional signal and keeps this recovery check independent of log level.
  if pdu_interface="$(kubectl --kubeconfig="${KUBECONFIG_PATH}" -n "${NAMESPACE}" \
    exec deployment/srsue -c srsue -- \
    ip -brief address show tun_srsue 2>/dev/null)"; then
    echo "PDU session ready: ${pdu_interface}"
    exit 0
  fi
  sleep 5
done

echo "UE did not establish a PDU session within 180 seconds." >&2
exit 1

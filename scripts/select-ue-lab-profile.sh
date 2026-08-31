#!/usr/bin/env bash
set -euo pipefail

# Select one virtual SIM/handset profile for the single ZMQ RF slot.

RAN_NAMESPACE="${RAN_NAMESPACE:-ran}"
CORE_NAMESPACE="${CORE_NAMESPACE:-5g-core}"
UE_DEPLOYMENT="${UE_DEPLOYMENT:-srsue}"
PROFILE="${1:-}"

case "${PROFILE}" in
  ue1|1)
    profile_name=ue1
    imsi=001010000000001
    imei=353490069873319
    ;;
  ue2|2)
    profile_name=ue2
    imsi=001010000000002
    imei=353490069873320
    ;;
  ue3|3)
    profile_name=ue3
    imsi=001010000000003
    imei=353490069873321
    ;;
  *)
    echo "Uso: $0 {ue1|ue2|ue3}" >&2
    exit 2
    ;;
esac

kubectl_args=()
if [[ -n "${KUBECONFIG:-}" ]]; then
  kubectl_args+=(--kubeconfig "${KUBECONFIG}")
fi

kctl() {
  kubectl "${kubectl_args[@]}" "$@"
}

subscriber_count="$({
  kctl -n "${CORE_NAMESPACE}" exec mongodb-0 -c mongodb -- \
    mongosh open5gs --quiet --eval \
    "db.subscribers.countDocuments({imsi:'${imsi}'})"
} | tr -d '\r' | tail -n 1)"
if [[ "${subscriber_count}" != "1" ]]; then
  echo "Perfil ${profile_name} não existe no Open5GS; execute provision-ue-lab-profiles.sh." >&2
  exit 1
fi

echo "Parando o único peer UE do enlace ZMQ..."
kctl -n "${RAN_NAMESPACE}" scale "deployment/${UE_DEPLOYMENT}" --replicas=0
kctl -n "${RAN_NAMESPACE}" wait --for=delete pod -l app=srsue --timeout=120s

echo "Selecionando ${profile_name}: IMSI=${imsi}, IMEI=${imei}..."
patch="$(printf \
  '{"spec":{"template":{"metadata":{"annotations":{"lab.oran.unb.br/ue-profile":"%s"}},"spec":{"initContainers":[{"name":"render-ue-config","env":[{"name":"UE_IMSI","value":"%s"},{"name":"UE_IMEI","value":"%s"}]}]}}}}' \
  "${profile_name}" "${imsi}" "${imei}")"
kctl -n "${RAN_NAMESPACE}" patch "deployment/${UE_DEPLOYMENT}" \
  --type=strategic -p "${patch}" >/dev/null

# The current direct ZMQ endpoint does not reliably accept a second peer after
# the first srsUE disconnects. Recreate only the DU while the UE is stopped;
# keep the CU, Core and E2Term untouched.
echo "Reabrindo o endpoint RF do DU para o novo peer ZMQ..."
kctl -n "${RAN_NAMESPACE}" rollout restart deployment/ocudu-du
kctl -n "${RAN_NAMESPACE}" rollout status deployment/ocudu-du --timeout=180s

kctl -n "${RAN_NAMESPACE}" scale "deployment/${UE_DEPLOYMENT}" --replicas=1
kctl -n "${RAN_NAMESPACE}" rollout status "deployment/${UE_DEPLOYMENT}" --timeout=180s

for _ in $(seq 1 36); do
  if pdu_interface="$(
    kctl -n "${RAN_NAMESPACE}" exec "deployment/${UE_DEPLOYMENT}" -c srsue -- \
      ip -brief address show tun_srsue 2>/dev/null
  )"; then
    rendered_identity="$(
      kctl -n "${RAN_NAMESPACE}" exec "deployment/${UE_DEPLOYMENT}" -c srsue -- \
        sh -c "grep -E '^[[:space:]]*(imsi|imei)[[:space:]]*=' /mnt/srsran/configs/ue.conf"
    )"
    printf '%s\n' "${rendered_identity}"
    echo "PDU session: ${pdu_interface}"
    echo "UE_PROFILE_ATTACHED profile=${profile_name} imsi=${imsi}"
    exit 0
  fi
  sleep 5
done

echo "Falha: ${profile_name} não estabeleceu PDU session em 180 segundos." >&2
exit 1

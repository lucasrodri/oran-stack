#!/usr/bin/env bash
set -euo pipefail

# Trigger kpm-anomaly-prb with a paced downlink flood from the UPF.
#
# The xApp subscribes to DRB.RlcSduTransmittedVolumeDL (kbit per one-second
# report). Its default threshold is 1000 kbit over a five-sample window, so a
# ping stays far below it. A download started on the UE also fails to move the
# metric: an unpaced burst fills the tunnel queue before those packets become
# RLC SDUs at the DU.
#
# This sends about 80 Mbit/s for 30 seconds from the UPF address 10.45.0.1 to
# the UE address currently on tun_srsue. 143 datagrams of 1400 bytes every
# 20 ms is about 214500 packets. The xApp sends E2SM-RC Style 2 Action 6 at
# most once for that UE, so a second run after ACTED does not send again
# until the xApp pod restarts.
#
# Run on oran-k8s-01:
#   sudo env KUBECONFIG=/etc/kubernetes/admin.conf ./scripts/demo-anomaly-prb.sh

RAN_NAMESPACE="${RAN_NAMESPACE:-ran}"
CORE_NAMESPACE="${CORE_NAMESPACE:-5g-core}"
UE_DEPLOYMENT="${UE_DEPLOYMENT:-srsue}"
UPF_ADDRESS="${UPF_ADDRESS:-10.45.0.1}"
FLOOD_SECONDS="${FLOOD_SECONDS:-30}"
FLOOD_BATCH="${FLOOD_BATCH:-143}"
FLOOD_PERIOD="${FLOOD_PERIOD:-0.02}"
FLOOD_PAYLOAD="${FLOOD_PAYLOAD:-1400}"
DEBUG_IMAGE="${DEBUG_IMAGE:-python:3.12-alpine}"

kubectl_args=()
if [[ -n "${KUBECONFIG:-}" ]]; then
  kubectl_args+=(--kubeconfig "${KUBECONFIG}")
fi

kctl() {
  kubectl "${kubectl_args[@]}" "$@"
}

ue_cidr="$(
  kctl -n "${RAN_NAMESPACE}" exec "deployment/${UE_DEPLOYMENT}" -c srsue -- \
    ip -4 -o address show dev tun_srsue
)"
ue_ip="$(awk '{print $4}' <<<"${ue_cidr}")"
ue_ip="${ue_ip%%/*}"
if [[ ! "${ue_ip}" =~ ^10\.45\.0\.([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$ ]]; then
  printf 'tun_srsue has no 10.45.0.0/24 address: %s\n' "${ue_cidr}" >&2
  exit 1
fi

upf_pod="$(
  kctl -n "${CORE_NAMESPACE}" get pod -l app=upf \
    -o jsonpath='{.items[0].metadata.name}'
)"
if [[ -z "${upf_pod}" ]]; then
  echo "No UPF pod found." >&2
  exit 1
fi

printf 'UE address: %s\n' "${ue_ip}"
printf 'UPF pod: %s\n' "${upf_pod}"
printf 'Flood: %ss at %s packets of %s bytes every %ss\n' \
  "${FLOOD_SECONDS}" "${FLOOD_BATCH}" "${FLOOD_PAYLOAD}" "${FLOOD_PERIOD}"

flood_log="$(mktemp -t oran-anomaly-prb.XXXXXX)"
trap 'rm -f "${flood_log}"' EXIT

# A fixed debug-container name fails on the second run because the previous
# ephemeral container is still recorded on the UPF pod.
kctl -n "${CORE_NAMESPACE}" debug -i \
  "${upf_pod}" \
  --container="prb-flood-$(date +%s)" \
  --image="${DEBUG_IMAGE}" \
  --profile=netadmin \
  -- python -c '
import socket, sys, time
dst_ip, upf_ip = sys.argv[1], sys.argv[2]
seconds, batch = float(sys.argv[3]), int(sys.argv[4])
period, size = float(sys.argv[5]), int(sys.argv[6])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((upf_ip, 0))
payload = b"x" * size
dst = (dst_ip, 9)
end = time.perf_counter() + seconds
n = 0
while time.perf_counter() < end:
    start = time.perf_counter()
    for _ in range(batch):
        s.sendto(payload, dst)
    n += batch
    delay = period - (time.perf_counter() - start)
    if delay > 0:
        time.sleep(delay)
print("sent", n, flush=True)
' "${ue_ip}" "${UPF_ADDRESS}" "${FLOOD_SECONDS}" "${FLOOD_BATCH}" \
  "${FLOOD_PERIOD}" "${FLOOD_PAYLOAD}" >"${flood_log}" 2>&1 || {
  cat "${flood_log}" >&2
  exit 1
}

cat "${flood_log}"
sent="$(awk '$1 == "sent" { value = $2 } END { print value + 0 }' "${flood_log}")"
if (( sent <= 0 )); then
  echo "Flood produced no packets." >&2
  exit 1
fi

printf 'Look for the control in the xApp log:\n'
printf '  kubectl -n ricxapp logs deploy/kpm-anomaly-prb -c xapp --tail=40\n'
printf 'The line is: anomaly ue_id=0 ... -> RIC Control Style 2 Action 6 max_prb=0\n'

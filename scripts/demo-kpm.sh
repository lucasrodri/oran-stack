#!/usr/bin/env bash
set -euo pipefail

# Generate bounded downlink traffic through the simulated UE and print the
# E2SM-KPM throughput observed by r4-simple-mon while the transfer is active.

RAN_NAMESPACE="${RAN_NAMESPACE:-ran}"
XAPP_NAMESPACE="${XAPP_NAMESPACE:-ricxapp}"
UE_DEPLOYMENT="${UE_DEPLOYMENT:-srsue}"
XAPP_DEPLOYMENT="${XAPP_DEPLOYMENT:-r4-simple-mon}"
TRAFFIC_URL="${TRAFFIC_URL:-https://speed.cloudflare.com/__down?bytes=10000000}"
GRAFANA_URL="${GRAFANA_URL:-http://192.168.72.10:30300/d/oran-overview/o-ran-stack-overview}"

kubectl_args=()
if [[ -n "${KUBECONFIG:-}" ]]; then
  kubectl_args+=(--kubeconfig "${KUBECONFIG}")
fi

kctl() {
  kubectl "${kubectl_args[@]}" "$@"
}

read_kpm_kbps() {
  kctl -n "${XAPP_NAMESPACE}" exec "deployment/${XAPP_DEPLOYMENT}" -c xapp -- \
    sh -c 'wget -qO- http://127.0.0.1:8091/metrics' 2>/dev/null | \
    awk '
      $1 ~ /^oran_kpm_drb_ue_throughput_dl_kbps\{/ {
        value = $2 + 0
        if (!seen || value > maximum) maximum = value
        seen = 1
      }
      END { print seen ? maximum : 0 }
    '
}

echo "Interface da UE:"
kctl -n "${RAN_NAMESPACE}" exec "deployment/${UE_DEPLOYMENT}" -c srsue -- \
  ip -brief address show tun_srsue

echo "KPM antes do tráfego: $(read_kpm_kbps) kbps"
echo "Gerando tráfego pela tun_srsue: ${TRAFFIC_URL}"

traffic_log="$(mktemp -t oran-kpm-traffic.XXXXXX)"
trap 'rm -f "${traffic_log}"' EXIT

kctl -n "${RAN_NAMESPACE}" exec "deployment/${UE_DEPLOYMENT}" -c srsue -- \
  curl --interface tun_srsue -L --max-time 120 -sS -o /dev/null \
  -w 'HTTP %{http_code}; %{size_download} bytes; %{speed_download} bytes/s\n' \
  "${TRAFFIC_URL}" >"${traffic_log}" &
traffic_pid=$!

maximum_kbps=0
while kill -0 "${traffic_pid}" 2>/dev/null; do
  current_kbps="$(read_kpm_kbps)"
  maximum_kbps="$(awk -v current="${current_kbps}" -v maximum="${maximum_kbps}" \
    'BEGIN { print (current > maximum) ? current : maximum }')"
  printf 'KPM DRB.UEThpDl: %s kbps\n' "${current_kbps}"
  sleep 1
done

wait "${traffic_pid}"
cat "${traffic_log}"

# One final sample catches the report emitted immediately after curl exits.
final_kbps="$(read_kpm_kbps)"
maximum_kbps="$(awk -v current="${final_kbps}" -v maximum="${maximum_kbps}" \
  'BEGIN { print (current > maximum) ? current : maximum }')"
printf 'KPM final: %s kbps; pico observado: %s kbps\n' "${final_kbps}" "${maximum_kbps}"
echo "Grafana: ${GRAFANA_URL}"

if awk -v value="${maximum_kbps}" 'BEGIN { exit !(value > 0) }'; then
  echo "DEMO_KPM_OK"
else
  echo "DEMO_KPM_FALHOU: nenhuma amostra de throughput maior que zero" >&2
  exit 1
fi

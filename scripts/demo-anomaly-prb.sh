#!/usr/bin/env bash
set -euo pipefail

# Leave the normal UE on a clean radio and push one bounded downlink transfer
# through the anomaly UE. The broker erases a fraction of that UE's downlink
# frames so the DU can report DRB.RlcPacketDropRateDl. Prints the per-UE drop
# rate from kpm-anomaly-prb, then checks that the RIC control ACK names the UE
# whose drop rate rose.

RAN_NAMESPACE="${RAN_NAMESPACE:-ran}"
XAPP_NAMESPACE="${XAPP_NAMESPACE:-ricxapp}"
NORMAL_UE="${NORMAL_UE:-srsue-ue1}"
ANOMALY_UE="${ANOMALY_UE:-srsue-ue2}"
XAPP_DEPLOYMENT="${XAPP_DEPLOYMENT:-kpm-anomaly-prb}"
XAPP_HTTP_PORT="${XAPP_HTTP_PORT:-8093}"
TRAFFIC_URL="${TRAFFIC_URL:-https://speed.cloudflare.com/__down?bytes=50000000}"
GRAFANA_URL="${GRAFANA_URL:-http://192.168.72.10:30300/d/oran-overview/o-ran-stack-overview}"

kubectl_args=()
if [[ -n "${KUBECONFIG:-}" ]]; then
  kubectl_args+=(--kubeconfig "${KUBECONFIG}")
fi

kctl() {
  kubectl "${kubectl_args[@]}" "$@"
}

require_tun() {
  local deployment="$1"
  kctl -n "${RAN_NAMESPACE}" exec "deployment/${deployment}" -c srsue -- \
    ip -brief address show tun_srsue
}

read_metrics() {
  kctl -n "${XAPP_NAMESPACE}" exec "deployment/${XAPP_DEPLOYMENT}" -c xapp -- \
    sh -c "if command -v curl >/dev/null 2>&1; then curl -fsS http://127.0.0.1:${XAPP_HTTP_PORT}/metrics; else wget -qO- http://127.0.0.1:${XAPP_HTTP_PORT}/metrics; fi" \
    2>/dev/null
}

echo "UE normal (${NORMAL_UE}), sem transferência:"
normal_before="$(require_tun "${NORMAL_UE}")"
echo "${normal_before}"
echo "UE anômalo (${ANOMALY_UE}):"
require_tun "${ANOMALY_UE}"
echo "Grafana: ${GRAFANA_URL}"
echo "Explore: oran_xapp_kpm_measurement{metric=\"DRB.RlcPacketDropRateDl\",service=\"service-ricxapp-${XAPP_DEPLOYMENT}-http\"}"
echo "Gerando downlink só em ${ANOMALY_UE}: ${TRAFFIC_URL}"

traffic_log="$(mktemp -t oran-anomaly-prb.XXXXXX)"
trap 'rm -f "${traffic_log}"' EXIT

kctl -n "${RAN_NAMESPACE}" exec "deployment/${ANOMALY_UE}" -c srsue -- \
  curl --interface tun_srsue -L --max-time 120 -sS -o /dev/null \
  -w 'HTTP %{http_code}; %{size_download} bytes; %{speed_download} bytes/s\n' \
  "${TRAFFIC_URL}" >"${traffic_log}" &
traffic_pid=$!

declare -A peak_drop=()
while kill -0 "${traffic_pid}" 2>/dev/null; do
  snapshot="$(read_metrics || true)"
  while read -r ue_id drop_rate; do
    [[ -n "${ue_id}" ]] || continue
    printf 'KPM ue_id=%s DRB.RlcPacketDropRateDl=%s\n' "${ue_id}" "${drop_rate}"
    previous="${peak_drop[${ue_id}]:-0}"
    peak_drop["${ue_id}"]="$(awk -v current="${drop_rate}" -v previous="${previous}" \
      'BEGIN { print (current > previous) ? current : previous }')"
  done < <(
    awk '
      $1 ~ /^oran_xapp_kpm_measurement\{/ && $1 ~ /metric="DRB.RlcPacketDropRateDl"/ && $1 ~ /scope="ue"/ {
        ue = ""
        if (match($1, /ue_id="[^"]*"/)) {
          ue = substr($1, RSTART + 7, RLENGTH - 8)
        }
        if (ue != "") print ue, $2 + 0
      }
    ' <<<"${snapshot}"
  )
  sleep 1
done

wait "${traffic_pid}"
cat "${traffic_log}"

echo "UE normal depois da transferência:"
if ! normal_after="$(require_tun "${NORMAL_UE}" 2>/dev/null)"; then
  echo "DEMO_ANOMALY_PRB_FALHOU: ${NORMAL_UE} perdeu tun_srsue" >&2
  exit 1
fi
echo "${normal_after}"

logs="$(kctl -n "${XAPP_NAMESPACE}" logs "deployment/${XAPP_DEPLOYMENT}" -c xapp --tail=400 || true)"
printf '%s\n' "${logs}" | grep -E 'anomaly ue_id=|RIC_CONTROL_(ACK|FAILURE) ue_id=' || true

busy_ue=""
busy_peak=0
for ue_id in "${!peak_drop[@]}"; do
  printf 'Pico ue_id=%s drop_rate=%s\n' "${ue_id}" "${peak_drop[${ue_id}]}"
  if awk -v current="${peak_drop[${ue_id}]}" -v best="${busy_peak}" \
      'BEGIN { exit !(current > best) }'; then
    busy_peak="${peak_drop[${ue_id}]}"
    busy_ue="${ue_id}"
  fi
done

ack_ue="$(printf '%s\n' "${logs}" | sed -n 's/.*RIC_CONTROL_ACK ue_id=\([^ ]*\).*/\1/p' | tail -n 1)"

if [[ "${#peak_drop[@]}" -lt 2 ]]; then
  echo "DEMO_ANOMALY_PRB_FALHOU: a xApp não reportou dois ue_id" >&2
  exit 1
fi
if ! awk -v value="${busy_peak}" 'BEGIN { exit !(value > 0) }'; then
  echo "DEMO_ANOMALY_PRB_FALHOU: nenhum UE teve drop rate maior que zero" >&2
  exit 1
fi
if [[ "${normal_after}" != *tun_srsue* ]]; then
  echo "DEMO_ANOMALY_PRB_FALHOU: ${NORMAL_UE} perdeu tun_srsue" >&2
  exit 1
fi
if [[ -z "${ack_ue}" ]]; then
  echo "DEMO_ANOMALY_PRB_FALHOU: RIC_CONTROL_ACK não apareceu no log" >&2
  exit 1
fi
if [[ "${ack_ue}" != "${busy_ue}" ]]; then
  echo "DEMO_ANOMALY_PRB_FALHOU: ACK ue_id=${ack_ue}, pico no ue_id=${busy_ue}" >&2
  exit 1
fi

echo "DEMO_ANOMALY_PRB_OK ue_id=${ack_ue} pico_drop_rate=${busy_peak}"

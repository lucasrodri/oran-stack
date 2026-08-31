#!/usr/bin/env bash
set -euo pipefail

# Acceptance test for the NMI/CIC lab: generate one bounded transfer through
# the simulated UE and observe the same E2SM-KPM indication stream in the
# local amd64 xApp and in the remote arm64 xApp.

RAN_NAMESPACE="${RAN_NAMESPACE:-ran}"
XAPP_NAMESPACE="${XAPP_NAMESPACE:-ricxapp}"
UE_DEPLOYMENT="${UE_DEPLOYMENT:-srsue}"
XAPP_DEPLOYMENT="${XAPP_DEPLOYMENT:-r4-simple-mon}"
CIC_METRICS_URL="${CIC_METRICS_URL:-http://192.168.0.211:30691/metrics}"
TRAFFIC_URL="${TRAFFIC_URL:-https://speed.cloudflare.com/__down?bytes=50000000}"
GRAFANA_URL="${GRAFANA_URL:-http://192.168.72.10:30300/d/oran-overview/o-ran-stack-overview}"

kubectl_args=()
if [[ -n "${KUBECONFIG:-}" ]]; then
  kubectl_args+=(--kubeconfig "${KUBECONFIG}")
fi

kctl() {
  kubectl "${kubectl_args[@]}" "$@"
}

metric_maximum() {
  awk '
    $1 ~ /^oran_kpm_drb_ue_throughput_dl_kbps\{/ {
      value = $2 + 0
      if (!seen || value > maximum) maximum = value
      seen = 1
    }
    END { print seen ? maximum : 0 }
  '
}

read_nmi_kpm() {
  kctl -n "${XAPP_NAMESPACE}" exec "deployment/${XAPP_DEPLOYMENT}" -c xapp -- \
    sh -c 'if command -v curl >/dev/null 2>&1; then curl -fsS http://127.0.0.1:8091/metrics; else wget -qO- http://127.0.0.1:8091/metrics; fi' \
    2>/dev/null | metric_maximum
}

read_cic_kpm() {
  curl -fsS --max-time 5 "${CIC_METRICS_URL}" | metric_maximum
}

interface_address="$(
  kctl -n "${RAN_NAMESPACE}" exec "deployment/${UE_DEPLOYMENT}" -c srsue -- \
    ip -brief address show tun_srsue
)"
echo "UE pronta: ${interface_address}"
echo "KPM inicial: NMI=$(read_nmi_kpm) kbps CIC=$(read_cic_kpm) kbps"
echo "Transferência limitada: ${TRAFFIC_URL}"

traffic_log="$(mktemp -t oran-kpm-multisite.XXXXXX)"
trap 'rm -f "${traffic_log}"' EXIT

kctl -n "${RAN_NAMESPACE}" exec "deployment/${UE_DEPLOYMENT}" -c srsue -- \
  curl --interface tun_srsue -L --max-time 120 -sS -o /dev/null \
  -w 'HTTP %{http_code}; %{size_download} bytes; %{speed_download} bytes/s\n' \
  "${TRAFFIC_URL}" >"${traffic_log}" &
traffic_pid=$!

nmi_peak=0
cic_peak=0
while kill -0 "${traffic_pid}" 2>/dev/null; do
  nmi_current="$(read_nmi_kpm)"
  cic_current="$(read_cic_kpm)"
  nmi_peak="$(awk -v current="${nmi_current}" -v peak="${nmi_peak}" \
    'BEGIN { print (current > peak) ? current : peak }')"
  cic_peak="$(awk -v current="${cic_current}" -v peak="${cic_peak}" \
    'BEGIN { print (current > peak) ? current : peak }')"
  printf 'KPM: NMI=%s kbps CIC=%s kbps\n' "${nmi_current}" "${cic_current}"
  sleep 1
done

wait "${traffic_pid}"
cat "${traffic_log}"

# Capture the report immediately following transfer completion.
nmi_final="$(read_nmi_kpm)"
cic_final="$(read_cic_kpm)"
nmi_peak="$(awk -v current="${nmi_final}" -v peak="${nmi_peak}" \
  'BEGIN { print (current > peak) ? current : peak }')"
cic_peak="$(awk -v current="${cic_final}" -v peak="${cic_peak}" \
  'BEGIN { print (current > peak) ? current : peak }')"

printf 'Picos: NMI=%s kbps CIC=%s kbps\n' "${nmi_peak}" "${cic_peak}"
echo "Grafana: ${GRAFANA_URL}"

if awk -v nmi="${nmi_peak}" -v cic="${cic_peak}" \
  'BEGIN { exit !(nmi > 0 && cic > 0) }'; then
  echo "DEMO_KPM_MULTISITE_OK"
else
  echo "DEMO_KPM_MULTISITE_FALHOU: um dos xApps não observou throughput" >&2
  exit 1
fi

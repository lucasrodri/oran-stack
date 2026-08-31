#!/usr/bin/env bash
set -euo pipefail

# Demonstrate the kpm-load-watch algorithm with one bounded UE transfer.

RAN_NAMESPACE="${RAN_NAMESPACE:-ran}"
XAPP_NAMESPACE="${XAPP_NAMESPACE:-ricxapp}"
UE_DEPLOYMENT="${UE_DEPLOYMENT:-srsue}"
XAPP_DEPLOYMENT="${XAPP_DEPLOYMENT:-kpm-load-watch}"
TRAFFIC_URL="${TRAFFIC_URL:-https://speed.cloudflare.com/__down?bytes=50000000}"
GRAFANA_URL="${GRAFANA_URL:-http://192.168.72.10:30300/d/oran-overview/o-ran-stack-overview}"

kubectl_args=()
if [[ -n "${KUBECONFIG:-}" ]]; then
  kubectl_args+=(--kubeconfig "${KUBECONFIG}")
fi

kctl() {
  kubectl "${kubectl_args[@]}" "$@"
}

read_metrics() {
  kctl -n "${XAPP_NAMESPACE}" exec "deployment/${XAPP_DEPLOYMENT}" -c xapp -- \
    sh -c 'if command -v curl >/dev/null 2>&1; then curl -fsS http://127.0.0.1:8091/metrics; else wget -qO- http://127.0.0.1:8091/metrics; fi' \
    2>/dev/null
}

parse_state() {
  grep -E '^oran_kpm_load_watch_state\{state="[^"]+"\} 1(\.0)?$' | \
    sed -n 's/.*state="\([^"]*\)".*/\1/p'
}

parse_average() {
  awk '$1 == "oran_kpm_load_watch_average_kbps" { print $2 + 0 }'
}

interface_address="$(
  kctl -n "${RAN_NAMESPACE}" exec "deployment/${UE_DEPLOYMENT}" -c srsue -- \
    ip -brief address show tun_srsue
)"
echo "UE pronta: ${interface_address}"
echo "Grafana: ${GRAFANA_URL}"

traffic_log="$(mktemp -t oran-load-watch.XXXXXX)"
trap 'rm -f "${traffic_log}"' EXIT

kctl -n "${RAN_NAMESPACE}" exec "deployment/${UE_DEPLOYMENT}" -c srsue -- \
  curl --interface tun_srsue -L --max-time 120 -sS -o /dev/null \
  -w 'HTTP %{http_code}; %{size_download} bytes; %{speed_download} bytes/s\n' \
  "${TRAFFIC_URL}" >"${traffic_log}" &
traffic_pid=$!

seen_active=0
seen_busy=0
peak_average=0
while kill -0 "${traffic_pid}" 2>/dev/null; do
  snapshot="$(read_metrics)"
  state="$(parse_state <<<"${snapshot}")"
  average="$(parse_average <<<"${snapshot}")"
  peak_average="$(awk -v current="${average}" -v peak="${peak_average}" \
    'BEGIN { print (current > peak) ? current : peak }')"
  [[ "${state}" == active ]] && seen_active=1
  [[ "${state}" == busy ]] && seen_busy=1
  printf 'load-watch: state=%s average=%s kbps\n' "${state}" "${average}"
  sleep 1
done

wait "${traffic_pid}"
cat "${traffic_log}"

returned_idle=0
for _ in $(seq 1 24); do
  snapshot="$(read_metrics)"
  state="$(parse_state <<<"${snapshot}")"
  average="$(parse_average <<<"${snapshot}")"
  printf 'cooldown: state=%s average=%s kbps\n' "${state}" "${average}"
  if [[ "${state}" == idle ]]; then
    returned_idle=1
    break
  fi
  sleep 2
done

printf 'Resumo: active=%s busy=%s idle-final=%s pico-media=%s kbps\n' \
  "${seen_active}" "${seen_busy}" "${returned_idle}" "${peak_average}"

if (( seen_active == 1 && seen_busy == 1 && returned_idle == 1 )); then
  echo "DEMO_LOAD_WATCH_OK"
else
  echo "DEMO_LOAD_WATCH_FALHOU: o ciclo completo de estados não foi observado" >&2
  exit 1
fi

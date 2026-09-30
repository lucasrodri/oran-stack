#!/usr/bin/env bash
set -euo pipefail

if (( $# < 2 )); then
  printf 'Usage: %s <output-directory> <username> [username ...]\n' "$0" >&2
  exit 2
fi

output_dir=$1
shift

if [[ ${EUID} -eq 0 && -z ${KUBECONFIG:-} && -r /etc/kubernetes/admin.conf ]]; then
  export KUBECONFIG=/etc/kubernetes/admin.conf
fi

for command_name in kubectl openssl base64; do
  if ! command -v "${command_name}" >/dev/null; then
    printf 'Required command not found: %s\n' "${command_name}" >&2
    exit 1
  fi
done

cluster_server=$(kubectl config view --raw --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
cluster_ca=$(kubectl config view --raw --minify \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')

if [[ -z ${cluster_server} || -z ${cluster_ca} ]]; then
  printf 'The active kubeconfig must contain an API server and embedded CA data\n' >&2
  exit 1
fi

mkdir -p "${output_dir}"
chmod 0700 "${output_dir}"
work_dir=$(mktemp -d)
trap 'rm -rf -- "${work_dir}"' EXIT

for username in "$@"; do
  if [[ ! ${username} =~ ^[a-z][a-z0-9.-]{1,31}$ ]]; then
    printf 'Invalid Linux/Kubernetes username: %s\n' "${username}" >&2
    exit 2
  fi

  safe_name=${username//./-}
  csr_name="openran-student-${safe_name}"
  user_dir="${work_dir}/${safe_name}"
  mkdir -p "${user_dir}"

  openssl genrsa -out "${user_dir}/client.key" 3072 2>/dev/null
  openssl req -new \
    -key "${user_dir}/client.key" \
    -out "${user_dir}/client.csr" \
    -subj "/CN=${username}/O=openran-students"

  kubectl delete certificatesigningrequest "${csr_name}" \
    --ignore-not-found >/dev/null
  csr_data=$(base64 < "${user_dir}/client.csr" | tr -d '\n')
  kubectl apply -f - >/dev/null <<EOF
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: ${csr_name}
spec:
  request: ${csr_data}
  signerName: kubernetes.io/kube-apiserver-client
  expirationSeconds: 31536000
  usages:
    - client auth
EOF
  kubectl certificate approve "${csr_name}" >/dev/null

  for _ in {1..20}; do
    certificate_data=$(kubectl get certificatesigningrequest "${csr_name}" \
      -o jsonpath='{.status.certificate}')
    [[ -n ${certificate_data} ]] && break
    sleep 0.5
  done
  if [[ -z ${certificate_data:-} ]]; then
    printf 'Certificate was not issued for %s\n' "${username}" >&2
    exit 1
  fi

  certificate_file="${user_dir}/client.crt"
  printf '%s' "${certificate_data}" | base64 -d > "${certificate_file}"
  kubeconfig_file="${output_dir}/${username}.kubeconfig"

  KUBECONFIG="${kubeconfig_file}" kubectl config set-cluster nmi-openran \
    --server="${cluster_server}" \
    --certificate-authority=<(printf '%s' "${cluster_ca}" | base64 -d) \
    --embed-certs=true >/dev/null
  KUBECONFIG="${kubeconfig_file}" kubectl config set-credentials "${username}" \
    --client-certificate="${certificate_file}" \
    --client-key="${user_dir}/client.key" \
    --embed-certs=true >/dev/null
  KUBECONFIG="${kubeconfig_file}" kubectl config set-context student-lab \
    --cluster=nmi-openran \
    --user="${username}" \
    --namespace=student-lab >/dev/null
  KUBECONFIG="${kubeconfig_file}" kubectl config use-context student-lab >/dev/null
  chmod 0600 "${kubeconfig_file}"

  kubectl delete certificatesigningrequest "${csr_name}" >/dev/null
  printf 'Created %s\n' "${kubeconfig_file}"
done

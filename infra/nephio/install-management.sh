#!/usr/bin/env bash
set -euo pipefail

# Minimal Nephio management plane for the UnB laboratory.
# Run as root on nephio-k8s-w01 after it joins the NMI Kubernetes cluster.

KPT_VERSION="1.0.0-beta.64"
KPT_SHA256="bb157fff0e44f4e5561c00dd667ef893bbbd49b273eb6ab965b43038b052f30b"
PORCH_VERSION="1.5.7"
PORCHCTL_SHA256="61a50b7512a0accf84074e20c3d82a335b2e5b08f1ffba706bb3f712c68ebd0f"
NEPHIO_VERSION="6.0.0"
CATALOG_COMMIT="3d81f20e7a5e578e28152cb5b85841cfbae6d300"
WEBUI_IMAGE="docker.io/nephio/kpt-backstage-plugins@sha256:45937b27d1bd682cbef34c8e2b0b028399b949e06c1db71ddea70d6f5ffef9e1"

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
NEPHIO_ROOT="/opt/nephio"
CATALOG_DIR="${NEPHIO_ROOT}/catalog"
PACKAGES_DIR="${NEPHIO_ROOT}/packages"
GITEA_PASSWORD_FILE="/etc/nephio/gitea-password"
KUBECONFIG="${KUBECONFIG:-/etc/kubernetes/admin.conf}"
export KUBECONFIG

install_host_dependencies() {
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl docker-ce docker-ce-cli git jq openssl
  systemctl enable --now docker
}

install_kpt() {
  local kpt_tmp
  kpt_tmp=$(mktemp -d)
  curl -fsSL --retry 3 \
    -o "${kpt_tmp}/kpt_linux_amd64" \
    "https://github.com/kptdev/kpt/releases/download/v${KPT_VERSION}/kpt_linux_amd64"
  echo "${KPT_SHA256}  ${kpt_tmp}/kpt_linux_amd64" | sha256sum -c -
  install -m 0755 "${kpt_tmp}/kpt_linux_amd64" /usr/local/bin/kpt
  rm -r "${kpt_tmp}"
}

install_porchctl() {
  local porch_tmp
  porch_tmp=$(mktemp -d)
  curl -fsSL --retry 3 \
    -o "${porch_tmp}/porchctl.tar.gz" \
    "https://github.com/kptdev/porch/releases/download/v${PORCH_VERSION}/porchctl_${PORCH_VERSION}_linux_amd64.tar.gz"
  echo "${PORCHCTL_SHA256}  ${porch_tmp}/porchctl.tar.gz" | sha256sum -c -
  tar -xzf "${porch_tmp}/porchctl.tar.gz" -C "${porch_tmp}"
  install -m 0755 "${porch_tmp}/porchctl" /usr/local/bin/porchctl
  rm -r "${porch_tmp}"
}

checkout_catalog() {
  local catalog_marker="${PACKAGES_DIR}/.catalog-commit"
  install -d -m 0755 "${NEPHIO_ROOT}"
  if [[ ! -d "${CATALOG_DIR}/.git" ]]; then
    git clone https://github.com/nephio-project/catalog.git "${CATALOG_DIR}"
  fi
  git -C "${CATALOG_DIR}" fetch origin "${CATALOG_COMMIT}"
  git -C "${CATALOG_DIR}" checkout --detach "${CATALOG_COMMIT}"

  # Keep kpt's generated inventory between reruns. Rebuild the working copy
  # only when the pinned catalog revision changes.
  if [[ ! -f "${catalog_marker}" ]] || \
     [[ "$(< "${catalog_marker}")" != "${CATALOG_COMMIT}" ]]; then
    if [[ -d "${PACKAGES_DIR}" ]]; then
      rm -r "${PACKAGES_DIR}"
    fi
    install -d -m 0755 "${PACKAGES_DIR}"
    cp -a "${CATALOG_DIR}/distros/sandbox/gitea" "${PACKAGES_DIR}/gitea"
    cp -a "${CATALOG_DIR}/nephio/core/porch" "${PACKAGES_DIR}/porch"
    cp -a "${CATALOG_DIR}/nephio/core/nephio-operator" "${PACKAGES_DIR}/nephio-operator"
    cp -a "${CATALOG_DIR}/nephio/optional/resource-backend/crd" \
      "${PACKAGES_DIR}/resource-backend-crd"
    cp -a "${CATALOG_DIR}/nephio/optional/fluxcd" "${PACKAGES_DIR}/fluxcd"
    cp -a "${CATALOG_DIR}/nephio/optional/webui" "${PACKAGES_DIR}/webui"
    printf '%s\n' "${CATALOG_COMMIT}" > "${catalog_marker}"
  fi
}

configure_credentials() {
  local gitea_password gitea_password_b64
  install -d -m 0700 /etc/nephio
  if [[ ! -f "${GITEA_PASSWORD_FILE}" ]]; then
    umask 077
    openssl rand -hex 24 > "${GITEA_PASSWORD_FILE}"
  fi
  chmod 0600 "${GITEA_PASSWORD_FILE}"
  gitea_password=$(tr -d '\n' < "${GITEA_PASSWORD_FILE}")
  gitea_password_b64=$(printf '%s' "${gitea_password}" | base64 -w 0)

  sed -i "s/password: secret/password: ${gitea_password}/" \
    "${PACKAGES_DIR}/gitea/secret-git-user.yaml"
  sed -i "s/PASSWD=secret/PASSWD=${gitea_password}/" \
    "${PACKAGES_DIR}/gitea/secret-gitea-inline-config.yaml"
  sed -i "s/c2VjcmV0/${gitea_password_b64}/g" \
    "${PACKAGES_DIR}/gitea/secret-postgresql.yaml"

  unset gitea_password gitea_password_b64
}

configure_private_services() {
  sed -i 's/type: LoadBalancer/type: ClusterIP/' \
    "${PACKAGES_DIR}/gitea/service-gitea.yaml" \
    "${PACKAGES_DIR}/webui/service.yaml"
}

configure_nephio_operator() {
  local operator_dir="${PACKAGES_DIR}/nephio-operator/app/controller"
  sed -i \
    "s#docker.io/nephio/nephio-operator:latest#docker.io/nephio/nephio-operator:v${NEPHIO_VERSION}#g" \
    "${operator_dir}/deployment-controller.yaml" \
    "${operator_dir}/deployment-token-controller.yaml"
  sed -i \
    's#http://172.18.0.200:3000#http://gitea.gitea.svc.cluster.local:3000#g' \
    "${operator_dir}/deployment-controller.yaml" \
    "${operator_dir}/deployment-token-controller.yaml"
}

configure_webui() {
  local webui_dir="${PACKAGES_DIR}/webui"
  sed -i \
    "s#docker.io/nephio/gen-configmap-fn:latest#docker.io/nephio/gen-configmap-fn:v${NEPHIO_VERSION}#" \
    "${webui_dir}/Kptfile"
  sed -i \
    "s#nephio/kpt-backstage-plugins:latest#${WEBUI_IMAGE}#" \
    "${webui_dir}/deployment.yaml"

  cat > "${webui_dir}/cluster-role.yaml" <<'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: nephio-webui-packages
rules:
  - apiGroups: ["config.porch.kpt.dev", "porch.kpt.dev"]
    resources: ["*"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["get", "list", "watch"]
EOF
  sed -i 's/name: cluster-admin/name: nephio-webui-packages/' \
    "${webui_dir}/cluster-role-binding.yaml"
  sed -i 's/apiGroup: ""/apiGroup: rbac.authorization.k8s.io/' \
    "${webui_dir}/cluster-role-binding.yaml"
}

configure_workload_placement() {
  local package_dir
  local package_dirs=(
    "${PACKAGES_DIR}/gitea"
    "${PACKAGES_DIR}/porch"
    "${PACKAGES_DIR}/nephio-operator/app"
    "${PACKAGES_DIR}/fluxcd"
    "${PACKAGES_DIR}/webui"
  )

  for package_dir in "${package_dirs[@]}"; do
    kpt fn eval "${package_dir}" \
      --image ghcr.io/kptdev/krm-functions-catalog/starlark:v0.5.2 \
      --fn-config "${SCRIPT_DIR}/placement-starlark.yaml"
  done
}

apply_kpt_package() {
  local package_dir="$1"
  if ! grep -q '^inventory:' "${package_dir}/Kptfile"; then
    kpt live init "${package_dir}"
  fi
  # Event output prints each transition once; table output redraws the entire
  # resource tree every second and produces enormous CI/terminal logs.
  kpt live apply "${package_dir}" --reconcile-timeout=15m --output=events
}

deploy_components() {
  apply_kpt_package "${PACKAGES_DIR}/gitea"
  kubectl wait pods --all -n gitea --for=condition=Ready --timeout=10m

  apply_kpt_package "${PACKAGES_DIR}/porch"
  kubectl wait pods --all -n porch-system --for=condition=Ready --timeout=10m

  kubectl apply -f "${PACKAGES_DIR}/nephio-operator/namespace.yaml"
  apply_kpt_package "${PACKAGES_DIR}/nephio-operator/crd"
  # The Nephio network controller watches these inventory/IPAM/VLAN kinds.
  # Only their CRDs are required for the minimal lab; the optional backend is
  # deliberately not installed.
  apply_kpt_package "${PACKAGES_DIR}/resource-backend-crd"
  kubectl get secret git-user-secret -n gitea -o json | \
    jq 'del(.metadata.creationTimestamp,.metadata.resourceVersion,.metadata.uid) | .metadata.namespace="nephio-system"' | \
    kubectl apply -f -
  apply_kpt_package "${PACKAGES_DIR}/nephio-operator/app"
  kubectl wait pods --all -n nephio-system --for=condition=Ready --timeout=10m

  apply_kpt_package "${PACKAGES_DIR}/fluxcd"
  kubectl wait pods --all -n flux-system --for=condition=Ready --timeout=10m

  kpt fn render "${PACKAGES_DIR}/webui"
  apply_kpt_package "${PACKAGES_DIR}/webui"
  kubectl wait pods --all -n nephio-webui --for=condition=Ready --timeout=10m

  # R6 WebUI assumes every YAML document has metadata. Kustomization files do
  # not require it, so keep the upstream image immutable and patch its static
  # bundle in an init container until the upstream guard is available.
  kubectl apply -f "${SCRIPT_DIR}/webui-compat/patch-configmap.yaml"
  kubectl patch deployment nephio-webui \
    --namespace=nephio-webui \
    --type=strategic \
    --patch-file="${SCRIPT_DIR}/webui-compat/deployment-patch.yaml"
  kubectl rollout status deployment/nephio-webui \
    --namespace=nephio-webui \
    --timeout=10m
}

validate_installation() {
  kpt version
  porchctl version
  kubectl get pods -n gitea
  kubectl get pods -n porch-system
  kubectl get pods -n nephio-system
  kubectl get pods -n flux-system
  kubectl get pods -n nephio-webui
  kubectl get repositories.config.porch.kpt.dev 2>/dev/null || true
}

install_host_dependencies
install_kpt
install_porchctl
checkout_catalog
configure_credentials
configure_private_services
configure_nephio_operator
configure_webui
configure_workload_placement
deploy_components
validate_installation

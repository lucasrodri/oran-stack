#!/usr/bin/env bash
set -euo pipefail

# The worker must follow the control-plane minor version. Upgrade the cluster
# one minor at a time before changing this value.
KUBERNETES_MINOR="${KUBERNETES_MINOR:-1.30}"

sudo swapoff -a
sudo sed -ri '/\sswap\s/s/^#?/#/' /etc/fstab

sudo modprobe overlay
sudo modprobe br_netfilter
printf '%s\n' overlay br_netfilter | sudo tee /etc/modules-load.d/k8s.conf >/dev/null
printf '%s\n' \
  'net.bridge.bridge-nf-call-iptables = 1' \
  'net.bridge.bridge-nf-call-ip6tables = 1' \
  'net.ipv4.ip_forward = 1' | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf >/dev/null
sudo sysctl --system >/dev/null

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl gpg containerd openvswitch-switch

sudo install -d -m 0755 /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml >/dev/null
sudo sed -ri 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl enable --now containerd openvswitch-switch

curl -fsSL "https://pkgs.k8s.io/core:/stable:/v${KUBERNETES_MINOR}/deb/Release.key" \
  -o /tmp/kubernetes-release.key
sudo install -d -m 0755 /etc/apt/keyrings
sudo gpg --dearmor --yes -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg \
  /tmp/kubernetes-release.key
printf 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v%s/deb/ /\n' \
  "${KUBERNETES_MINOR}" | sudo tee /etc/apt/sources.list.d/kubernetes.list >/dev/null

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
sudo systemctl enable kubelet

kubeadm version -o short
containerd --version

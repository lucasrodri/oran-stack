#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 8 ]]; then
  echo "usage: $0 VMID NAME MEMORY_MB CORES DISK_SIZE IP_CIDR GATEWAY SSH_PUBLIC_KEY_FILE" >&2
  exit 2
fi

vmid="$1"
vm_name="$2"
memory_mb="$3"
cores="$4"
disk_size="$5"
ip_cidr="$6"
gateway="$7"
ssh_public_key_file="$8"

image_url="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2"
image_path="/var/lib/vz/template/iso/debian-12-genericcloud-amd64.qcow2"
storage="local-lvm"
bridge="vmbr2"

if qm config "$vmid" >/dev/null 2>&1; then
  echo "VM $vmid already exists; refusing to overwrite it" >&2
  exit 1
fi

if [[ ! -s "$ssh_public_key_file" ]]; then
  echo "SSH public key not found: $ssh_public_key_file" >&2
  exit 1
fi

if [[ ! -s "$image_path" ]]; then
  curl -fL --retry 3 -o "$image_path" "$image_url"
fi

qm create "$vmid" \
  --name "$vm_name" \
  --memory "$memory_mb" \
  --balloon 0 \
  --cores "$cores" \
  --cpu host \
  --ostype l26 \
  --agent enabled=1 \
  --net0 "virtio,bridge=${bridge},firewall=1" \
  --tags "kubernetes;openran;worker"

qm importdisk "$vmid" "$image_path" "$storage" --format raw
qm set "$vmid" --scsihw virtio-scsi-single
qm set "$vmid" --scsi0 "${storage}:vm-${vmid}-disk-0,discard=on,iothread=1,ssd=1"
qm resize "$vmid" scsi0 "$disk_size"
qm set "$vmid" --ide2 "${storage}:cloudinit"
qm set "$vmid" --boot order=scsi0
qm set "$vmid" --serial0 socket --vga serial0
qm set "$vmid" --ciuser "${CLOUD_INIT_USER:-aluno}"
qm set "$vmid" --sshkeys "$ssh_public_key_file"
qm set "$vmid" --ipconfig0 "ip=${ip_cidr},gw=${gateway}"
qm set "$vmid" --nameserver "$gateway"
qm set "$vmid" --searchdomain nmi
qm set "$vmid" --onboot 1
qm start "$vmid"

qm config "$vmid"

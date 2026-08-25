# NMI single-node deployment

Last verified: 2026-08-25

## Infrastructure

| Item | Value |
|---|---|
| Proxmox node | `proxmox002` |
| VM ID / name | `105` / `oran-k8s-01` |
| Management IP | `192.168.72.10/24` |
| Gateway | `192.168.72.1` |
| Resources | 12 vCPU, 24 GiB RAM, 64 GiB disk |
| OS | Debian 12 |
| Kubernetes | kubeadm 1.30.14, single control-plane/worker node |
| CNI | Flannel + Multus + OVS-CNI |

The single node intentionally runs both the control plane and workloads. This is
appropriate for the NMI laboratory deployment; additional workers can be joined
later without changing the namespace, service, or pod communication model.

## Verified state

- Kubernetes node is `Ready`.
- The `5g-core` Helm release is deployed; MongoDB and all Open5GS NFs are running.
- The `near-rt-ric` Helm release revision 9 is deployed with DBAAS, E2 Manager,
  E2 Termination, Subscription Manager, Application Manager, Routing Manager,
  and A1 Mediator running.
- The `ran` release is deployed; CU, DU, and srsUE pods are running.
- N2 NG Setup and F1 Setup complete successfully.
- CU and DU appear as `CONNECTED` in the e2mgr `/v1/nodeb/states` endpoint.
- CU logs contain `E2 Setup procedure successful`.

The srsUE completes random access, RRC connection, registration, and PDU session
establishment. It receives `10.45.0.2` on `tun_srsue`; the UPF creates the
matching `internet` session and `ping 10.45.0.1` through the simulated radio path
succeeds. SMF↔UPF PFCP uses direct pod identities through a headless UPF Service.
The lab profile keeps the RRC bearer for up to 7200 seconds of inactivity so the
simulated UE remains testable during long observation sessions.

Internet egress from the UE subnet is not yet part of the chart. Reaching the UPF
gateway proves the end-to-end radio/GTP-U user plane; external egress additionally
requires forwarding and source NAT policy for `10.45.0.0/16`.

## O-RAN SC image supply

The O-RAN SC Nexus Docker endpoints return HTTP `402 Invalid license` from the
NMI environment. The fork therefore rebuilds the pinned official M-release
sources in GitHub Actions and publishes public `linux/amd64` images to
`ghcr.io/lucasrodri/oran-stack`:

- `ric-plt-appmgr:0.5.10`
- `ric-plt-dbaas:0.6.5`
- `ric-plt-e2:6.0.8`
- `ric-plt-e2mgr:6.0.8`
- `ric-plt-submgr:0.10.4`
- `ric-plt-rtmgr:0.9.7`
- `ric-plt-a1:3.2.3`

The exact upstream commits and reproducible workflow are documented in
`docs/RIC_IMAGES.md`. A clean installation no longer depends on the old VM's
containerd cache or on access to Nexus.

RTMgr and A1 Mediator are enabled. RTMgr successfully pushes a 31-entry route
table to A1 on its RMR data endpoint. The A1 Service must expose both the RMR
route-management port `4561` and data port `4562`; RTMgr opens its management
wormhole on `4561` regardless of the data port declared in PlatformComponents.

## Useful checks

Run these on `oran-k8s-01`:

```bash
sudo kubectl get nodes -o wide
sudo kubectl get pods -A
helm list -A

sudo kubectl run e2-state --rm -i --restart=Never \
  --image=busybox:1.36 -n near-rt-ric -- \
  wget -qO- http://ric-e2mgr:3800/v1/nodeb/states

sudo kubectl logs -n ran deployment/ocudu-cu -c ocudu-cu | \
  grep 'E2 Setup procedure successful'
sudo kubectl logs -n ran deployment/srsue -c srsue -f

sudo kubectl exec -n ran deployment/srsue -- \
  ip -brief address show tun_srsue
sudo kubectl exec -n ran deployment/srsue -- \
  ping -I tun_srsue -c 3 10.45.0.1

sudo kubectl exec -n near-rt-ric deployment/ric-a1mediator -- \
  wget -qO- http://localhost:10000/A1-P/v2/healthcheck
sudo kubectl logs -n near-rt-ric deployment/ric-rtmgr | \
  grep 'ric-a1mediator:4562 successful'
```

## Restore points

Proxmox snapshots created during provisioning:

- `pre-k8s`: generalized Debian VM before Kubernetes.
- `k8s-ready`: healthy Kubernetes/CNI/OVS base before application deployment.
- `pre-ric-m-20260825`: complete VM before the O-RAN SC M-release image upgrade.

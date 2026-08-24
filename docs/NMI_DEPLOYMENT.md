# NMI single-node deployment

Last verified: 2026-08-24

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
- The `near-rt-ric` release is deployed with DBAAS, E2 Manager, E2 Termination,
  Subscription Manager, and Application Manager running.
- The `ran` release is deployed; CU, DU, and srsUE pods are running.
- N2 NG Setup and F1 Setup complete successfully.
- CU and DU appear as `CONNECTED` in the e2mgr `/v1/nodeb/states` endpoint.
- CU logs contain `E2 Setup procedure successful`.

The srsUE process reaches `NAS5G Switching on` but does not yet reach `RRC
Connected` or `PDU Session Established`. This is the existing P3/ZMQ cell-search
issue documented in `docs/STATUS.md`, not a Kubernetes scheduling or pod-health
failure.

## O-RAN SC image-registry workaround

On 2026-08-24 all O-RAN SC Nexus Docker endpoints (`10001`, `10002`, and
`10004`) returned HTTP `402 Invalid license`. Five compatible I/J-release images
were recovered from the existing `vm-ric` containerd cache and imported into the
new node:

- `ric-plt-appmgr:0.5.7`
- `ric-plt-dbaas:0.6.4`
- `ric-plt-e2:6.0.6`
- `ric-plt-e2mgr:6.0.4`
- `ric-plt-submgr:0.10.1`

Their Helm pull policy is `IfNotPresent`, so the deployment uses the local cache.
Do not prune these images until they have been mirrored into a registry controlled
by NMI.

The official RTMgr and A1Mediator images were not present in that cache. For the
base E2 path, A1Mediator is disabled and a deliberately limited HTTP acknowledgement
stub is used for the E2T registration callback. RMR traffic uses the chart's static
seed routes. This supports E2 Setup and node registration, but it does **not**
provide RTMgr's dynamic xApp route management. Deploy the simple-mon xApp only
after a full RTMgr image is rebuilt or mirrored and `rtmgr.enabled` is restored.

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
```

## Restore points

Proxmox snapshots created during provisioning:

- `pre-k8s`: generalized Debian VM before Kubernetes.
- `k8s-ready`: healthy Kubernetes/CNI/OVS base before application deployment.

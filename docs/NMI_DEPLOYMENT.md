# NMI five-node deployment

Last verified: 2026-08-30

## Infrastructure

| Item | Value |
|---|---|
| Proxmox control plane | `proxmox002`, VM `105` / `oran-k8s-01` |
| Control-plane IP | `192.168.72.10/24` via `192.168.72.1` |
| Control-plane resources | 12 vCPU, 24 GiB RAM, 64 GiB disk, Debian 12 |
| Proxmox001 worker | VM `111` / `oran-k8s-w01`, `192.168.71.20`, 8 vCPU, 12 GiB RAM, 48 GiB disk |
| Proxmox002 worker | VM `112` / `oran-k8s-w02`, `192.168.72.20`, 4 vCPU, 8 GiB RAM, 32 GiB disk |
| Nephio worker | Proxmox001 VM `113` / `nephio-k8s-w01`, `192.168.71.30`, Ubuntu 22.04, 8 vCPU, 8 GiB RAM, 80 GB disk |
| Observability worker | `nmi-srv03`, `164.41.240.13`, Ubuntu 24.04 |
| Inter-network routes | `.71.0/24 via 164.41.240.21`; `.72.0/24 via 164.41.240.22` on `nmi-srv03` |
| Firewall policy | pfSense1/2 allow `164.41.240.13` only to workers `.71.20`/`.72.20`; pfSense2 also allows the control plane `.72.10` |
| Kubernetes | kubeadm 1.30.14, one control plane plus four workers |
| CNI | Flannel + Multus + OVS-CNI |

The SCTP/ZMQ-sensitive RAN, 5G core, and E2Term remain on `oran-k8s-01`.
`r4-simple-mon` runs on `oran-k8s-w02`, while Prometheus, Grafana, Alertmanager,
Loki, the Prometheus Operator, and kube-state-metrics run on `nmi-srv03`; Alloy
runs on all five nodes. The physical observability
worker is selected with `workload=observability` and protected by the
`workload=observability:NoSchedule` taint. `oran-k8s-w01` is a general worker and
has passed scheduling, DNS, Flannel, Multus, and OVS-CNI tests.

VM 113 is labeled `workload=nephio`. Gitea, Porch, Nephio controllers, Flux and
the WebUI run in dedicated namespaces on the same NMI cluster and select this
worker. The smoke Flux identity is restricted to ConfigMaps in `nephio-lab`.
The separate `r4-simple-mon-deployer` identity manages only the xApp resources
in `ricxapp`; RAN, Near-RT RIC and 5G Core remain under Helm/Ansible ownership.

The three VM nodes have `n2br`, `f1cbr`, and `e2br` OVS bridges and a VXLAN full
mesh protected by RSTP. Secondary-network traffic is verified across
Proxmox001 and Proxmox002 with 0% packet loss. Both pfSense instances use Hybrid
Outbound NAT with narrowly scoped NO-NAT and WAN pass rules for UDP/4789 between
`192.168.71.0/24` and `192.168.72.0/24`. `Block private networks` is disabled on
these inter-router WAN interfaces; the default-deny policy and bogon protection
remain active.

## Verified state

- All five Kubernetes nodes are `Ready`.
- The complete observability control plane runs on `nmi-srv03`.
- Prometheus, Grafana, Alertmanager, and Loki use bound PVCs. Prometheus retains
  seven days of metrics; Loki retains only 24 hours of logs from the stack
  namespaces, appropriate for this disposable test environment.
- The `5g-core` Helm release is deployed; MongoDB and all Open5GS NFs are running.
- The `near-rt-ric` Helm release revision 9 is deployed with DBAAS, E2 Manager,
  E2 Termination, Subscription Manager, Application Manager, Routing Manager,
  and A1 Mediator running.
- The `ran` release is deployed; CU, DU, and srsUE pods are running.
- The `r4-simple-mon` xApp is managed by Porch/Flux, scheduled on
  `oran-k8s-w02`, and receives KPM indications across the Flannel overlay
  without restarting E2Term. Deploy, update and forward rollback were validated.
- N2 NG Setup and F1 Setup complete successfully.
- CU and DU appear as `CONNECTED` in the e2mgr `/v1/nodeb/states` endpoint.
- CU logs contain `E2 Setup procedure successful`.

The srsUE completes random access, RRC connection, registration, and PDU session
establishment. It receives an address from `10.45.0.0/24` on `tun_srsue`; the UPF creates the
matching `internet` session and `ping 10.45.0.1` through the simulated radio path
succeeds. SMF↔UPF PFCP uses direct pod identities through a headless UPF Service.
The lab profile keeps the RRC bearer for up to 7200 seconds of inactivity so the
simulated UE remains testable during long observation sessions.

Internet egress is also validated. The UPF entrypoint enables forwarding and
installs idempotent filter/NAT rules for `10.45.0.0/16`; a request made with
`curl --interface tun_srsue` reaches an external HTTP endpoint.

The `r4-simple-mon` xApp discovers the connected E2 node dynamically and
subscribes to O-DU KPM metric `DRB.UEThpDl` (report style 1). Its AppMgr
registration declares the official RMR message contract, including
`RIC_INDICATION`. This is required by RTMgr 0.9.7 so full `newrt` refreshes retain
the subscription-specific `mse|12050|<id>|...` route. No periodic route re-POST
workaround is used. The xApp exposes `/metrics`; Grafana's overview dashboard
shows the decoded KPM indication rate and the live `DRB.UEThpDl` throughput.
Prometheus stores both the delivery counters and the decoded KPI as
`oran_kpm_drb_ue_throughput_dl_kbps`. The DU explicitly enables RLC metrics:
OCUDU 26.04 derives this KPM from RLC byte counters, while its default
`enable_rlc: false` produces a valid but permanently zero report.

### Demonstrate UE traffic in the KPM dashboard

With the NMI VPN connected, open the **UE Downlink Throughput — E2SM-KPM** panel
at `http://192.168.72.10:30300/d/oran-overview/o-ran-stack-overview`. On VM 105,
run:

```bash
cd /home/lucasrc/oran-stack-main
./scripts/demo-kpm.sh
```

The script downloads a bounded 50 MB test file through `tun_srsue`, polls the
xApp's Prometheus endpoint once per second, and prints the current and peak KPM
values. Its duration intentionally crosses Prometheus's 15-second scrape interval
so the non-zero KPI is also visible in Grafana.
The expected result is HTTP 200, at least one `DRB.UEThpDl` sample above zero,
and `DEMO_KPM_OK`. No RAN control action is sent: this is observation only.

## Access from the NMI VPN

The lab is operated through the institutional NMI VPN. Tailscale may remain as
an out-of-band maintenance path, but it is not part of the deployment topology.
Grafana runs on the observability worker and is published through a Kubernetes
NodePort. The supported entry point is the private control-plane address, reached
while connected to the NMI VPN; kube-proxy forwards it to the physical worker:

- URL: `http://192.168.72.10:30300`
- Alertmanager: `http://192.168.72.10:30301`
- Lab credentials: `admin` / `oran-lab`

The service is not intended to be exposed to the public Internet; the NMI
perimeter/VPN remains the access boundary.

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
sudo kubectl get gitrepository,kustomization -n flux-system
sudo kubectl get packagerevision -n default

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
sudo kubectl exec -n ran deployment/srsue -- \
  curl --interface tun_srsue -fsS -o /dev/null http://example.com

sudo kubectl logs -n ricxapp deployment/r4-simple-mon | \
  grep 'RIC Indication Received'

sudo kubectl exec -n near-rt-ric deployment/ric-a1mediator -- \
  wget -qO- http://localhost:10000/A1-P/v2/healthcheck
sudo kubectl logs -n near-rt-ric deployment/ric-rtmgr | \
  grep 'ric-a1mediator:4562 successful'
```

On `nmi-srv03`, `infra/nmi-srv03/bootstrap-k8s-worker.sh` prepares the node and
`infra/nmi-srv03/99-openran-route.yaml` persists the route to the VM network.

## Restore points

Proxmox snapshots created during provisioning:

- `pre-k8s`: generalized Debian VM before Kubernetes.
- `k8s-ready`: healthy Kubernetes/CNI/OVS base before application deployment.
- `pre-ric-m-20260825`: complete VM before the O-RAN SC M-release image upgrade.

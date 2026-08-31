# O-RAN Lab Stack — Status

_Last updated: 2026-08-30_

---

## 0. Recent Changes

### 2026-08-30 — repeatable student xApp laboratory added

- Built and verified the corrected student-lab image for both architectures at
  `ghcr.io/lucasrodri/oran-stack/oran-xapps@sha256:fd9aab365046bb666061db157520ae8552a3912072ae1da75385ec1b1dd65878`.
- Added `scripts/new-kpm-xapp.sh`, which creates a bounded-log E2SM-KPM Python
  entry point, reusable Nephio blueprint, NMI `PackageVariant` and restricted
  Flux delivery identity from one DNS-safe xApp name.
- Added generic Porch helpers to publish any generated Team Blueprint and move
  the downstream package through `Draft -> Proposed -> Published`.
- Added CI validation for the generated contract before the shared
  multi-architecture xApp image is built.
- Generalized NMI ServiceMonitor discovery and Grafana KPM legends so multiple
  student xApps can be compared by Kubernetes Service without editing the
  monitoring chart for each experiment.
- Made the KPM report period a workload parameter. Concurrent xApps requesting
  the same metric use distinct periods so SubMgr does not merge them into one
  E2 subscription and one RMR subscription ID.
- Started a clean `r4-simple-mon-nmi-v5` downstream lineage because Porch's
  three-way upgrade correctly refused to invent env fields absent from the
  original `blueprint-v1` NMI package.
- Documented the complete student path in `docs/STUDENT_XAPP_LAB.md`, including
  real KPM acceptance, UE egress traffic, update and forward rollback.

### 2026-08-30 — simple-mon ARM64 delivered to CIC with real KPM

- Built and verified the multi-architecture xApp image at
  `ghcr.io/lucasrodri/oran-stack/oran-xapps@sha256:dd52cb4bc7508357d0407d1a977850a27fab932155fd589e1fe36676ec8fd0f9`.
  The container runs natively as `aarch64` on `cic-k8s-w01`; the RIC, RAN,
  Open5GS and UE remain on the validated NMI `amd64` cluster.
- Fixed undefined signed-overflow behavior in the RMR 4.9.4 symbol-table hash
  which caused the route collector to crash only on ARM64. Dynamic RMR routing
  now remains enabled with `RMR_FLAGS=0`.
- Published `cic.r4-simple-mon-cic-arm64.packagevariant-3` from the shared
  `team-blueprints/r4-simple-mon.v4` blueprint. CIC Flux reconciled Git revision
  `fbad22adb6eaaaea2845171a33fec1affd2d349c` and kept the xApp Ready.
- Added bidirectional, private RMR bridges: NMI canonical xApp ports
  `4561/8091` map to CIC NodePorts `30611/30691`, and the CIC
  `ric-rtmgr.near-rt-ric:4560` bridge maps back to NMI NodePort `30460`.
- RTMgr accepted the remote route table, AppMgr listed `r4-simple-mon-cic`, and
  the ARM xApp established one active subscription and received real E2SM-KPM
  indications. The acceptance sample reached 401 indications; E2Term retained
  UID `87985448-eafa-43fa-a605-9005256c1372` with zero restarts.
- Prometheus now scrapes the `cic-simple-mon` job through the log-free relay;
  Grafana dashboard `O-RAN Multi-Site Lab` displays CIC subscription and KPM
  rate alongside the existing NMI telemetry.

### 2026-08-30 — Nephio blueprint and CIC workload GitOps validated

- Published `team-blueprints/r4-simple-mon` as a reusable Porch package and
  created the NMI deployment package through a real `PackageVariant` backed by
  `WorkloadCluster/nmi`. Flux now consumes a specialized NMI downstream package,
  not the source blueprint; its current clean lineage is `r4-simple-mon-nmi-v5`.
- Patched the pinned Nephio WebUI frontend at startup to ignore valid non-KRM
  YAML documents instead of crashing on a missing `metadata.name`.
- Registered `WorkloadCluster/cic`, created its Porch/Gitea deployment
  repository and exposed Gitea only to routed lab networks at NMI NodePort
  `30302`; no public pfSense publication was added.
- Installed only Flux v2.7.5 source and kustomize controllers on the CIC ARM64
  cluster. Published `cic.cic-lab-smoke.v1`; CIC reconciled Git commit
  `1f3c994c` and created the expected `site=cic`, `architecture=arm64` ConfigMap.
- Restricted the CIC Flux identity to ConfigMaps in `nephio-lab`. The complete
  Nephio management plane remains in NMI; CIC did not receive a duplicate
  Nephio installation.

### 2026-08-30 — simple-mon deployed and rolled back through Nephio

- Packaged the complete `r4-simple-mon` contract for Porch/Flux: digest-pinned
  image, Deployment, RMR/HTTP Services, NMI placement and byte-identical
  `xAppBase.py` runtime override.
- Published `nmi.r4-simple-mon.v1`; Flux adopted the live xApp with a dedicated
  identity restricted to `ricxapp`. Secrets and RAN updates remain denied.
- Archived the ten Helm release Secrets root-only and removed them without
  deleting Kubernetes resources. NMI Ansible now skips Helm ownership of the
  xApp, preventing two reconcilers from fighting over the same Deployment.
- Demonstrated v2 update (`state=tuned`, Git `0f2773a`) and a forward rollback
  copied from v1 (`state=baseline`, Git `ca9e3ee`). Both rollouts became Flux
  Ready and received real E2SM-KPM indications; that demonstration ended on
  subscription ID 47 before the later PackageVariant rollout.
- Added bounded scripts for baseline publication, first-adoption RMR
  stabilization, functional verification, and repeatable update/rollback.

### 2026-08-30 — Nephio R6 integrated into the NMI cluster

- Reused VM `113` as Ubuntu worker `nephio-k8s-w01` (`192.168.71.30`) on
  Proxmox001 with 8 vCPU, 8 GiB RAM and 80 GB disk. The former standalone
  Kubernetes cluster was reset, downgraded from 1.32 to `v1.30.14`, and joined
  to the existing NMI control plane as its fifth node.
- Installed pinned Nephio R6 components in NMI namespaces: Gitea, Porch
  `v1.5.7`, Nephio operator `v6.0.0`, kpt `v1.0.0-beta.64`, WebUI and Flux.
  Main Deployments and StatefulSets select `workload=nephio` and run on VM 113.
- Kept the WebUI private as a ClusterIP service. Its access uses an SSH tunnel
  over the NMI VPN and its service account cannot read Secrets. Gitea retained
  its ClusterIP and later gained a separate lab-routed NodePort for CIC Flux.
- Published Porch package revision `nmi.nmi-lab-smoke.v1` through
  `Draft -> Proposed -> Published`; Flux reconciled Git commit `e7e3352` and
  created `nephio-lab/nephio-delivery-smoke`.
- Restricted the Flux delivery identity to ConfigMaps in `nephio-lab`.
  Authorization checks denied Secrets and RAN Deployment updates. Core, RIC,
  RAN, UE and `r4-simple-mon` remained healthy and on their original nodes.
- Added reproduction, access and architecture notes in
  `docs/NEPHIO_MANAGEMENT_CLUSTER.md`.

### 2026-08-30 — CIC ARM64 metrics integrated into NMI Grafana

- Deployed node-exporter `v1.12.1` on both CIC ARM nodes and
  kube-state-metrics `v2.16.0` on `cic-k8s-w01`; all images ran natively as
  `arm64` and all three endpoints returned HTTP 200 from NMI VM 105.
- Added a stateless HAProxy `3.4.4-alpine` relay pinned to VM 105 because the
  physical Prometheus node has no direct route to `192.168.0.0/24`. The relay
  uses TCP mode, stores no metric data or access logs, and avoids a broad new
  pfSense rule.
- Added labeled Prometheus scrape jobs (`cluster=cic-arm`, `site=cic`,
  `architecture=arm64`), CIC target/node/crash-loop alerts, and the Grafana
  dashboard `O-RAN Multi-Site Lab` for NMI/CIC node, Pod, CPU and memory views.

### 2026-08-30 — CIC ARM64 two-host Kubernetes cluster validated

- Created VM `120` (`cic-k8s-cp01`, `192.168.0.210`) on Ampere 2 and VM `121`
  (`cic-k8s-w01`, `192.168.0.211`) on Ampere 3, each with 8 vCPU, 16 GiB RAM
  and 100 GB disk.
- Bootstrapped a two-node Kubernetes `v1.32.13` ARM64 cluster using the new
  `cic-arm.ini` inventory. CIC uses dedicated Pod and Service ranges
  (`10.246.0.0/16` and `10.97.0.0/16`) and remains reachable from NMI.
- Installed Flannel, Multus, OVS-CNI, local-path storage and the `n2br`,
  `f1cbr`, `e2br` inter-host VXLAN mesh. OVS-CNI is available on both the
  tainted control plane and worker.
- Validated an `aarch64` workload on Ampere 3, HTTP from Ampere 2 to the remote
  Pod and Service, and bidirectional E2 secondary-network traffic between
  `10.200.3.250` and `.251` with 0% packet loss.
- Hardened provisioning by installing `cri-tools`, asserting the requested
  Kubernetes minor, honoring custom Flannel Pod CIDRs, applying CNAO workload
  tolerations, and cleaning stale CNI interfaces during teardown.
- Detailed topology and reproduction steps are in `docs/CIC_ARM_CLUSTER.md`.

### 2026-08-30 — Persistent observability and bounded lab logging

- Added persistent Prometheus, Grafana, Alertmanager and Loki storage on the
  physical `nmi-srv03` observability worker, plus an Alloy collector on every
  Kubernetes node.
- Added the `O-RAN Kubernetes Logs` dashboard and alerts for nodes, crash loops,
  E2Term, xApp, UE, stale KPM, RMR errors and monitoring storage.
- Restricted log collection to the five stack namespaces and Loki retention to
  24 hours. Routine scrape/KPM/RLC success lines are dropped before storage.
  RAN and srsUE normal operation now logs at `warning`; the UE no longer emits
  thousands of PHY/FAPI lines per minute.
- Added the missing persistent route from `nmi-srv03` to `192.168.71.0/24` and
  restricted pfSense WAN rules to both Kubernetes workers, restoring complete
  Prometheus/Alloy reachability across the four-node Flannel network.
- Fixed an RMR receive hot loop in `r4-simple-mon` by yielding after normal
  receive timeouts. E2Term delivery, decoded KPM metrics, UE PDU session and
  Internet egress were revalidated.

### 2026-08-30 — Inter-Proxmox overlay and KPM recovery validated

- Applied Hybrid Outbound NAT and restricted WAN rules on both pfSense routers
  so UDP/4789 crosses `.71` ↔ `.72` without source NAT; disabled private-network
  blocking only on the two inter-router WANs and retained bogon/default-deny
  protection.
- Enabled RSTP on every `n2br`, `f1cbr`, and `e2br` bridge. Bidirectional Multus
  tests across Proxmox001 and Proxmox002 passed on all three networks with 0%
  packet loss.
- Made xApp startup require the selected E2 node to be `CONNECTED`, fixed the NMI
  inventory precedence so `r4-simple-mon` stays on `oran-k8s-w02`, and changed
  the RMR receive loop to allocate a fresh message buffer per timed receive.
- Recovered E2, ZMQ, and the UE in a controlled sequence. The final 10 MB HTTP
  demo through `tun_srsue` returned HTTP 200 and produced a
  `DRB.UEThpDl` peak of 28,841 kbps in the xApp/Prometheus path.

### 2026-08-29 — NMI Kubernetes workers on both Proxmox servers

- Provisioned Debian 12 VM `111` (`oran-k8s-w01`, `192.168.71.20`) on
  Proxmox001 and VM `112` (`oran-k8s-w02`, `192.168.72.20`) on Proxmox002.
- Joined both workers to kubeadm 1.30.14 and validated Flannel pod traffic,
  cluster DNS, Multus, OVS-CNI, SCTP initialization, and node-exporter.
- Expanded Multus and the `n2br`/`f1cbr`/`e2br` OVS VXLAN mesh to the VM nodes.
  Hybrid NO-NAT plus restricted WAN rules permit UDP/4789 across `.71` ↔ `.72`,
  and RSTP prevents loops in the three-node full mesh. Inter-Proxmox secondary
  network traffic was validated bidirectionally with 0% packet loss.
- Added per-component Helm placement. The radio-sensitive RAN stays on VM 105,
  while `r4-simple-mon` runs on `oran-k8s-w02` and receives live KPM indications.
- Revalidated UE Internet egress and a 10 MiB KPM demo after expansion. The
  measured `DRB.UEThpDl` peak was 28,014 kbps and E2Term was not restarted.

### 2026-08-29 — Live KPM values and repeatable UE traffic demonstration

- Enabled OCUDU DU RLC metrics, the source used by the 26.04 KPM provider to
  calculate `DRB.UEThpDl`; this removes the permanent zero caused by the
  upstream `enable_rlc: false` default.
- Exported decoded KPM values from `r4-simple-mon` as Prometheus gauges,
  including `oran_kpm_drb_ue_throughput_dl_kbps`.
- Added a Grafana throughput time series and `scripts/demo-kpm.sh`, which
  generates bounded traffic through `tun_srsue` and verifies a non-zero KPI.
- Validated the live path with a 10 MiB HTTP 200 transfer: the xApp observed a
  peak of 22,162 kbps and Prometheus persisted the new series. When CU and DU
  E2 agents are both connected, xApp deployment now prefers the `gnbd_*` O-DU,
  because this KPI is provided by the DU RLC measurement source.

### 2026-08-28 — NMI multi-node observability, UE egress, and durable KPM route

- Joined physical server `nmi-srv03` (`164.41.240.13`) as the dedicated
  observability worker; both Kubernetes nodes are `Ready`.
- Added the persistent route to `192.168.72.0/24` and the matching pfSense2 WAN
  policy, allowing the worker to reach the control plane without exposing it.
- Scheduled Prometheus, Grafana, the operator, and kube-state-metrics on the
  worker with a selector and taint/toleration pair.
- Enabled forwarding and idempotent MASQUERADE rules in the UPF; the srsUE now
  reaches the Internet through `tun_srsue`, not only the UPF gateway.
- Fixed the KPM xApp AppMgr descriptor. The previous registration produced
  `txMessages: null` and `rxMessages: null`, so RTMgr omitted subscription routes
  whenever it generated a full `newrt` table. The xApp now declares the official
  subscription/RIC-indication message set, and RTMgr's full policy retains
  `mse|12050|<subscription-id>|service-ricxapp-r4-simple-mon-rmr...` without a
  periodic route-keeper pod.
- Added native Prometheus counters to the xApp and a Grafana KPM indication-rate
  panel, making the working RMR/KPM path visible without reading pod logs.


### 2026-08-25 — NMI srsUE attach and PDU session completed

The single-node NMI deployment now completes the full simulated 5G SA attach:

- srsUE completes random access and RRC connection through the OCUDU DU/CU.
- Open5GS authenticates and registers `imsi-001010000000001`.
- SMF and UPF complete PFCP association using their pod IPs.
- The UE establishes DNN `internet` and receives `10.45.0.2`.
- The CU completes `PDU Session Resource Setup` and the UPF creates the matching
  GTP-U session.
- `ping 10.45.0.1` through `tun_srsue` succeeds with 0% loss.
- The CU inactivity timer is raised from 120 to 7200 seconds because this lab's
  srsUE does not reliably resume its NR bearer after an idle RRC release.

The final PDU-session blocker was caused by combining a ClusterIP Service with a
`hostNetwork` UPF. The SMF sent PFCP to the Service IP, while the UPF replied and
advertised a different node identity. Open5GS consequently logged repeated
`Cannot find PFCP-Node`, `invalid step`, and `No UPFs are associated` errors.

The UPF now runs on the Kubernetes pod network, binds PFCP/GTP-U to `eth0`, and
is discovered through a headless Service. SMF and UPF therefore use the same pod
IP as both the destination and advertised/source identity. Explicit session
gateway and DNN values were also added to match the Open5GS 2.7.7 schema.

External Internet egress is separate from attach/PDU establishment and is not
yet declared by this chart; the validated user-plane boundary is UE ↔ UPF
gateway (`10.45.0.2` ↔ `10.45.0.1`).

### 2026-04-14 — GCP Deployment + Bug Fixes

**Deployment:**
- Two GCP VMs created: `oran-cp1` (e2-standard-2, cp1 `34.173.61.132`) and `oran-w1` (e2-standard-4, `34.46.210.174`) via `gcp-vm-create.yml`
- kubeadm cluster bootstrapped via `provision.yml` (Calico 3.28.4, local-path-provisioner)
- Full O-RAN stack deployed: 5g-core (13 NFs + MongoDB), near-rt-ric (7 components), ran (CU + DU + UE), monitoring (Prometheus + Grafana)
- **All 50 pods Running** — first clean full-stack deployment

**Bugs fixed during this session:**

| Bug | Fix | File(s) |
|-----|-----|---------|
| `crictl` not found during provision | Moved `Verify containerd CRI socket` task to after kubeadm/kubectl install | `ansible/roles/kubeadm_prereqs/tasks/main.yml` |
| e2term crash: `illegal pod_name` | `pod_name=` in `config.conf` is an **env var pointer**, not a literal — kept as `E2TERM_POD_NAME`; set `E2TERM_POD_NAME` via Downward API `metadata.name` | `helm/near-rt-ric/templates/deployments.yaml` |
| e2term crash: RBAC denied K8s pod lookup | Added `ServiceAccount ric-e2term` + `Role`/`RoleBinding` granting `get/list pods` in near-rt-ric namespace | `helm/near-rt-ric/templates/rbac.yaml`, `deployments.yaml` |
| srs-cu readiness probe always failing | F1-U is UDP — TCP probe on port 2153 always fails; replaced with `exec: kill -0 $(pgrep srscu)` process check | `helm/ran/templates/deployments.yaml` |
| Prometheus pod Pending: insufficient CPU | Reduced Prometheus CPU request from 200m to 50m | `helm/monitoring/values.yaml` |

**Verified results:**
- P1 (co-location): `srs-cu` and `amf` both on `w1` ✓
- P2 (E2): gNB `gnb_001_001_00019b` registered in e2mgr (`GET /v1/nodeb/states`) ✓
- F1 setup: DU F1SetupRequest → CU F1SetupResponse completed ✓
- N2: NGSetupRequest → NGSetupResponse completed, AMF connection stable ✓
- ZMQ: UE ↔ DU TCP link established (`10.244.190.105:2000 ↔ 10.244.190.103`) ✓
- UE: Cell search in progress (NAS `Switching on`) — historical 2026-04 GCP
  result; P3 was resolved on the NMI deployment on 2026-08-25

### 2026-04-13 — Pre-Deployment Improvements

| Change | File(s) | Expected Impact |
|--------|---------|-----------------|
| **P1 fix (1a)**: `podAffinity` on srs-cu to prefer the same node as AMF | `helm/ran/templates/deployments.yaml`, `helm/ran/values.yaml` | Eliminates cross-node SCTP path; P1 observed only cross-node |
| **P1 fix (1b)**: SCTP sysctl tuning in `sctp-init` DaemonSet | `helm/5g-core/templates/daemonset-sctp-init.yaml` | Reduces RTO, max_retrans — tightens SCTP association failure detection and retry behaviour |
| **P5 fix**: e2term `render-config` now substitutes `local-ip`, `external-fqdn`, `pod_name` directly; `/log` emptyDir volume added | `helm/near-rt-ric/templates/deployments.yaml` | E2AP processing logs now visible at `/log/e2term.log`; config correctly reflects pod IP |
| **Probes**: Liveness + readiness probes for AMF, srs-cu, srs-du | `helm/5g-core/templates/deployment-amf.yaml`, `helm/ran/templates/deployments.yaml` | `helm --wait` and `kubectl rollout status` now reflect actual readiness |
| **Observability**: Prometheus + Grafana stack (`helm/monitoring`) with ServiceMonitors for all existing `/metrics` endpoints | `helm/monitoring/`, `ansible/roles/deploy_monitoring/`, `ansible/playbooks/deploy.yml` | Operational visibility into NF health, pod restarts, and E2 status |

---

## 1. Current Problems

### P1 — AMF Flapping (N2 / NGAP) — **MITIGATION APPLIED, NEEDS RETEST**

The srsRAN CU-CP connects to Open5GS AMF, completes NGSetupRequest/Response successfully,
then loses the connection ~200–600 ms later. The cycle repeats every ~1–2 seconds indefinitely.

Observed in AMF logs:
```
gNB-N2 accepted[10.4.0.14] in master_sm module
[Added] Number of gNBs is now 7
gNB-N2[10.4.0.14] connection refused!!!
[Removed] Number of gNBs is now 6
```

Observed in CU logs:
```
N2: Connection to AMF ... was established
NGSetupResponse received
"AMF Connection Loss Routine" started...
```

The CU and AMF are on different GKE nodes. This problem occurs — and persists — even with
GKE Dataplane V2 (Cilium / anetd) enabled.

### P2 — E2 Agent Not Connecting — **INTERMITTENT**

The srsRAN DU has `enable_du_e2: true` configured with the correct e2term address
(`e2term.near-rt-ric.svc.cluster.local:36421`). In one observed run (with `all_level: debug`),
the E2 SCTP association was established and E2AP service model OIDs were generated. In all
other runs there are zero `[E2-DU]` log lines and no SCTP association to port 36421 in
`/proc/net/sctp/assocs`.

The inconsistency suggests the E2 agent initialises only when a specific condition is met
(possibly: cell scheduling must be active **and** F1 setup must have succeeded **before** a
certain startup window). The one successful run occurred with debug logging enabled and on a
fresh DU pod; subsequent restarts without debug logging produced no E2 activity.

### P3 — UE Never Attaches — **RESOLVED ON NMI**

The original GCP run stopped at NAS `Switching on`. On NMI, the corrected OCUDU
ZMQ radio profile reaches random access and RRC, while the corrected Open5GS
subscriber/SBI/PFCP configuration completes registration and PDU establishment.
The UE receives `10.45.0.2` and reaches its UPF gateway. See the 2026-08-25
entry above for the verified result.

### P4 — Duplicate DU ID Rejection on DU Restart (**RESOLVED**)

When the DU pod is restarted (e.g. via `kubectl rollout restart`), the new pod sends
F1SetupRequest before the CU has cleaned up the previous DU's state. The CU rejects it with
`"Duplicate DU ID"` and `message-not-compatible-with-receiver-state`. The DU makes only one
retry by default and then gives up, leaving the cell un-served until a second manual restart.

**Fix:** srsRAN's F1 setup retry count is hardcoded to 1 and is not configurable. The fix
is in the DU Deployment's `wait-for-cu` initContainer
(`helm/ran/templates/deployments.yaml`). After confirming the CU process is reachable (DNS
+ UDP F1-U port probe), the container now waits an additional `duF1SetupHoldOffSec` seconds
(default: **30 s**, configurable in `helm/ran/values.yaml`) before allowing srsRAN to
start. The CU purges stale DU state ~23 s after SCTP COMM_LOST, so the 30 s hold-off
guarantees the cleanup window has fully elapsed before srsRAN makes its single F1Setup
attempt.

### P5 — e2term Config File Is Read-Only

The Near-RT RIC e2term startup script tries to run `sed -i` on files inside a ConfigMap
volume mount, which is always read-only in Kubernetes. The `sed` fails silently:
```
sed: couldn't open temporary file /opt/e2/config/sedKL88du: Read-only file system
```
The substitutions (pod IP, pod name) are not applied. e2term still starts and accepts SCTP
connections, so this is not currently blocking P2, but it means e2term runs with its
compiled-in defaults rather than the values the Helm chart intends.

### P6 — Preemptible Nodes Cause Cascading Restarts (**RESOLVED**)

The GKE cluster previously used preemptible (`e2-standard-4`) VMs. When a node was
preempted, all pods on it were deleted simultaneously. Because AMF, CU, and e2term
may land on different nodes, a single preemption event disrupted all three interface
layers (N2, F1, E2) at once and required a coordinated restart sequence (core → RIC →
RAN) to recover cleanly. This was observed to trigger the Duplicate DU ID problem (P4)
on every node preemption.

**Fix:** `preemptible_nodes = false` in `terraform/variables.tf`. The node pool now
provisions standard on-demand `e2-standard-4` nodes (`preemptible = false` in the
`google_container_node_pool` resource). Re-apply Terraform to replace the node pool.

---

## 2. Hypothesis

### H1 — SCTP Cross-Node Behaviour in GKE Dataplane V2

**Hypothesis:** GKE Dataplane V2 (Cilium eBPF) does not fully fix SCTP conntrack for
cross-node pod-to-pod traffic in the same way it fixes TCP. The AMF flapping (P1) was
initially attributed to iptables kube-proxy failing to handle SCTP state on the original
cluster (without Dataplane V2). After recreating the cluster with `ADVANCED_DATAPATH` the
flapping was transiently absent on the first successful run, but returned once the `sgmm`
node was preempted and a new node joined. This suggests either:

- Cilium's SCTP conntrack is correct but **something else** in the path is resetting the
  association (e.g. Open5GS AMF state machine bug triggered by a specific SCTP multi-stream
  negotiation parameter from srsRAN).
- Dataplane V2 helps for steady-state traffic but SCTP association setup across nodes still
  hits a race condition in the eBPF program during the initial 4-way handshake.
- The headless service DNS resolves to the correct pod IP, but the SCTP INIT ACK or
  COOKIE-ECHO is being dropped or re-routed on the new node before eBPF state is fully
  programmed.

### H2 — Open5GS AMF Rejects srsRAN SCTP Stream Count

**Hypothesis:** Open5GS AMF is closing the SCTP association because srsRAN negotiates
`max_num_of_ostreams: 30` in the INIT, but the AMF's internal NGAP state machine expects
exactly 1 outbound stream for the first NGAP message and treats anything else as an error.
The log line `gNB-N2[x.x.x.x] connection refused!!!` in Open5GS is emitted from
`amf-sm.c:1013`, which is the handler for an SCTP_COMM_LOST event — i.e. the AMF itself is
not actively refusing; it is reacting to the SCTP association being closed from the network
or from within the kernel. This shifts the blame back toward the datapath (H1) rather than
the application layer.

### H3 — E2 Agent Requires Active Cell Before Initialising

**Hypothesis:** The srsRAN DU E2 agent only starts after the cell scheduler is active
**and** at least one scheduling cycle has completed. In the one run where E2 connected, the
DU pod was fresh (no prior state), debug logging was on (which adds startup latency), and
the init containers' DNS wait guaranteed the CU was fully ready before F1 Setup. In all
other runs the DU pod was restarted mid-flight while the CU still had stale state, causing
F1 Setup to fail (P4) and the cell scheduler to never activate — which in turn prevented
the E2 agent from starting.

---

## 3. Facts

| # | Fact | Source |
|---|------|--------|
| F1 | GKE Dataplane V2 (`ADVANCED_DATAPATH`) uses Cilium eBPF (`anetd`). `anetd` is running on both nodes (verified via `kubectl get pods -n kube-system`). | kubectl |
| F2 | AMF flapping (`connection refused!!!`) occurs with cross-node CU↔AMF placement even on Dataplane V2. It was absent for ~10 minutes after first deploy, then returned after node preemption. | AMF logs |
| F3 | The `amf-ngap-headless` service is `clusterIP: None` (headless). DNS resolves directly to the AMF pod IP, bypassing kube-proxy DNAT entirely. | kubectl |
| F4 | The SCTP 4-way handshake completes (NGSetupRequest → NGSetupResponse received), proving the connection reaches application layer. The AMF logs `COMM_LOST` ~200–600 ms later. | CU + AMF logs |
| F5 | In the one run where E2 worked, `[E2-DU]` log lines appeared, SCTP association to `10.8.7.148:36421` (e2term ClusterIP) was established, and E2AP RAN function OIDs for KPM and RC were generated. | DU logs + `/proc/net/sctp/assocs` |
| F6 | In all other DU runs `/proc/net/sctp/assocs` shows only the F1AP association (to CU port 38472). There are no `[E2-DU]` log lines and no error messages about E2. | kubectl exec |
| F7 | The DU config is rendered correctly: `enable_du_e2: true`, `addr: e2term.near-rt-ric.svc.cluster.local`, `port: 36421`, `bind_addr: <pod IP>`. The pod IP is a real IP (sed substitution works). | kubectl exec cat |
| F8 | F1 Setup fails with "Duplicate DU ID" if the new DU pod races ahead of the CU cleaning up the old DU. The CU cleans up the old DU ~23 seconds after SCTP COMM_LOST. The DU's internal retry count is hardcoded to 1 (not configurable). **Fixed (P4):** `wait-for-cu` initContainer now holds off 30 s after the CU is reachable, outlasting the cleanup window. | CU logs / `helm/ran/values.yaml` |
| F9 | `apk add gettext` fails silently inside the GKE init containers (no internet egress to Alpine mirrors). This was the original cause of `${POD_IP}` not being substituted. Fixed by replacing `envsubst` with `sed`. | init container logs |
| F10 | In the historical GCP run the UE stopped at NAS `Switching on`; the NMI deployment resolved the radio, registration, and PFCP/PDU path on 2026-08-25. | UE + DU + Open5GS logs |
| F11 | Node pool now uses standard (on-demand) `e2-standard-4` nodes (`preemptible = false`). Previously preemptible — preemption was observed once during a session, causing `sgmm` to be replaced and triggering P1 + P4 simultaneously. P6 resolved. | terraform/variables.tf |
| F12 | e2term `sed -i` substitutions fail at startup (read-only ConfigMap volume). e2term is still functional (accepts SCTP). The Helm chart's intent to inject pod IP / pod name is not applied. | e2term logs |
| F13 | Open5GS AMF NRF registration, UDM/AUSF/NSSF subscriptions, and all SBI NF-to-NF links are healthy and stable. The 5G core NFs other than the AMF SCTP path are not the problem. | AMF logs |
| F14 | The Near-RT RIC internal RMR mesh (e2term ↔ e2mgr ↔ rtmgr ↔ submgr) is healthy. RMR heartbeat counts increment normally. No internal RIC errors observed. | e2mgr + e2term logs |

---

## 4. VPS vs GKE — Would This Be Easier on VMs?

**Short answer: yes, significantly, for a lab.**

### What gets easier on VPS

**SCTP works without fighting the dataplane.**
On a plain Linux VM (Debian, Ubuntu, etc.), SCTP is a first-class kernel feature. There is
no container network plugin, no eBPF overlay, no conntrack translation layer between two
pods. srsRAN CU and Open5GS AMF would run as processes (or in Docker with `--network=host`)
and their SCTP associations would be handled by the vanilla kernel TCP/IP stack with
`CONFIG_IP_SCTP=y`. The AMF flapping problem (P1) would almost certainly not exist.

**No node preemption.**
A VPS does not disappear mid-session. Preemptible GKE nodes were the direct cause of the
cascading restart problem (P6) and contributed to the Duplicate DU ID race (P4). P6 has
been resolved by switching to standard on-demand nodes; however on a VPS services stay
up until you restart them with no GCP infrastructure dependency.

**No container networking overhead for SCTP.**
ZMQ (used by srsRAN for the simulated radio between DU and UE) is TCP-based and works fine
in Kubernetes. SCTP (used by N2, F1, E2) is the problematic protocol in every container
network plugin tested so far.

**Simpler config management.**
On VMs you can use the original srsRAN `.yml` / `.conf` files directly with real hostnames
or IPs. There is no ConfigMap templating, no init container `envsubst`/`sed` pipeline, no
imagePullSecret management.

**Cheaper for always-on lab use.**
Two `e2-standard-4` GKE nodes (4 vCPU, 16 GB each) cost ~$0.17/hour each (preemptible) or
~$0.57/hour (on-demand). A comparable VPS (e.g. Hetzner CX41: 8 vCPU, 16 GB) costs ~$0.03–
0.06/hour. For a continuously-running lab the cost difference is significant.

### What GKE does better

| Concern | GKE | VPS |
|---------|-----|-----|
| Declarative infra | Terraform + Helm — reproducible from scratch | Manual or Ansible against static IPs |
| Scaling | Add nodes, pods reschedule automatically | Manual VM provisioning |
| Rolling updates | `helm upgrade` with zero-downtime for stateless NFs | Stop, update, restart |
| Observability | Prometheus / GMP built-in, log forwarding to Cloud Logging | Self-hosted or nothing |
| Image distribution | Docker Hub pull works everywhere | Same — no advantage |
| SCTP | Requires Dataplane V2 and careful service design; still unreliable in testing | Works out of the box |

### Recommendation

For a **protocol-correct, always-on lab** where SCTP reliability is the priority:
use 2–3 VPS instances (1 for 5G core, 1 for RAN, 1 for RIC) with Docker Compose or bare
processes. The existing Helm charts and Ansible roles can be adapted to Compose with minimal
effort — the config templates and image names are already parameterised.

For a **reproducible, cloud-native lab** where the goal is to practice Kubernetes-native
O-RAN deployment: stay on GKE with standard (non-preemptible) nodes (now the default) and
add a `PodAntiAffinity` rule to keep CU and AMF on the same node until the cross-node SCTP
issue is fully understood.

A hybrid is also viable: run the 5G core and RIC on GKE (stateless HTTP/gRPC SBI is well-
suited to Kubernetes), and run srsRAN CU/DU/UE as Docker Compose on a single VPS that
connects to the GKE cluster via a VPN or `kubectl port-forward`. This isolates the SCTP
problem to a single hop (VPS process → GKE NodePort → AMF pod) which is easier to debug
and avoids cross-node SCTP entirely.

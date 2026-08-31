# Nephio R6 on the NMI cluster

Last verified: 2026-08-30

## Purpose and corrected architecture

Nephio is installed in the existing NMI Kubernetes cluster. There is no second
NMI management cluster. VM `113` was reused as the fifth NMI node and provides
placement capacity for the Nephio namespaces.

```text
NMI Kubernetes v1.30.14
|
+-- oran-k8s-01       control plane + radio-sensitive workloads
+-- oran-k8s-w01      general worker
+-- oran-k8s-w02      general worker + r4-simple-mon
+-- nmi-srv03         observability worker
+-- nephio-k8s-w01    Gitea + Porch + Nephio + Flux + WebUI
                          |
                          v
     blueprint -> PackageVariant -> Published -> Git
                       |                         |
                       |                         +--> NMI Flux -> NMI workload
                       +--> CIC package -> CIC Flux ARM64 -> CIC workload
```

Namespaces separate the Nephio services from `5g-core`, `near-rt-ric`, `ran`,
and `ricxapp`. The main Deployments and StatefulSets also use
`nodeSelector: {workload: nephio}` so they run on VM 113. CRDs and RBAC remain
cluster-scoped by Kubernetes design.

Proxmox, pfSense, Kubernetes bootstrap, Multus/OVS, RAN, Near-RT RIC and 5G Core
remain under the existing Ansible/Helm path. Nephio owns the harmless NMI/CIC
smoke packages and, after the validated handoff, the `r4-simple-mon` xApp only.

## Reused VM 113

| Item | Value |
| --- | --- |
| Proxmox host | `proxmox001` |
| VM / node | `113` / `nephio-k8s-w01` |
| Address | `192.168.71.30/24` via `192.168.71.1` |
| Resources | 8 vCPU, 8 GiB RAM, 80 GB disk |
| OS | Ubuntu 22.04.5 LTS |
| Kubernetes | worker `v1.30.14` |
| Node label | `workload=nephio` |

Ubuntu and Debian workers coexist normally in this Linux/amd64 cluster. The
important compatibility boundary is Kubernetes version skew, not the Linux
distribution. Before joining, VM 113 was reset and downgraded from Kubernetes
1.32.13 to exactly `1.30.14-1.1`, matching the NMI control plane.

The worker does not need its own telecom OVS mesh for Nephio. Cluster-wide
DaemonSets still install Flannel, kube-proxy, OVS-CNI, SCTP init, Alloy and
node-exporter on the node, and all were verified `Running` after the join.

## Installed components

| Namespace | Components | Baseline |
| --- | --- | --- |
| `gitea` | Gitea, PostgreSQL, Memcached | Nephio R6 catalog |
| `porch-system` | Porch server, controllers, function runners | `v1.5.7` |
| `porch-fn-system` | Temporary KRM function pods | created on demand |
| `nephio-system` | Nephio and token controllers | `v6.0.0` |
| `flux-system` | source, kustomize, helm and notification controllers | R6 catalog baseline |
| `nephio-webui` | Kpt/Porch WebUI | image pinned by digest |
| `nephio-lab` | first package delivery target | ConfigMap-only POC |
| `ricxapp` | `r4-simple-mon` delivery target | Deployment, Services and runtime ConfigMap |

The catalog is pinned to commit
`3d81f20e7a5e578e28152cb5b85841cfbae6d300`. kpt is
`v1.0.0-beta.64`, Porch/porchctl is `v1.5.7`, and downloaded binaries are
checked against committed SHA-256 values.

Only the resource-backend CRDs are installed. The optional inventory/IPAM/VLAN
backend service is not required for this POC.

## Package and GitOps flow

The first end-to-end package is `nmi-lab-smoke`:

```text
Porch revision nmi.nmi-lab-smoke.v1
  Draft -> Proposed -> Published (revision 1)
             |
             v
Gitea repository nephio/nmi, branch main
             |
             v
Flux GitRepository Ready=True
             |
             v
Flux Kustomization Ready=True
             |
             v
ConfigMap nephio-lab/nephio-delivery-smoke
```

The validated Git revision was
`e7e3352977b366e7c8256c44cc5e68843017ad9f`. The resulting ConfigMap contains:

```text
Package approved by Porch and reconciled by Flux | revision=v1
```

Because Flux now runs in the target cluster, no cross-cluster kubeconfig or
public Kubernetes API exposure is needed.

## Blueprint, intent and site specialization

`team-blueprints/r4-simple-mon` is the reusable student-facing package. It does
not target a cluster directly. A `PackageVariant` combines that blueprint with
the `WorkloadCluster/nmi` inventory and runs a KRM replacement function. The
result is the published deployment package `nmi/r4-simple-mon-nmi-v5` consumed by
Flux.

The NMI variant injects the site, target node, digest-pinned image, E2 node id
and KPM metric. This is the concrete meaning of an intent in this POC: choose
the blueprint and site; Nephio renders the site-specific package; Porch
publishes it; Flux applies it. Students still write and test xApp code,
container images and Kubernetes resources. Nephio manages their reusable
configuration lifecycle, not the RMR runtime or the radio protocol.

The WebUI parser shipped by the pinned Nephio image assumed every YAML file was
a Kubernetes resource with `metadata.name`. Real kpt packages also contain
files such as `Kustomization`, so the frontend crashed while the Porch API
remained healthy. `infra/nephio/webui-compat/` installs a reproducible
init-container patch that skips non-KRM documents.

## CIC workload-cluster delivery proof

The CIC inventory is now more than a catalog entry. The management side has a
Porch deployment repository named `cic`; CIC runs only Flux v2.7.5
`source-controller` and `kustomize-controller`. Version 2.7 is pinned because
it is the newest Flux minor supporting Kubernetes 1.32.

```text
WorkloadCluster/cic
  -> Porch revision cic.cic-lab-smoke.v1 (Published)
  -> Gitea nephio/cic, commit 1f3c994c090da3033100aaa93ee186647e08115c
  -> CIC GitRepository Ready=True
  -> CIC Kustomization Ready=True
  -> ConfigMap nephio-lab/nephio-delivery-smoke
     site=cic, architecture=arm64, revision=v1
```

The CIC GitOps identity can modify only ConfigMaps in `nephio-lab`. Gitea is
reachable from the routed laboratory networks through NMI NodePort `30302`; no
pfSense WAN publication or remote Kubernetes API credential is used.

## Restricted delivery identities

The Flux Kustomization uses ServiceAccount
`flux-system/nephio-deployer`. A RoleBinding grants it only ConfigMap operations
inside `nephio-lab`.

Validated authorization results:

```text
create ConfigMaps in nephio-lab: yes
get Secrets in nephio-lab: no
update Deployments in ran: no
WebUI list Secrets: no
```

The xApp uses a separate ServiceAccount,
`flux-system/r4-simple-mon-deployer`. Its Role is confined to `ricxapp`: it may
manage Deployments, Services and ConfigMaps and may read Pods/ReplicaSets for
health assessment. It cannot read Secrets and cannot update RAN Deployments.

## r4-simple-mon deploy, update and rollback

The package in `packages/nephio/r4-simple-mon/` captures the live xApp contract:

- image `x0tok/oran-xapps` pinned by digest;
- `DRB.UEThpDl`, report style 1 and RAN function 2;
- E2 node `gnbd_001_001_00019b_e2`;
- RMR/HTTP Services on ports 4561/8091;
- placement on `oran-k8s-w02`;
- the exact `xAppBase.py` runtime hotfix, SHA-256 `48ca48a...129b`.

The accepted lifecycle was:

| Porch revision | Git revision | Desired state | Functional result |
| --- | --- | --- | --- |
| `nmi.r4-simple-mon.v1` | `eeb8a88` | `v1 / baseline` | Flux Ready and KPM received |
| `nmi.r4-simple-mon.v2` | `0f2773a` | `v2 / tuned` | rollout healthy and KPM received |
| `nmi.r4-simple-mon.v3` | `ca9e3ee` | `v3-rollback / baseline` | rollback healthy and KPM received |

Rollback is a new forward revision copied from the known-good v1 content. Git
history never moves backwards. That demonstration ended on subscription 47.
The later `PackageVariant` rollout subscribed as ID 50 and had 832 RMR/decoded
KPM indications at the final acceptance check.

During the first Helm-to-Flux adoption, RTMgr needed one controlled restart to
republish its complete route table. The old REST subscription and only the xApp
pod were then recreated; E2Term was not restarted and the SCTP connection was
preserved. Subsequent v2 and rollback rollouts subscribed and received KPM
without manual recovery.

The ten Helm release Secrets (revisions 19 through 28) were backed up root-only
under `/opt/nephio/backups/` on `oran-k8s-01`, then removed. `helm list -n
ricxapp` is now empty, avoiding dual ownership. The NMI Ansible inventory sets
`xapp_deployment_backend=nephio`, so future full deploy runs do not overwrite
the package with Helm.

## Private access over the NMI VPN

The WebUI is a NodePort service on TCP `30707`, restricted by pfSense to the
NMI VPN network. Browse to
`http://192.168.71.30:30707/config-as-data`. Gitea keeps its normal ClusterIP,
with a separate NodePort `30302` used by CIC Flux over the routed private lab
networks. Neither service has a public Internet rule.

For Gitea, browse to `http://127.0.0.1:3000` while this tunnel is active:

```bash
ssh -L 3000:127.0.0.1:3000 -t lucasrc@192.168.72.10 \
  'kubectl -n gitea port-forward --address=127.0.0.1 service/gitea 3000:3000'
```

The Gitea password is generated and not committed. An administrator can read it
on the Nephio worker with:

```bash
sudo cat /etc/nephio/gitea-password
```

## Reproduction

Join or repair VM 113 without reinitialising the NMI control plane:

```bash
cd ansible
ansible-playbook playbooks/join-nephio-worker.yml \
  -i inventories/nmi-nephio-worker.ini
```

The playbook resets only hosts in `nephio_workers`, pins Kubernetes
`1.30.14-1.1`, uses a 30-minute join token and validates Flannel before
returning.

Run `infra/nephio/install-management.sh` as root on `nephio-k8s-w01` with a
root-readable NMI admin kubeconfig. The installer pins all versions, applies
worker placement through a KRM function, preserves kpt inventory between
reruns, and uses bounded event output instead of the continuously redrawn kpt
table.

Declarative onboarding files are in `infra/nephio/nmi-onboarding/`; package
sources are in `packages/nephio/nmi-lab-smoke/` and
`packages/nephio/r4-simple-mon/`.

The blueprint and CIC workload-cluster flows are reproducible from
`infra/nephio/blueprints/`, `infra/nephio/cic-onboarding/` and
`packages/nephio/cic-lab-smoke/`.

Run the complete, idempotent onboarding after installing the controllers:

```bash
export KUBECONFIG=/etc/nephio/nmi-admin.conf
sudo -E ./infra/nephio/nmi-onboarding/onboard-nmi.sh
```

The script waits for the Gitea tokens, registers the Porch repository, publishes
the package lifecycle and confirms the Flux reconciliation. A published
revision is detected and reused on subsequent runs.

Publish and verify the xApp baseline:

```bash
cd infra/nephio/nmi-onboarding
./publish-xapp-package.sh ../../../packages/nephio/r4-simple-mon
kubectl apply -f xapp-rbac.yaml
kubectl apply -f xapp-flux-sync.yaml
./stabilize-xapp-rmr.sh       # first Helm-to-Flux handoff only
./verify-xapp-package.sh v1 baseline
```

Repeat the update/rollback demonstration with unique Porch workspaces:

```bash
./demo-xapp-update-rollback.sh
```

## Useful checks

```bash
kubectl get nodes -L workload
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded
kubectl get repository.config.porch.kpt.dev
kubectl get workloadcluster.infra.nephio.org
kubectl get packagevariant.config.porch.kpt.dev
porchctl rpkg get -n default
kubectl get gitrepository,kustomization -n flux-system
kubectl get configmap nephio-delivery-smoke -n nephio-lab
kubectl get kustomization r4-simple-mon -n flux-system
kubectl get deployment r4-simple-mon -n ricxapp \
  -o jsonpath='{.metadata.annotations.nephio\.org/package-revision}{" / "}{.metadata.annotations.nephio\.org/demo-state}{"\n"}'
```

## Next step

The ARM experiment is complete. The multi-architecture `simple-mon` image runs
natively on `cic-k8s-w01`, and Porch revision
`cic.r4-simple-mon-cic-arm64.packagevariant-3` is reconciled by CIC Flux. A
bidirectional RMR bridge preserves the canonical RIC service names and ports;
the xApp registered, subscribed and received real KPM indications while RIC,
RAN and Core remained on the validated NMI `amd64` environment.

The next step is to prepare a bounded student workflow: start from the Team
Blueprint, build a digest-pinned multi-architecture image, create an NMI or CIC
variant, approve it in Porch, observe Flux reconciliation, verify KPM in
Grafana, and demonstrate a forward rollback.

## Primary references

- Nephio R6 release notes: <https://docs.nephio.org/docs/release-notes/r6/>
- Bring-your-own-cluster installation: <https://docs.nephio.org/docs/guides/install-guides/install-on-byoc/>
- Centralized Flux workload deployment: <https://docs.nephio.org/docs/guides/user-guides/usecase-user-guides/exercise-3-fluxcd-wl/>
- Porch documentation: <https://docs.nephio.org/docs/porch/>

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
        Draft -> Proposed -> Published -> Git -> Flux
                          |
                          v
             namespace nephio-lab (first POC package)
```

Namespaces separate the Nephio services from `5g-core`, `near-rt-ric`, `ran`,
and `ricxapp`. The main Deployments and StatefulSets also use
`nodeSelector: {workload: nephio}` so they run on VM 113. CRDs and RBAC remain
cluster-scoped by Kubernetes design.

Proxmox, pfSense, Kubernetes bootstrap, Multus/OVS and the complete O-RAN stack
remain under the existing Ansible/Helm path. Nephio initially owns only the
harmless package in `nephio-lab`.

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

## Restricted first deployment

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

This role will be expanded only when the `r4-simple-mon` package is ready, and
only for the exact namespaced resources that package needs.

## Private access over the NMI VPN

Gitea and the WebUI are `ClusterIP` services. Neither has a NodePort nor a
public pfSense rule.

Open the WebUI by keeping this tunnel active and browsing to
`http://127.0.0.1:7007`:

```bash
ssh -L 7007:127.0.0.1:7007 -t lucasrc@192.168.72.10 \
  'kubectl -n nephio-webui port-forward --address=127.0.0.1 service/nephio-webui 7007:7007'
```

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

Declarative onboarding files are in `infra/nephio/nmi-onboarding/`; the package
source is in `packages/nephio/nmi-lab-smoke/`.

Run the complete, idempotent onboarding after installing the controllers:

```bash
export KUBECONFIG=/etc/nephio/nmi-admin.conf
sudo -E ./infra/nephio/nmi-onboarding/onboard-nmi.sh
```

The script waits for the Gitea tokens, registers the Porch repository, publishes
the package lifecycle and confirms the Flux reconciliation. A published
revision is detected and reused on subsequent runs.

## Useful checks

```bash
kubectl get nodes -L workload
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded
kubectl get repository.config.porch.kpt.dev
porchctl rpkg get -n default
kubectl get gitrepository,kustomization -n flux-system
kubectl get configmap nephio-delivery-smoke -n nephio-lab
```

## Next package

The next POC step is to package `r4-simple-mon`, expose only site and resource
parameters, then demonstrate an update and rollback through Porch and Flux. The
complete RIC, RAN and Core remain outside Nephio ownership.

## Primary references

- Nephio R6 release notes: <https://docs.nephio.org/docs/release-notes/r6/>
- Bring-your-own-cluster installation: <https://docs.nephio.org/docs/guides/install-guides/install-on-byoc/>
- Centralized Flux workload deployment: <https://docs.nephio.org/docs/guides/user-guides/usecase-user-guides/exercise-3-fluxcd-wl/>
- Porch documentation: <https://docs.nephio.org/docs/porch/>

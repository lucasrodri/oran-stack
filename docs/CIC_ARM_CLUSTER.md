# CIC ARM64 laboratory cluster

## Purpose

This is a two-node Kubernetes laboratory cluster running on separate Ampere
servers at CIC. It is not a high-availability or production design. Two VMs
were chosen because they let students exercise scheduling, cross-host Pod
networking, Multus, Open vSwitch and O-RAN secondary networks on real ARM64
hosts. The same software can run on one VM, but it would not demonstrate those
inter-host paths.

The cluster is initially empty of the O-RAN application stack. NMI remains the
validated `amd64` reference environment. CIC is now registered as the `arm64`
Nephio workload target for multi-architecture images, xApps and site variants.

## Deployed topology

| Role | Proxmox host | VMID | VM | Address | Resources | OS |
| --- | --- | ---: | --- | --- | --- | --- |
| Control plane | Ampere 2 | 120 | `cic-k8s-cp01` | `192.168.0.210/24` | 8 vCPU, 16 GiB, 100 GB | Debian 12 ARM64 |
| Worker | Ampere 3 | 121 | `cic-k8s-w01` | `192.168.0.211/24` | 8 vCPU, 16 GiB, 100 GB | Debian 12 ARM64 |

Both VMs use gateway `192.168.0.2`, can reach the NMI `.71` and `.72`
networks, and can reach package and image registries. No pfSense change was
required for this cluster.

```text
                         CIC LAN 192.168.0.0/24

       Ampere 2                                      Ampere 3
  +------------------+                          +------------------+
  | Proxmox / VM 120 |                          | Proxmox / VM 121 |
  | cic-k8s-cp01     |                          | cic-k8s-w01      |
  | 192.168.0.210    |                          | 192.168.0.211    |
  | control plane    |                          | worker           |
  +--------+---------+                          +---------+--------+
           |                                                |
           +========= Flannel 10.246.0.0/16 ================+
           +========= OVS/VXLAN n2br  10.200.1/24 ==========+
           +========= OVS/VXLAN f1cbr 10.200.2/24 ==========+
           +========= OVS/VXLAN e2br  10.200.3/24 ==========+
                                    |
                         gateway 192.168.0.2
                                    |
                     NMI networks 192.168.71/72
```

## Software baseline

| Component | Deployed value |
| --- | --- |
| Architecture | `arm64` / `aarch64` |
| Kubernetes | `v1.32.13` |
| Container runtime | containerd `2.3.4` |
| Primary CNI | Flannel `v0.28.8` |
| Meta-CNI | Multus `v4.3.0` |
| Secondary CNI | OVS-CNI managed by CNAO `v0.102.0` |
| Storage | Rancher local-path `v0.0.36` |
| Node metrics | node-exporter `v1.12.1` on both nodes |
| Kubernetes object metrics | kube-state-metrics `v2.16.0` on Ampere 3 |
| GitOps runtime | Flux `v2.7.5`, source + kustomize controllers only |
| Pod CIDR | `10.246.0.0/16` |
| Service CIDR | `10.97.0.0/16` |

Kubernetes 1.32 is an inventory-specific compatibility target: Nephio R6
documents support through the 1.32 minor. The repository-wide baseline for a
generic fresh cluster remains independent from this exception.

## Provisioning

The committed inventory is `ansible/inventories/cic-arm.ini`. From the
repository root:

```bash
cd ansible
ansible-playbook playbooks/provision.yml -i inventories/cic-arm.ini
```

The playbook prepares containerd and Kubernetes, installs Flannel, Multus,
OVS-CNI and local-path-provisioner, creates the `n2br`, `f1cbr` and `e2br`
bridges, and builds a full-mesh VXLAN for those bridges.

It also writes a local `kubeconfig` at the repository root. The file is ignored
by Git because it contains cluster credentials.

## Validated acceptance tests

The reproducible test manifest is
`ansible/manifests/cic-arm-smoke.yaml`:

```bash
kubectl --kubeconfig kubeconfig apply -f ansible/manifests/cic-arm-smoke.yaml
kubectl --kubeconfig kubeconfig -n lab-smoke get pods -o wide
```

Validated on 2026-08-30:

- both nodes were `Ready`, `arm64`, and running Kubernetes `v1.32.13`;
- two `nginx:1.27-alpine` replicas were scheduled on `cic-k8s-w01`;
- `uname -m` inside the workload returned `aarch64`;
- the control-plane host reached a worker Pod and its ClusterIP Service with
  HTTP 200;
- OVS-CNI was `Ready` on both nodes;
- a Pod on each node received a Multus interface on `e2br`;
- `10.200.3.250` and `10.200.3.251` exchanged four pings in both directions
  over the inter-host OVS VXLAN with 0% packet loss;
- no system Pod remained Pending or failed after the test.
- both ARM node-exporter endpoints and the kube-state-metrics NodePort returned
  HTTP 200 when queried from NMI VM 105.

The two E2 probe Pods deliberately sleep for 24 hours and produce no routine
logs. Delete and reapply them to repeat the OVS test after they complete.

## Multi-site observability

The NMI Prometheus instance scrapes both ARM nodes and the CIC Kubernetes object
metrics through a TCP relay pinned to VM 105 (`192.168.72.10`). Prometheus adds
the labels `cluster=cic-arm`, `site=cic` and `architecture=arm64`. Grafana shows
the result in `O-RAN Multi-Site Lab` alongside the five-node NMI cluster.

Apply or update the CIC collectors with:

```bash
kubectl --kubeconfig kubeconfig apply \
  -f ansible/manifests/cic-arm-observability.yaml
```

The relay is part of the NMI `helm/monitoring` chart. No Prometheus or Grafana
instance is duplicated at CIC, and no metric access logs are retained.

## Nephio and GitOps onboarding

Nephio/Porch remains in the NMI cluster. CIC does not run a second Nephio
management plane; it runs the minimum Flux workload agent. Flux reads the CIC
deployment repository through the private routed path to
`192.168.72.10:30302`.

The first accepted package, `cic.cic-lab-smoke.v1`, was approved by Porch in
NMI and reconciled in CIC at Git revision
`1f3c994c090da3033100aaa93ee186647e08115c`. It created
`nephio-lab/nephio-delivery-smoke` with `site=cic` and
`architecture=arm64`. Both Flux controllers and both reconciliation resources
were `Ready=True`.

Reproduction manifests and bounded scripts live in
`infra/nephio/cic-onboarding/`. The Flux ARM64 archive is pinned and checked by
SHA-256 before execution. Its ServiceAccount can modify only ConfigMaps in the
test namespace.

## ARM xApp acceptance

The first real O-RAN workload now runs in CIC. Porch generated and published
`cic.r4-simple-mon-cic-arm64.packagevariant-3` from
`team-blueprints/r4-simple-mon.v4`; CIC Flux reconciled Git revision
`fbad22adb6eaaaea2845171a33fec1affd2d349c`. The Deployment uses the verified
multi-architecture image index:

```text
ghcr.io/lucasrodri/oran-stack/oran-xapps
  @sha256:dd52cb4bc7508357d0407d1a977850a27fab932155fd589e1fe36676ec8fd0f9
```

The xApp process reports `aarch64`, registers in the NMI AppMgr and subscribes
to `DRB.UEThpDl` through the NMI SubMgr. RTMgr distributes its dynamic route
table across the two clusters. At acceptance, CIC reported one active
subscription and 401 RMR/E2SM-KPM indications; Prometheus target
`job="cic-simple-mon"` was up.

```text
NMI RTMgr/AppMgr/SubMgr
  -> service-ricxapp-r4-simple-mon-cic-rmr:4561/8091
  -> 192.168.0.211:30611/30691
  -> simple-mon ARM64

simple-mon RMR acknowledgement
  -> ric-rtmgr.near-rt-ric:4560 (CIC bridge)
  -> 192.168.72.10:30460
  -> NMI RTMgr
```

## Current boundary and next use

This validates a distributed experiment, not a complete ARM64 port of the
stack. Near-RT RIC, simulated RAN/UE and Open5GS deliberately remain in NMI;
only `simple-mon` runs in CIC. The next useful step is the student tutorial and
package template for building, publishing, deploying and rolling back new
xApps on either architecture.

Ampere 1 remains available as a physical Ubuntu ARM64 machine, but it is not a
member of this cluster. Keeping it separate preserves a useful bare-metal test
target for radio, performance or image-build experiments.

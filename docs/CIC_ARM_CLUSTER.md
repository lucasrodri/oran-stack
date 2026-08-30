# CIC ARM64 laboratory cluster

## Purpose

This is a two-node Kubernetes laboratory cluster running on separate Ampere
servers at CIC. It is not a high-availability or production design. Two VMs
were chosen because they let students exercise scheduling, cross-host Pod
networking, Multus, Open vSwitch and O-RAN secondary networks on real ARM64
hosts. The same software can run on one VM, but it would not demonstrate those
inter-host paths.

The cluster is initially empty of the O-RAN application stack. NMI remains the
validated `amd64` reference environment. CIC is the `arm64` workload target for
multi-architecture images, xApps and later Nephio site variants.

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

The two E2 probe Pods deliberately sleep for 24 hours and produce no routine
logs. Delete and reapply them to repeat the OVS test after they complete.

## Current boundary and next use

This completes the infrastructure portion of the CIC ARM integration. It does
not claim that the whole O-RAN stack already runs on ARM64. The next useful
steps are:

1. add this cluster to the NMI Prometheus/Grafana view using node-level targets;
2. build and validate a small multi-architecture workload, preferably the
   `simple-mon` xApp or a telemetry-only component;
3. keep the current Near-RT RIC on NMI until its RMR/SDL image chain has a
   tested ARM64 build;
4. later register CIC as a Nephio workload cluster and create a CIC package
   variant.

Ampere 1 remains available as a physical Ubuntu ARM64 machine, but it is not a
member of this cluster. Keeping it separate preserves a useful bare-metal test
target for radio, performance or image-build experiments.

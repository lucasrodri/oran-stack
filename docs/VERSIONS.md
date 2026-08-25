# Version baseline

This repository separates the version used for a fresh installation from the
version currently running in an existing environment. Updating a variable here
does not authorize an unsupported in-place upgrade.

Baseline reviewed on 2026-08-24:

| Component | Version | Policy |
| --- | --- | --- |
| Kubernetes | 1.36 (latest patch from the 1.36 apt repository) | Current stable minor |
| Flannel | v0.28.8 | Current stable release |
| Multus | v4.3.0 | Current stable release |
| Cluster Network Addons Operator | v0.102.0 | Current stable release |
| Local Path Provisioner | v0.0.36 | Current stable release; includes a security fix |
| Open5GS | v2.7.7 | Current stable release |
| MongoDB | 8.0.29 | Current patch in the supported 8.0 major line; direct upgrade path from 7.0 |
| OCUDU | release_26_04 | Current completed release; 26.10 is not released yet |
| srsRAN 4G / srsUE | release_25_10 | Current stable release |
| Node.js (WebUI build/runtime) | 24 LTS | Supported LTS line |
| xApp runner | O-RAN SC I release compatibility baseline | Legacy exception: Python 3.8 and amd64-only RMR packages must be replaced before CIC/arm64 deployment |

### Near-RT RIC upstream baseline

The latest release branch currently published by the official Near-RT RIC
deployment repository is M. Its recipe declares the following component tags:

| Component | M-release tag |
| --- | --- |
| E2 Termination | 6.0.8 |
| E2 Manager | 6.0.8 |
| Application Manager | 0.5.10 |
| Subscription Manager | 0.10.4 |
| Routing Manager | 0.9.7 |
| A1 Mediator | 3.2.3 |
| DBaaS | 0.6.5 |

These tags are the Near-RT RIC deployment defaults for the NMI `amd64`
environment. The official recipe points to the Linux Foundation Nexus
registry, which returns HTTP 402 from this environment. To make clean installs
reproducible, `.github/workflows/ric-m-images.yml` builds the pinned upstream
sources and publishes `linux/amd64` images under
`ghcr.io/lucasrodri/oran-stack`. See `docs/RIC_IMAGES.md` for the exact source
commits and build procedure.

The Ampere/CIC `arm64` environment is deliberately outside this deployment
phase. RMR and SDL are compiled as dependencies inside these RIC container
images; they are not installed separately on the NMI VM.

Primary sources:

- Kubernetes releases: <https://kubernetes.io/releases/>
- kubeadm upgrade rules: <https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/>
- Flannel releases: <https://github.com/flannel-io/flannel/releases>
- Multus releases: <https://github.com/k8snetworkplumbingwg/multus-cni/releases>
- Cluster Network Addons Operator releases: <https://github.com/kubevirt/cluster-network-addons-operator/releases>
- Local Path Provisioner releases: <https://github.com/rancher/local-path-provisioner/releases>
- Open5GS releases: <https://github.com/open5gs/open5gs/releases>
- MongoDB 8.0 releases: <https://www.mongodb.com/docs/v8.0/release-notes/8.0/>
- OCUDU milestones: <https://gitlab.com/ocudu/ocudu/-/milestones>
- srsRAN 4G releases: <https://github.com/srsran/srsRAN_4G/releases>
- Node.js release status: <https://nodejs.org/en/about/previous-releases>
- O-RAN SC Near-RT RIC M-release recipe: <https://github.com/o-ran-sc/ric-plt-ric-dep/blob/m-release/RECIPE_EXAMPLE/example_recipe_oran_m_release.yaml>

## Existing NMI cluster

The NMI lab was initially validated on Kubernetes 1.30.14. Kubernetes does not
support skipping minor versions with kubeadm, so the migration must follow this
sequence:

```text
1.30 -> 1.31 -> 1.32 -> 1.33 -> 1.34 -> 1.35 -> 1.36
```

Take a Proxmox snapshot and a data backup before the first step. At every minor
version, upgrade kubeadm, apply the control-plane upgrade, upgrade kubelet and
kubectl, then verify node readiness, CNI health, persistent volumes, Open5GS,
E2 connectivity, and the RAN pods before continuing.

## Reproducibility

Application source checkouts and deployable image tags are pinned. Do not use
`latest` for release deployments. Base image patch digests are not pinned yet;
that is tracked separately because digest pinning must cover both amd64 and
arm64 images used by the NMI and CIC environments.

The Open5GS v2.7.7 WebUI dependency lock currently reports vulnerable legacy
npm packages during the image build. Node.js itself is on a supported LTS line,
but the application dependency tree is an upstream risk. Do not apply a forced
major-version `npm audit` rewrite without an application migration and an
end-to-end subscriber-management test.

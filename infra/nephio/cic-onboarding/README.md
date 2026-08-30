# CIC workload-cluster onboarding

This directory completes the Nephio workload-cluster registration for the CIC
ARM64 cluster. Nephio and Porch stay in the NMI management namespace; only the
minimum GitOps runtime (`source-controller` and `kustomize-controller`) runs in
the CIC cluster.

## Data path

1. Porch publishes an approved package to the `cic` Gitea repository in NMI.
2. NMI exposes read-only HTTP access to the lab networks at
   `http://192.168.72.10:30302/nephio/cic.git`.
3. Flux in CIC pulls the repository and reconciles the selected package.
4. The `nephio-deployer` service account can modify only ConfigMaps in the
   `nephio-lab` namespace for this smoke test.

The Gitea repository is intentionally public inside the routed laboratory
networks. Porch still uses a generated token for writes. Do not publish the
NodePort through the pfSense WAN.

## Reproduce

Run `prepare-repository.sh` with the NMI cluster as the current kubectl context.
Run `onboard-workload.sh` with the CIC cluster as the current context.

Flux v2.7.5 is pinned because v2.7 is the newest Flux minor supporting
Kubernetes 1.32. Its official ARM64 archive is verified before execution. The
installer deploys two controllers instead of the default full Flux suite.

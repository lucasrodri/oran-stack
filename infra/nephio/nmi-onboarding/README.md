# NMI Nephio onboarding

Run after `install-management.sh` has made all Nephio and Flux controllers
Ready. The scripts expect `kubectl`, `porchctl`, the NMI admin context, and the
repository root (including the packages under `packages/nephio/`).

```bash
export KUBECONFIG=/etc/nephio/nmi-admin.conf
sudo -E ./infra/nephio/nmi-onboarding/onboard-nmi.sh
```

The order is intentional:

1. create the internal Gitea repository and separate tokens;
2. wait for both token Secrets before registering the repository with Porch;
3. create the restricted local Flux identity;
4. publish the smoke package through the Porch lifecycle;
5. start Flux reconciliation and verify the resulting ConfigMap.

Neither script prints token or password values. Rerunning the onboarding is
safe after the package is Published; the publish script detects and reuses it.

## r4-simple-mon package

Publish the known-good xApp baseline, grant Flux access only to `ricxapp`, and
start reconciliation:

```bash
./publish-xapp-package.sh ../../../packages/nephio/r4-simple-mon
kubectl apply -f xapp-rbac.yaml
kubectl apply -f xapp-flux-sync.yaml
```

On the first handoff from Helm to Flux, run `stabilize-xapp-rmr.sh` once after
the Kustomization is Ready. It restarts RTMgr, removes the previous REST
subscription and recreates only the xApp pod. It deliberately never restarts
E2Term, preserving the O-DU SCTP association.

The repeatable classroom demonstration creates two new Porch revisions: a
harmless `tuned` update and a forward rollback copied from the v1 baseline.

```bash
./demo-xapp-update-rollback.sh
```

`verify-xapp-package.sh` requires Flux Ready, the expected package metadata,
one active subscription and a real `RIC Indication Received` before succeeding.

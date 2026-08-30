# NMI Nephio onboarding

Run after `install-management.sh` has made all Nephio and Flux controllers
Ready. The scripts expect `kubectl`, `porchctl`, the NMI admin context, and the
repository root (including `packages/nephio/nmi-lab-smoke`).

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

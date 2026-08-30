# Nephio xApp blueprints

This directory creates the WebUI-visible `team-blueprints` repository, publishes
the reusable `r4-simple-mon` package and specializes it for the NMI workload
cluster with a Porch `PackageVariant`.

Run from the Nephio worker with the NMI admin kubeconfig:

```bash
export KUBECONFIG=/etc/nephio/nmi-admin.conf
sudo -E ./infra/nephio/blueprints/onboard-blueprints.sh
kubectl apply -f infra/nephio/nmi-onboarding/xapp-flux-sync.yaml
```

The site inventory is stored as `WorkloadCluster` resources. The blueprint
injects the selected site's values and executes `apply-replacements` before the
downstream package is published. Flux only consumes the downstream deployment
package; it never applies the blueprint directly.

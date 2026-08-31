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

For a new student xApp, generate the Python entry point, reusable blueprint,
NMI variant and restricted Flux identity with:

```bash
./scripts/new-kpm-xapp.sh kpm-latency-lab DRB.UEThpDl 2000
```

Publish any generated blueprint and approve its downstream variant with the
generic helpers:

```bash
sudo -E ./infra/nephio/blueprints/publish-xapp-blueprint.sh \
  kpm-latency-lab packages/nephio/kpm-latency-lab v1
kubectl apply -f infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml
sudo -E ./infra/nephio/blueprints/approve-packagevariant.sh \
  kpm-latency-lab-nmi
```

The complete student workflow, acceptance checks and safe update/rollback
procedure are documented in
[`docs/STUDENT_XAPP_LAB.md`](../../../docs/STUDENT_XAPP_LAB.md).

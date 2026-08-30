# Nephio R6 WebUI package parser compatibility patch

The pinned R6 WebUI bundle parses every `*.yaml` file returned by Porch as a
Kubernetes resource and dereferences `metadata.name` unconditionally. A valid
Kustomize `kustomization.yaml` commonly has no metadata, which makes the package
details page throw a JavaScript `TypeError` even though Porch and Flux remain
healthy.

The init container copies the immutable upstream static bundle to an `emptyDir`
and adds the missing metadata guard. It fails closed if the expected minified
expression or chunk changes, preventing an unnoticed patch against a different
WebUI release. Remove this overlay when the pinned upstream image contains an
equivalent guard.

Apply it to an existing installation with:

```bash
kubectl apply -f infra/nephio/webui-compat/patch-configmap.yaml
kubectl patch deployment nephio-webui -n nephio-webui --type=strategic \
  --patch-file=infra/nephio/webui-compat/deployment-patch.yaml
kubectl rollout status deployment/nephio-webui -n nephio-webui
```

Browsers that previously cached the hashed chunk need one hard refresh.

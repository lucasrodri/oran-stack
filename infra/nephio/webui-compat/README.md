# Nephio R6 WebUI laboratory overlay

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

The overlay also keeps the laboratory identity and access path explicit:

- `unb-configmap.yaml` sets the external NMI VPN URL, keeps the Nephio title,
  embeds the [official 2025 UnB logo](https://cen.unb.br/wp-content/uploads/2025/02/logo_unb_oficial_2025.png)
  and clears the upstream decorative background;
- `nodeport-service.yaml` publishes the WebUI on TCP `30707`;
- pfSense must allow only the NMI VPN network to reach
  `192.168.71.30:30707`.

Apply it to an existing installation with:

```bash
kubectl apply -f infra/nephio/webui-compat/patch-configmap.yaml
kubectl apply -f infra/nephio/webui-compat/unb-configmap.yaml
kubectl apply -f infra/nephio/webui-compat/nodeport-service.yaml
kubectl patch deployment nephio-webui -n nephio-webui --type=strategic \
  --patch-file=infra/nephio/webui-compat/deployment-patch.yaml
kubectl rollout status deployment/nephio-webui -n nephio-webui
```

Browsers that previously cached the hashed chunk need one hard refresh.

VPN URL: `http://192.168.71.30:30707/config-as-data`

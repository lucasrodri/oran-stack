# Near-RT RIC image supply chain

The Linux Foundation Nexus registry referenced by the O-RAN SC deployment
recipes currently returns HTTP 402 to unauthenticated pulls. This repository
therefore rebuilds the Near-RT RIC M-release images from pinned official source
commits and publishes them under:

```text
ghcr.io/lucasrodri/oran-stack/<image>:<version>
```

The workflow is `.github/workflows/ric-m-images.yml`.

## Provenance

| Image | Version | Official repository | Pinned commit |
| --- | --- | --- | --- |
| ric-plt-a1 | 3.2.3 | o-ran-sc/ric-plt-a1 | 09a757b4fd63198d8690d50b52bfd04552d47f1f |
| ric-plt-appmgr | 0.5.10 | o-ran-sc/ric-plt-appmgr | 2f70f24239e3f9281b899b7d5b4807cf36e062d1 |
| ric-plt-dbaas | 0.6.5 | o-ran-sc/ric-plt-dbaas | 23c983c62fa8f1677351ced9fbfe65c64375edb9 |
| ric-plt-e2 | 6.0.8 | o-ran-sc/ric-plt-e2 | ccd8f31d9699277fb88ffb2049b6a09b65485cf3 |
| ric-plt-e2mgr | 6.0.8 | o-ran-sc/ric-plt-e2mgr | 69e847fc3e4a66e3f8aea652624da98054d2bdb0 |
| ric-plt-rtmgr | 0.9.7 | o-ran-sc/ric-plt-rtmgr | c794f21a206c6cab2e352128201333a5924aee61 |
| ric-plt-submgr | 0.10.4 | o-ran-sc/ric-plt-submgr | 191c81a6c587cde692345b50da94e7cdae8c56d8 |

The deployment versions come from the official M-release recipe. Some source
repositories retain the preceding value in `container-tag.yaml` after a
maintenance build, so the deployment recipe is authoritative for the
published image tag while the commit SHA is authoritative for the source.

## Architecture status

The publication target is `linux/amd64`, matching the Dell/Intel NMI servers.
This is intentional: the official M-release Dockerfiles download amd64-only
Go/Swagger archives and RMR/mdclog Debian packages and copy files from
`x86_64-linux-gnu` paths. ARM64/CIC is outside the scope of this deployment.

The Helm chart must continue using the validated NMI image set until the
workflow publishes every required M-release image and an end-to-end E2 test
passes.

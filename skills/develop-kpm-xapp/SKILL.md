---
name: develop-kpm-xapp
description: >-
  Scaffold, implement, test, and package a new E2SM-KPM monitoring xApp in
  oran-stack. Use when the user asks to create, develop, or extend a KPM xApp,
  follow the student xApp lab, run new-kpm-xapp.sh, or repeat the kpm-mon-tmt
  or kpm-load-watch pattern.
---

# Develop a KPM xApp

Build a receive-only E2SM-KPM monitor. The xApp subscribes, classifies indications, and exports metrics. It does not register the UE, configure Open5GS, or send RAN control.

Human walkthroughs, in Portuguese: `docs/STUDENT_XAPP_LAB.md` (full lab) and `docs/INFRA_XAPP_QUICKSTART.md` (restricted infra account). Read the matching section before publishing, accepting on the cluster, or diagnosing a live failure. Do not invent NodePorts, pfSense bridges, or writes to `ran`, `5g-core`, or `near-rt-ric`.

## Workflow

Copy this checklist and track it:

```
- [ ] Branch from updated main (`aluno/<name>` or `lab/<name>`)
- [ ] Scaffold with scripts/new-kpm-xapp.sh
- [ ] Implement indication_callback and algorithm metrics
- [ ] Unit-test without starting the RIC runtime
- [ ] Commit the placeholder digest and let CI build amd64+arm64
- [ ] Pin the index digest, then stop
- [ ] Hand publish / Flux / traffic acceptance to the lab docs
```

### 1. Scaffold

```bash
./scripts/new-kpm-xapp.sh <dns-name> <KPM-metric> <report-period-ms>
```

- Name: 3–31 chars, `^[a-z][a-z0-9-]{2,30}$`. The generator refuses to overwrite an existing xApp.
- Metric: `DRB.UEThpUl` or `DRB.UEThpDl`. This O-DU implements those. `DRB.PacketSuccessRateUlgNBUu` let counters advance while the KPI stayed unusable; `kpm-mon-tmt` was corrected to `DRB.UEThpUl`.
- Period: integer 100–60000 ms. SubMgr merges identical metric+period subscriptions, so only one xApp receives. `r4-simple-mon` on NMI uses `DRB.UEThpDl` at 1000 ms. `kpm-load-watch` uses downlink. Pick a different metric or a different period from every xApp already subscribed.
- First deploy is NMI only. The generator deletes `services-external.yaml` on purpose. CIC NodePorts are an infrastructure step.

The command writes:

| Path | Role |
|---|---|
| `xapps/python/<name_underscores>_xapp.py` | Process in the shared image |
| `packages/nephio/<name>/` | Team Blueprint |
| `infra/nephio/blueprints/<name>-nmi-variant.yaml` | NMI PackageVariant |
| `infra/nephio/nmi-onboarding/<name>-rbac.yaml` | Flux identity limited to Deployment, Service, ConfigMap in `ricxapp` |
| `infra/nephio/nmi-onboarding/<name>-flux-sync.yaml` | Flux reconciliation |

`Dockerfile.xapps` copies all of `xapps/python/`. Do not add a per-xApp Dockerfile.

### 2. Program only the callback

`xAppBase` already registers with AppMgr, answers the subscription HTTP call, runs the RMR loop, ACKs RTMgr route updates (type 20 → type 22), and exports decoded samples at `/metrics`. Extend `indication_callback`. Keep it non-blocking. Log the first indication and then every `log_every` (default 30). Prometheus is the durable record.

`kpm-mon-tmt` is the pattern for a small algorithm on top of the scaffold:

- Bounded moving average (`collections.deque`, default window 5) plus a finite threshold.
- States `unknown`, `idle`, `active`. The sample that leaves `unknown` is not a transition.
- Build the lock and the deque **before** `super().__init__`. `xAppBase` starts the HTTP server inside `__init__`; a scrape can race `_state_lock` otherwise.
- Ignore a missing or non-numeric sample (`_latest_numeric` returns `None`).
- Append algorithm series from `_metrics_handler` after `super()`, prefixed `oran_<name_underscores>_`. One gauge for the average, counters for samples, idle samples, and transitions, plus a one-hot state gauge and the configured threshold.
- Pass window and threshold as constructor and CLI arguments so tests can vary them. Report period, metric, E2 node, and image already flow from `WorkloadCluster` annotations through `apply-replacements.yaml`. Do not hide experiment knobs that must change per lab run inside a rebuilt image when an annotation can carry them.

Do not send an E2 control action in the first version.

### 3. Test without the RIC

Follow `tests/test_kpm_mon_tmt_xapp.py`: insert a stub `lib.xAppBase` into `sys.modules` before loading the xApp file, then restore the previous modules. The real base starts RMR and HTTP.

Cover:

- average at the threshold stays on the healthy side of the comparison (`>=`)
- the sample that falls out of the window changes the average
- leaving `unknown` does not increment transitions; a later change does
- `/metrics` text contains the average, counts, and exactly one active state
- `window_size < 1` and a non-finite threshold raise `ValueError`

Add the test file to the path filters and the `python3 -m unittest` invocation in `.github/workflows/xapp-multiarch.yml`.

Before the image build:

```bash
python3 -m py_compile xapps/python/<name_underscores>_xapp.py
python3 -m unittest tests/test_<name_underscores>_xapp.py
rg 'REPLACE_WITH_MULTIARCH_IMAGE_DIGEST' packages/nephio/<name> infra/nephio/blueprints/<name>-nmi-variant.yaml
git diff --check
```

The `rg` must still match. The digest does not exist yet.

### 4. Pin the index digest

Commit and push the scaffold with `REPLACE_WITH_MULTIARCH_IMAGE_DIGEST` still in place. Wait until `Build multi-architecture laboratory xApps` has published both `linux/amd64` and `linux/arm64`.

Replace the placeholder with the **index** digest, never a single-platform digest and never `:latest`:

```text
ghcr.io/lucasrodri/oran-stack/oran-xapps@sha256:<64 hex digits>
```

Put that reference in:

- `packages/nephio/<name>/workload-cluster.yaml` annotation `oran.unb.br/xapp-image`
- `infra/nephio/blueprints/<name>-nmi-variant.yaml` (same annotation)
- `packages/nephio/<name>/deployment.yaml` container `xapp` image, if it still carries the copied `r4-simple-mon` digest

`apply-replacements.yaml` copies the annotation onto the Deployment at publish time. The committed Deployment image still has to match, which is the extra edit `kpm-mon-tmt` needed after the first pin. A pin made before the real multiarch build was thrown away and replaced; do not guess a digest.

`rg 'REPLACE_WITH|:latest'` on the package and the variant must be empty. Commit the digest on its own.

Keep `RMR_FLAGS=1` (`oran.unb.br/rmr-flags: "1"`). A receive-only xApp has one TCP listener on 4561. A second listener on that port makes RMR intermittent.

### 5. Publish and accept

Stop at the digest commit unless the user is doing the administrative promotion. Then follow `docs/STUDENT_XAPP_LAB.md` sections 6–9 exactly:

- `publish-xapp-blueprint.sh` on the Nephio worker, then apply the PackageVariant and `approve-packagevariant.sh`
- Flux RBAC and kustomization Ready
- Pod Ready, AppMgr registration, `active_subscriptions 1`, RMR and KPM counters increasing, one listener on 4561
- `XAPP_DEPLOYMENT=<name> ./scripts/demo-kpm.sh` for traffic. Acceptance is HTTP 200, KPI above zero, `DEMO_KPM_OK`

An update is a new Porch revision (`v2`), including `workspaceName`, package-revision annotations, and the runtime checksum. Roll back by copying the known revision into a newer one. Do not `git reset` a Published PackageRevision or move published tags.

## Failure checks

| Symptom | Check |
|---|---|
| Init container waits | E2 node missing or `DISCONNECTED` in E2Mgr |
| Subscribed, counters frozen after a DU restart | New E2 association dropped old subscriptions. Recreate the stateless xApp pods. Leave E2Term up if it is already registered. `scripts/recover-ran-zmq.sh` when ZMQ endpoints are stale |
| Counters move, KPI stays 0 | UE is idle, or the metric is not implemented by this O-DU |
| Two xApps, only one receives | Same metric and same period |
| Two listeners on 4561 | `RMR_FLAGS` must be `1` |
| Grafana `No Data` | Service needs `monitoring=true`; Prometheus target up; scrape has happened |
| NMI image fails on CIC | Manifest index has no `linux/arm64` |

After a full lab outage, use `docs/LAB_RECOVERY.md` before retesting the xApp.

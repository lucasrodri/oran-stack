# O-RAN lab observability

The NMI workload cluster runs a persistent observability plane on the physical
`nmi-srv03` worker. The O-RAN workloads remain distributed across the control
plane and the two Proxmox workers.

## Components

| Component | Purpose | Persistence |
|---|---|---|
| Prometheus | Kubernetes, core, RIC and xApp metrics | 20 GiB, 7 days |
| Grafana | Dashboards and data-source UI | 5 GiB |
| Alertmanager | Groups and displays lab alerts | 2 GiB, 5 days |
| Loki | O-RAN and monitoring container-log store | 20 GiB, 24 hours |
| Alloy | One log collector on every Kubernetes node | Stateless |

All persistent claims use the `local-path` StorageClass and are pinned by pod
scheduling to `nmi-srv03`. This is persistent across pod restarts, but it is not
high availability: loss of that physical disk still requires backup recovery.

## Access through the NMI VPN

- Grafana: `http://192.168.72.10:30300`
- Alertmanager: `http://192.168.72.10:30301`
- Grafana dashboard: `O-RAN Stack Overview`
- Grafana log dashboard: `O-RAN Kubernetes Logs`

The Grafana Loki data source is provisioned automatically. Alloy only forwards
the `5g-core`, `near-rt-ric`, `ricxapp`, `ran` and `monitoring` namespaces. Use
the log dashboard filters to narrow by namespace, container or free text. Normal
RAN and UE logging is set to `warning`; raise it temporarily only for a bounded
debug session and restore it afterward. Alloy also discards routine successful
metric scrapes and per-second KPM/RLC report lines before Loki; their durable
representation is the corresponding Prometheus time series.

## Lab alerts

The chart installs alerts for Kubernetes nodes, pod crash loops, E2Term, the
`r4-simple-mon` xApp, the simulated UE, stale KPM indications, RMR receive errors
and monitoring storage usage. Alertmanager currently uses a local UI receiver;
an email, Matrix or webhook receiver can be added after the lab chooses an
operational destination.

## Storage caveat and backup

Dashboard definitions and alert rules are stored in Git and can be recreated by
Ansible. The time-series and log PVC contents are not yet backed up. Before this
becomes production-like, add scheduled volume snapshots or file-level backups to
storage outside `nmi-srv03` and run a restore test.

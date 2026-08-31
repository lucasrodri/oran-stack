# O-RAN lab observability

The NMI workload cluster runs the laboratory observability plane on the
physical `nmi-srv03` worker. It now provides one view of the NMI `amd64` cluster
and the remote CIC `arm64` cluster. The O-RAN workloads remain distributed
across the NMI control plane and its two Proxmox workers.

## Components

| Component | Purpose | Persistence |
|---|---|---|
| Prometheus | Kubernetes, core, RIC and xApp metrics | 20 GiB, 7 days |
| Grafana | Dashboards and data-source UI | 5 GiB |
| Alertmanager | Groups and displays lab alerts | 2 GiB, 5 days |
| Loki | O-RAN and monitoring container-log store | 20 GiB, 24 hours |
| Alloy | One log collector on every Kubernetes node | Stateless |
| CIC metrics relay | Forwards node, object and ARM xApp metrics through VM 105 | Stateless, no access log |
| CIC node-exporter | CPU, memory, disk and network for both ARM VMs | Stateless |
| CIC kube-state-metrics | Node, Pod, namespace and workload state | Stateless |

All persistent claims use the `local-path` StorageClass and are pinned by pod
scheduling to `nmi-srv03`. This is persistent across pod restarts, but it is not
high availability: loss of that physical disk still requires backup recovery.

## Access through the NMI VPN

- Grafana: `http://192.168.72.10:30300`
- Alertmanager: `http://192.168.72.10:30301`
- Grafana dashboard: `O-RAN Stack Overview`
- Grafana log dashboard: `O-RAN Kubernetes Logs`
- Grafana multi-site dashboard: `O-RAN Multi-Site Lab`

Direct multi-site dashboard URL:
`http://192.168.72.10:30300/d/oran-multisite/cic-arm-lab`

The Grafana Loki data source is provisioned automatically. Alloy only forwards
the `5g-core`, `near-rt-ric`, `ricxapp`, `ran` and `monitoring` namespaces. Use
the log dashboard filters to narrow by namespace, container or free text. Normal
RAN and UE logging is set to `warning`; raise it temporarily only for a bounded
debug session and restore it afterward. Alloy also discards routine successful
metric scrapes and per-second KPM/RLC report lines before Loki; their durable
representation is the corresponding Prometheus time series.

## CIC ARM metrics path

The physical Prometheus node does not have a direct route to the CIC
`192.168.0.0/24` laboratory LAN. VM 105 (`oran-k8s-01`, `192.168.72.10`) does.
The chart therefore pins a small, TCP-only HAProxy relay to VM 105:

```text
cic-k8s-cp01:9100 ----\
cic-k8s-w01:9100 ------> VM 105 relay ---> NMI Prometheus ---> Grafana
CIC kube-state:30102 --/
CIC simple-mon:30691 --/
```

HAProxy does not terminate HTTP, inspect metric contents or retain access logs.
This design avoids a broad new firewall rule. The pfSense CIC configuration was
left unchanged because all three targets return HTTP 200 from VM 105.

Prometheus attaches `cluster="cic-arm"`, `site="cic"` and
`architecture="arm64"` labels to the remote series. This prevents CIC
kube-state-metrics from being confused with the NMI cluster's local metrics.
The xApp scrape is labeled `job="cic-simple-mon"`, `site="cic"`,
`architecture="arm64"` and `xapp="r4-simple-mon-cic"`. The multi-site
dashboard shows its active subscription and KPM indication rate; an idle
simulated UE may legitimately report a `DRB.UEThpDl` value of zero while the
indication counter continues to increase.

## Lab alerts

The chart installs alerts for Kubernetes nodes, pod crash loops, E2Term, the
`r4-simple-mon` xApp, the simulated UE, stale KPM indications, RMR receive
errors, monitoring storage and the CIC metric targets. Alertmanager uses
a local UI receiver, which is sufficient for this laboratory PoC.

## Laboratory storage boundary

Dashboard definitions and alert rules are stored in Git and can be recreated.
Time-series and log PVC contents are intentionally treated as disposable lab
data; this PoC does not claim high availability or production backup.

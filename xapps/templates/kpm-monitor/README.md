# KPM student xApp template

This template is consumed by `scripts/new-kpm-xapp.sh`. It deliberately starts
with E2SM-KPM Report Style 1 and node-level measurements. `xAppBase` handles
AppMgr registration, SubMgr subscription callbacks, RMR delivery and the
standard Prometheus metrics. The student callback is the extension point for a
new algorithm.

The callback prints only the first indication and every thirtieth indication by
default. Do not add per-indication debug output to normal laboratory runs;
decoded values are already available at `/metrics`.

Generate a copy with:

```bash
./scripts/new-kpm-xapp.sh <dns-safe-name> [KPM-metric] [report-period-ms]
```

Use a report period distinct from concurrently running xApps that request the
same metric. Otherwise SubMgr may merge the equivalent requests into one E2
subscription, which prevents an independent per-xApp experiment in this lab.

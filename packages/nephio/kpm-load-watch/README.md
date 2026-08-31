# kpm-load-watch blueprint

Reusable Nephio KRM blueprint for the laboratory E2SM-KPM monitoring xApp.
The blueprint is specialized from an injected `WorkloadCluster` object. Site,
target node, container image, E2 node and KPM metric are copied into the
Kubernetes Deployment by the package pipeline.

The package does not deploy the Near-RT RIC or the RAN. It assumes that the
target site provides compatible RIC endpoints and that the selected image
supports the site's CPU architecture.

`kpm-load-watch` computes a moving average over `DRB.UEThpDl` and classifies
the current cell load as `idle`, `active` or `busy`. The package exposes the
window and both thresholds as `WorkloadCluster` annotations so a PackageVariant
can express site-specific intent without changing the Python code.

Additional Prometheus series:

- `oran_kpm_load_watch_average_kbps`;
- `oran_kpm_load_watch_state{state="idle|active|busy"}`;
- `oran_kpm_load_watch_state_transitions_total`;
- `oran_kpm_load_watch_samples_total`.

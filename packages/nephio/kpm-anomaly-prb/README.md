# kpm-anomaly-prb blueprint

Reusable Nephio KRM blueprint for the per-UE anomaly xApp. It subscribes to
KPM Report Style 4 for `DRB.RlcPacketDropRateDl` and, once two UE IDs have
been seen, sends E2SM-RC Style 2 Action 6 with a zero PRB quota to each UE
whose moving average reaches the threshold.

The blueprint is specialized from an injected `WorkloadCluster` object. Site,
target node, container image, E2 node, KPM metric, window, threshold and
minimum UE count are copied into the Kubernetes Deployment by the package
pipeline.

The package does not deploy the Near-RT RIC or the RAN. It assumes that the
target site provides compatible RIC endpoints and that the selected image
supports the site's CPU architecture.

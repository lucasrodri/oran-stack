#!/usr/bin/env python3
"""Per-UE KPM monitor that starves an anomalous UE via E2SM-RC.

OCUDU 26.04 accepts one RIC Control: E2SM-RC Style 2 Action 6 (slice PRB
quota). This xApp subscribes to KPM Report Style 4 for DRB.RlcPacketDropRateDl,
the downlink RLC SDU drop rate reported by the DU. A UE is anomalous when the
moving average of that rate stays at or above the threshold. RRC Connection
Release is not implemented by this RAN.
"""

import argparse
import math
import signal
import threading

from lib.xAppBase import xAppBase


class AnomalyPrbXapp(xAppBase):
    STATES = ("unknown", "monitoring", "acted")

    def __init__(
        self,
        config,
        http_server_port,
        rmr_port,
        window_size,
        anomaly_threshold,
        min_ues,
        metric_name="DRB.RlcPacketDropRateDl",
        log_every=30,
    ):
        if window_size < 1:
            raise ValueError("window_size must be positive")
        if min_ues < 1:
            raise ValueError("min_ues must be positive")
        if not math.isfinite(anomaly_threshold):
            raise ValueError("anomaly_threshold must be finite")

        # xAppBase starts the HTTP server during initialization. Build the
        # state first so an early Prometheus scrape cannot race _state_lock.
        self.log_every = max(1, log_every)
        self.indication_count = 0
        self.window_size = window_size
        self.anomaly_threshold = float(anomaly_threshold)
        self.min_ues = min_ues
        self.metric_name = metric_name
        self._samples = {}
        self._seen = set()
        self._controlled = set()
        self._pending_controls = []
        self._sample_count = 0
        self._controls_sent = 0
        self._last_average = 0.0
        self._state = "unknown"
        self._state_lock = threading.Lock()
        super(AnomalyPrbXapp, self).__init__(config, http_server_port, rmr_port)
        self.control_outcome_callback = self._on_control_outcome

    def _on_control_outcome(self, outcome):
        with self._state_lock:
            ue_id = self._pending_controls.pop(0) if self._pending_controls else None
        label = "RIC_CONTROL_ACK" if outcome == "ack" else "RIC_CONTROL_FAILURE"
        print(
            "kpm-anomaly-prb: {0} ue_id={1}".format(label, ue_id),
            flush=True,
        )
        return ue_id

    def _snapshot(self):
        return {
            "average": self._last_average,
            "samples": self._sample_count,
            "ues_seen": len(self._seen),
            "controls": self._controls_sent,
            "state": self._state,
        }

    def _metrics_handler(self, name, path, data, ctype):
        response = super(AnomalyPrbXapp, self)._metrics_handler(
            name, path, data, ctype
        )
        with self._state_lock:
            snapshot = self._snapshot()
        payload = response["payload"]
        payload += (
            "# HELP oran_kpm_anomaly_prb_drop_rate_average Latest per-UE moving average of the downlink RLC drop rate.\n"
            "# TYPE oran_kpm_anomaly_prb_drop_rate_average gauge\n"
            "oran_kpm_anomaly_prb_drop_rate_average {:.12g}\n"
            "# HELP oran_kpm_anomaly_prb_samples_total Valid per-UE samples processed.\n"
            "# TYPE oran_kpm_anomaly_prb_samples_total counter\n"
            "oran_kpm_anomaly_prb_samples_total {}\n"
            "# HELP oran_kpm_anomaly_prb_ues_seen Distinct UE IDs observed.\n"
            "# TYPE oran_kpm_anomaly_prb_ues_seen gauge\n"
            "oran_kpm_anomaly_prb_ues_seen {}\n"
            "# HELP oran_kpm_anomaly_prb_controls_total Style 2 Action 6 controls sent.\n"
            "# TYPE oran_kpm_anomaly_prb_controls_total counter\n"
            "oran_kpm_anomaly_prb_controls_total {}\n"
            "# HELP oran_kpm_anomaly_prb_state Whether the xApp is still waiting, watching, or has acted.\n"
            "# TYPE oran_kpm_anomaly_prb_state gauge\n"
        ).format(
            snapshot["average"],
            snapshot["samples"],
            snapshot["ues_seen"],
            snapshot["controls"],
        )
        for state in self.STATES:
            payload += 'oran_kpm_anomaly_prb_state{{state="{}"}} {}\n'.format(
                state, int(snapshot["state"] == state)
            )
        payload += (
            "# HELP oran_kpm_anomaly_prb_anomaly_threshold Configured drop-rate threshold.\n"
            "# TYPE oran_kpm_anomaly_prb_anomaly_threshold gauge\n"
            "oran_kpm_anomaly_prb_anomaly_threshold {:.12g}\n"
        ).format(self.anomaly_threshold)
        response["payload"] = payload
        return response

    def observe_ues(self, e2_agent_id, samples):
        """Update per-UE averages and send Style 2 Action 6 at most once.

        samples maps gNB-CU-UE-F1AP-ID to the latest drop rate.
        No control is sent until at least min_ues distinct IDs have been seen.
        """
        acted = []
        with self._state_lock:
            for ue_id, value in samples.items():
                latest = self._latest_numeric(value)
                if latest is None:
                    continue
                window = self._samples.setdefault(ue_id, [])
                window.append(latest)
                if len(window) > self.window_size:
                    del window[0]
                self._seen.add(ue_id)
                self._sample_count += 1
                average = sum(window) / float(len(window))
                if self._state == "unknown":
                    self._state = "monitoring"
                if self._sample_count == 1 or self._sample_count % self.log_every == 0:
                    print(
                        "kpm-anomaly-prb: ue_id={0} drop_rate={1:.1f} "
                        "average_drop_rate={2:.1f}".format(ue_id, latest, average),
                        flush=True,
                    )

            averages = [
                sum(window) / float(len(window))
                for window in self._samples.values()
                if window
            ]
            if averages:
                self._last_average = max(averages)

            if len(self._seen) < self.min_ues:
                return acted

            for ue_id, window in list(self._samples.items()):
                if not window or ue_id in self._controlled:
                    continue
                average = sum(window) / float(len(window))
                if average < self.anomaly_threshold:
                    continue
                self._controlled.add(ue_id)
                self._pending_controls.append(ue_id)
                self._controls_sent += 1
                self._state = "acted"
                acted.append((ue_id, average))

        for ue_id, average in acted:
            print(
                "kpm-anomaly-prb: anomaly ue_id={0} average_drop_rate={1:.1f} "
                "-> RIC Control Style 2 Action 6 max_prb=0".format(ue_id, average),
                flush=True,
            )
            self.e2sm_rc.control_slice_level_prb_quota(
                e2_agent_id,
                ue_id,
                min_prb_ratio=0,
                max_prb_ratio=0,
                dedicated_prb_ratio=0,
                ack_request=1,
            )
        return [ue_id for ue_id, _average in acted]

    def indication_callback(self, e2_agent_id, subscription_id, indication_hdr, indication_msg):
        self.indication_count += 1
        measurements = self.e2sm_kpm.extract_meas_data(indication_msg)
        samples = {}
        for ue_id, ue_meas_data in measurements.get("ueMeasData", {}).items():
            values = ue_meas_data.get("measData", {}).get(self.metric_name)
            if values is None:
                continue
            samples[ue_id] = values
        if not samples:
            return []
        return self.observe_ues(e2_agent_id, samples)

    @xAppBase.start_function
    def start(self, e2_node_id, metric_names, report_period, granul_period):
        matching_ue_conds = [{
            "testCondInfo": {
                "testType": ("ul-rSRP", "true"),
                "testExpr": "lessthan",
                "testValue": ("valueInt", 1000),
            }
        }]
        print(
            "kpm-anomaly-prb: subscribing node={0} style=4 metrics={1}".format(
                e2_node_id, metric_names
            ),
            flush=True,
        )
        self.e2sm_kpm.subscribe_report_service_style_4(
            e2_node_id,
            report_period,
            matching_ue_conds,
            metric_names,
            granul_period,
            self.indication_callback,
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Starve an anomalous UE with E2SM-RC Style 2 Action 6"
    )
    parser.add_argument("--config", default="")
    parser.add_argument("--http_server_port", type=int, default=8091)
    parser.add_argument("--rmr_port", type=int, default=4561)
    parser.add_argument("--e2_node_id", required=True)
    parser.add_argument("--ran_func_id", type=int, default=2)
    parser.add_argument("--kpm_report_style", type=int, choices=[4], default=4)
    parser.add_argument("--metrics", default="DRB.RlcPacketDropRateDl")
    parser.add_argument("--report_period", type=int, default=1000)
    parser.add_argument("--granul_period", type=int, default=1000)
    parser.add_argument("--log_every", type=int, default=30)
    parser.add_argument("--window_size", type=int, default=5)
    parser.add_argument("--anomaly_threshold", type=float, default=1.0)
    parser.add_argument("--min_ues", type=int, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app = AnomalyPrbXapp(
        args.config,
        args.http_server_port,
        args.rmr_port,
        args.window_size,
        args.anomaly_threshold,
        args.min_ues,
        args.metrics.split(",")[0],
        args.log_every,
    )
    app.e2sm_kpm.set_ran_func_id(args.ran_func_id)

    signal.signal(signal.SIGQUIT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    signal.signal(signal.SIGINT, app.signal_handler)

    app.start(
        args.e2_node_id,
        args.metrics.split(","),
        args.report_period,
        args.granul_period,
    )

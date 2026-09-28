#!/usr/bin/env python3
"""Per-UE KPM monitor that starves an anomalous UE via E2SM-RC.

OCUDU 26.04 accepts one RIC Control: E2SM-RC Style 2 Action 6 (slice PRB
quota). This xApp subscribes to KPM Report Style 4 so each connected UE has
its own DRB.UEThpDl, and sends that control once for a UE whose moving
average stays at or above the anomaly threshold. RRC Connection Release is
not implemented by this RAN.
"""

import argparse
import signal

from lib.xAppBase import xAppBase


class AnomalyPrbXapp(xAppBase):
    def __init__(
        self,
        config,
        http_server_port,
        rmr_port,
        window_size,
        anomaly_threshold_kbps,
        min_ues,
    ):
        super(AnomalyPrbXapp, self).__init__(config, http_server_port, rmr_port)
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.anomaly_threshold_kbps = float(anomaly_threshold_kbps)
        self.min_ues = min_ues
        self._samples = {}
        self._seen = set()
        self._controlled = set()
        self._pending_controls = []
        self.control_outcome_callback = self._on_control_outcome

    def _on_control_outcome(self, outcome):
        ue_id = self._pending_controls.pop(0) if self._pending_controls else None
        label = "RIC_CONTROL_ACK" if outcome == "ack" else "RIC_CONTROL_FAILURE"
        print(
            "kpm-anomaly-prb: {0} ue_id={1}".format(label, ue_id),
            flush=True,
        )
        return ue_id

    def observe_ues(self, e2_agent_id, samples):
        """Update per-UE averages and send Style 2 Action 6 at most once.

        samples maps gNB-CU-UE-F1AP-ID to the latest DRB.UEThpDl in kbps.
        No control is sent until at least min_ues distinct IDs have been seen.
        """
        acted = []
        for ue_id, value in samples.items():
            latest = self._latest_numeric(value)
            if latest is None:
                continue
            window = self._samples.setdefault(ue_id, [])
            window.append(latest)
            if len(window) > self.window_size:
                del window[0]
            self._seen.add(ue_id)
            average = sum(window) / float(len(window))
            print(
                "kpm-anomaly-prb: ue_id={0} throughput_kbps={1:.1f} "
                "average_kbps={2:.1f}".format(ue_id, latest, average),
                flush=True,
            )

        if len(self._seen) < self.min_ues:
            return acted

        for ue_id, window in list(self._samples.items()):
            if not window or ue_id in self._controlled:
                continue
            average = sum(window) / float(len(window))
            if average < self.anomaly_threshold_kbps:
                continue
            self._controlled.add(ue_id)
            self._pending_controls.append(ue_id)
            print(
                "kpm-anomaly-prb: anomaly ue_id={0} average_kbps={1:.1f} "
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
            acted.append(ue_id)
        return acted

    def indication_callback(self, e2_agent_id, subscription_id, indication_hdr, indication_msg):
        measurements = self.e2sm_kpm.extract_meas_data(indication_msg)
        samples = {}
        for ue_id, ue_meas_data in measurements.get("ueMeasData", {}).items():
            values = ue_meas_data.get("measData", {}).get("DRB.UEThpDl")
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
    parser.add_argument("--http_server_port", type=int, default=8093)
    parser.add_argument("--rmr_port", type=int, default=4563)
    parser.add_argument("--e2_node_id", required=True)
    parser.add_argument("--ran_func_id", type=int, default=2)
    parser.add_argument("--kpm_report_style", type=int, choices=[4], default=4)
    parser.add_argument("--metrics", default="DRB.UEThpDl")
    parser.add_argument("--report_period", type=int, default=1000)
    parser.add_argument("--granul_period", type=int, default=1000)
    parser.add_argument("--window_size", type=int, default=5)
    parser.add_argument("--anomaly_threshold_kbps", type=float, default=1000.0)
    parser.add_argument("--min_ues", type=int, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app = AnomalyPrbXapp(
        args.config,
        args.http_server_port,
        args.rmr_port,
        args.window_size,
        args.anomaly_threshold_kbps,
        args.min_ues,
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

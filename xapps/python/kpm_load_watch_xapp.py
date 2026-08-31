#!/usr/bin/env python3
"""Starter E2SM-KPM monitoring xApp generated for kpm-load-watch."""

import argparse
import signal

from lib.xAppBase import xAppBase
from lib.load_classifier import LoadClassifier


class StudentKpmXapp(xAppBase):
    """Subscribe to one node-level KPM report and keep logs bounded."""

    def __init__(
        self,
        config,
        http_server_port,
        rmr_port,
        log_every,
        window_size,
        active_threshold_kbps,
        busy_threshold_kbps,
    ):
        self.load_classifier = LoadClassifier(
            window_size,
            active_threshold_kbps,
            busy_threshold_kbps,
        )
        super(StudentKpmXapp, self).__init__(config, http_server_port, rmr_port)
        self.log_every = max(1, log_every)
        self.indication_count = 0

    def _metrics_handler(self, name, path, data, ctype):
        response = super(StudentKpmXapp, self)._metrics_handler(
            name, path, data, ctype
        )
        snapshot = self.load_classifier.snapshot()
        payload = response["payload"]
        payload += (
            "# HELP oran_kpm_load_watch_average_kbps Moving-average downlink throughput.\n"
            "# TYPE oran_kpm_load_watch_average_kbps gauge\n"
            "oran_kpm_load_watch_average_kbps {:.12g}\n"
            "# HELP oran_kpm_load_watch_state Current classified load state.\n"
            "# TYPE oran_kpm_load_watch_state gauge\n"
        ).format(snapshot["average_kbps"])
        for state in LoadClassifier.STATES:
            payload += 'oran_kpm_load_watch_state{{state="{}"}} {}\n'.format(
                state, int(snapshot["state"] == state)
            )
        payload += (
            "# HELP oran_kpm_load_watch_state_transitions_total Load-state transitions.\n"
            "# TYPE oran_kpm_load_watch_state_transitions_total counter\n"
            "oran_kpm_load_watch_state_transitions_total {}\n"
            "# HELP oran_kpm_load_watch_samples_total Samples processed by the classifier.\n"
            "# TYPE oran_kpm_load_watch_samples_total counter\n"
            "oran_kpm_load_watch_samples_total {}\n"
        ).format(snapshot["transitions"], snapshot["samples"])
        response["payload"] = payload
        return response

    def indication_callback(
        self,
        e2_agent_id,
        subscription_id,
        indication_header,
        indication_message,
    ):
        self.indication_count += 1
        measurements = self.e2sm_kpm.extract_meas_data(indication_message)
        value = self._latest_numeric(
            measurements.get("measData", {}).get("DRB.UEThpDl", [])
        )
        if value is None:
            return

        snapshot = self.load_classifier.observe(value)
        periodic_log = (
            self.indication_count == 1
            or self.indication_count % self.log_every == 0
        )
        if not snapshot["state_changed"] and not periodic_log:
            return

        header = self.e2sm_kpm.extract_hdr_info(indication_header)
        print(
            "kpm-load-watch: indication={} node={} subscription={} time={} "
            "throughput_kbps={:.1f} average_kbps={:.1f} state={}".format(
                self.indication_count,
                e2_agent_id,
                subscription_id,
                header.get("colletStartTime"),
                value,
                snapshot["average_kbps"],
                snapshot["state"],
            ),
            flush=True,
        )

    @xAppBase.start_function
    def start(self, e2_node_id, metric_names, report_period, granul_period):
        print(
            "kpm-load-watch: subscribing node={} style=1 metrics={}".format(
                e2_node_id, metric_names
            ),
            flush=True,
        )
        self.e2sm_kpm.subscribe_report_service_style_1(
            e2_node_id,
            report_period,
            metric_names,
            granul_period,
            self.indication_callback,
        )


def parse_args():
    parser = argparse.ArgumentParser(description="kpm-load-watch KPM laboratory xApp")
    parser.add_argument("--config", default="")
    parser.add_argument("--http_server_port", type=int, default=8091)
    parser.add_argument("--rmr_port", type=int, default=4561)
    parser.add_argument("--e2_node_id", required=True)
    parser.add_argument("--ran_func_id", type=int, default=2)
    parser.add_argument("--kpm_report_style", type=int, choices=[1], default=1)
    parser.add_argument("--metrics", default="DRB.UEThpDl")
    parser.add_argument("--report_period", type=int, default=2000)
    parser.add_argument("--granul_period", type=int, default=2000)
    parser.add_argument("--log_every", type=int, default=30)
    parser.add_argument("--window_size", type=int, default=5)
    parser.add_argument("--active_threshold_kbps", type=float, default=1000.0)
    parser.add_argument("--busy_threshold_kbps", type=float, default=20000.0)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app = StudentKpmXapp(
        args.config,
        args.http_server_port,
        args.rmr_port,
        args.log_every,
        args.window_size,
        args.active_threshold_kbps,
        args.busy_threshold_kbps,
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

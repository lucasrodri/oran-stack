#!/usr/bin/env python3
"""Starter E2SM-KPM monitoring xApp generated for __XAPP_NAME__."""

import argparse
import signal

from lib.xAppBase import xAppBase


class StudentKpmXapp(xAppBase):
    """Subscribe to one node-level KPM report and keep logs bounded."""

    def __init__(self, config, http_server_port, rmr_port, log_every):
        super(StudentKpmXapp, self).__init__(config, http_server_port, rmr_port)
        self.log_every = max(1, log_every)
        self.indication_count = 0

    def indication_callback(
        self,
        e2_agent_id,
        subscription_id,
        indication_header,
        indication_message,
    ):
        # xAppBase already exports every decoded value at /metrics. The callback
        # is where the student adds an algorithm, aggregation or experiment.
        self.indication_count += 1
        if self.indication_count != 1 and self.indication_count % self.log_every:
            return

        header = self.e2sm_kpm.extract_hdr_info(indication_header)
        measurements = self.e2sm_kpm.extract_meas_data(indication_message)
        print(
            "__XAPP_NAME__: indication={} node={} subscription={} time={} metrics={}".format(
                self.indication_count,
                e2_agent_id,
                subscription_id,
                header.get("colletStartTime"),
                measurements.get("measData", {}),
            ),
            flush=True,
        )

    @xAppBase.start_function
    def start(self, e2_node_id, metric_names, report_period, granul_period):
        print(
            "__XAPP_NAME__: subscribing node={} style=1 metrics={}".format(
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
    parser = argparse.ArgumentParser(description="__XAPP_NAME__ KPM laboratory xApp")
    parser.add_argument("--config", default="")
    parser.add_argument("--http_server_port", type=int, default=8091)
    parser.add_argument("--rmr_port", type=int, default=4561)
    parser.add_argument("--e2_node_id", required=True)
    parser.add_argument("--ran_func_id", type=int, default=2)
    parser.add_argument("--kpm_report_style", type=int, choices=[1], default=1)
    parser.add_argument("--metrics", default="DRB.UEThpDl")
    parser.add_argument("--report_period", type=int, default=__REPORT_PERIOD__)
    parser.add_argument("--granul_period", type=int, default=__REPORT_PERIOD__)
    parser.add_argument("--log_every", type=int, default=30)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app = StudentKpmXapp(
        args.config,
        args.http_server_port,
        args.rmr_port,
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

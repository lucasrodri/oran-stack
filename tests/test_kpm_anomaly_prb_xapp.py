import importlib.util
import pathlib
import sys
import types
import unittest


def _load_xapp_class():
    """Load AnomalyPrbXapp without starting the RIC runtime."""
    saved = {
        name: sys.modules.get(name) for name in ("lib", "lib.xAppBase")
    }
    lib_pkg = types.ModuleType("lib")
    lib_pkg.__path__ = []
    base_module = types.ModuleType("lib.xAppBase")

    class _StubXAppBase(object):
        def __init__(self, config, http_server_port, rmr_port):
            self.control_outcome_callback = None

        def _metrics_handler(self, name, path, data, ctype):
            return {"payload": ""}

        @staticmethod
        def _latest_numeric(values):
            if not isinstance(values, (list, tuple)):
                values = [values]
            for value in reversed(values):
                if isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)):
                    return float(value)
            return None

        @staticmethod
        def start_function(fun):
            return fun

    base_module.xAppBase = _StubXAppBase
    lib_pkg.xAppBase = base_module
    sys.modules["lib"] = lib_pkg
    sys.modules["lib.xAppBase"] = base_module
    try:
        module_path = (
            pathlib.Path(__file__).parents[1]
            / "xapps"
            / "python"
            / "kpm_anomaly_prb_xapp.py"
        )
        spec = importlib.util.spec_from_file_location(
            "kpm_anomaly_prb_xapp", module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return module.AnomalyPrbXapp


AnomalyPrbXapp = _load_xapp_class()


class _ControlRecorder(object):
    def __init__(self):
        self.calls = []

    def control_slice_level_prb_quota(
        self,
        e2_node_id,
        ue_id,
        min_prb_ratio,
        max_prb_ratio,
        dedicated_prb_ratio,
        ack_request=1,
    ):
        self.calls.append({
            "e2_node_id": e2_node_id,
            "ue_id": ue_id,
            "min_prb_ratio": min_prb_ratio,
            "max_prb_ratio": max_prb_ratio,
            "dedicated_prb_ratio": dedicated_prb_ratio,
            "ack_request": ack_request,
        })


def _xapp(**kwargs):
    params = dict(
        window_size=2,
        anomaly_threshold=1.0,
        min_ues=2,
    )
    params.update(kwargs)
    app = AnomalyPrbXapp("", 8091, 4561, **params)
    app.e2sm_rc = _ControlRecorder()
    return app


class AnomalyPrbXappTest(unittest.TestCase):
    def test_controls_only_the_ue_at_or_above_threshold_and_only_once(self):
        app = _xapp()

        self.assertEqual([], app.observe_ues("gnb", {1: 1.0}))
        self.assertEqual([], app.e2sm_rc.calls)

        # [1, 1] averages to the threshold and is anomalous.
        acted = app.observe_ues("gnb", {1: 1.0, 2: 0.0})
        self.assertEqual([1], acted)
        self.assertEqual(1, len(app.e2sm_rc.calls))
        call = app.e2sm_rc.calls[0]
        self.assertEqual(1, call["ue_id"])
        self.assertEqual(0, call["min_prb_ratio"])
        self.assertEqual(0, call["max_prb_ratio"])
        self.assertEqual(0, call["dedicated_prb_ratio"])
        self.assertEqual(1, call["ack_request"])

        app.observe_ues("gnb", {1: 8.0, 2: 0.0})
        self.assertEqual(1, len(app.e2sm_rc.calls))

        self.assertEqual(1, app._on_control_outcome("ack"))
        self.assertIsNone(app._on_control_outcome("failure"))

    def test_second_anomalous_ue_is_controlled_separately(self):
        app = _xapp()
        app.observe_ues("gnb", {1: 5.0, 2: 0.0})
        app.observe_ues("gnb", {1: 5.0, 2: 4.0})
        self.assertEqual([1, 2], [call["ue_id"] for call in app.e2sm_rc.calls])

    def test_expired_window_sample_can_keep_a_ue_below_threshold(self):
        app = _xapp(window_size=2, anomaly_threshold=5.0, min_ues=2)

        # One UE is not enough to act, so the high samples only fill the window.
        self.assertEqual([], app.observe_ues("gnb", {1: 9.0}))
        self.assertEqual([], app.observe_ues("gnb", {1: 9.0}))

        # The oldest 9 leaves: [9, 0] averages to 4.5, under the threshold.
        acted = app.observe_ues("gnb", {1: 0.0, 2: 0.0})
        self.assertEqual([], acted)
        self.assertEqual([], app.e2sm_rc.calls)

    def test_metrics_report_the_average_and_current_state(self):
        app = _xapp()
        app.observe_ues("gnb", {1: 5.0, 2: 0.0})

        payload = app._metrics_handler("metrics", "/metrics", "", "")["payload"]
        self.assertIn("oran_kpm_anomaly_prb_drop_rate_average 5\n", payload)
        self.assertIn("oran_kpm_anomaly_prb_samples_total 2\n", payload)
        self.assertIn("oran_kpm_anomaly_prb_ues_seen 2\n", payload)
        self.assertIn("oran_kpm_anomaly_prb_controls_total 1\n", payload)
        self.assertIn('oran_kpm_anomaly_prb_state{state="unknown"} 0\n', payload)
        self.assertIn('oran_kpm_anomaly_prb_state{state="monitoring"} 0\n', payload)
        self.assertIn('oran_kpm_anomaly_prb_state{state="acted"} 1\n', payload)
        self.assertIn("oran_kpm_anomaly_prb_anomaly_threshold 1\n", payload)

    def test_indication_callback_reads_style_4_ue_measurements(self):
        app = _xapp()

        class _Kpm(object):
            def extract_meas_data(self, message):
                return message

        app.e2sm_kpm = _Kpm()
        acted = app.indication_callback(
            "gnb",
            1,
            {},
            {
                "ueMeasData": {
                    1: {"measData": {"DRB.RlcPacketDropRateDl": [5.0]}},
                    2: {"measData": {"DRB.RlcPacketDropRateDl": [0.0]}},
                }
            },
        )
        self.assertEqual([1], acted)

    def test_rejects_invalid_window_threshold_and_min_ues(self):
        with self.assertRaises(ValueError):
            _xapp(window_size=0)
        with self.assertRaises(ValueError):
            _xapp(min_ues=0)
        with self.assertRaises(ValueError):
            _xapp(anomaly_threshold=float("nan"))
        with self.assertRaises(ValueError):
            _xapp(anomaly_threshold=float("inf"))


if __name__ == "__main__":
    unittest.main()

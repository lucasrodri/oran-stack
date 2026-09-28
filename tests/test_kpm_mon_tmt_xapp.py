import importlib.util
import pathlib
import sys
import types
import unittest


def _load_xapp_class():
    """Load StudentKpmXapp without starting the RIC runtime."""
    saved = {
        name: sys.modules.get(name) for name in ("lib", "lib.xAppBase")
    }
    lib_pkg = types.ModuleType("lib")
    lib_pkg.__path__ = []
    base_module = types.ModuleType("lib.xAppBase")

    class _StubXAppBase(object):
        def __init__(self, config, http_server_port, rmr_port):
            pass

        def _metrics_handler(self, name, path, data, ctype):
            return {"payload": ""}

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
            / "kpm_mon_tmt_xapp.py"
        )
        spec = importlib.util.spec_from_file_location(
            "kpm_mon_tmt_xapp", module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return module.StudentKpmXapp


StudentKpmXapp = _load_xapp_class()


def _xapp(window_size=5, activity_threshold=10.0):
    return StudentKpmXapp("", 8091, 4561, 30, window_size, activity_threshold)


class KpmMonTmtClassifierTest(unittest.TestCase):
    def test_classifies_uplink_activity_from_a_moving_average(self):
        xapp = _xapp(window_size=2, activity_threshold=10.0)

        first = xapp._observe(100.0)
        self.assertEqual(100.0, first["average"])
        self.assertEqual("active", first["state"])
        self.assertEqual(0, first["transitions"])
        self.assertEqual(0, first["idle"])

        # [100, 0] stays active at the configured boundary.
        boundary = xapp._observe(0.0)
        self.assertEqual(50.0, boundary["average"])
        self.assertEqual("active", boundary["state"])
        self.assertEqual(0, boundary["transitions"])

        # The oldest sample leaves the window: [0, 0] -> idle.
        below = xapp._observe(0.0)
        self.assertEqual(0.0, below["average"])
        self.assertEqual("idle", below["state"])
        self.assertEqual(1, below["transitions"])
        self.assertEqual(1, below["idle"])

        still = xapp._observe(0.0)
        self.assertEqual(0.0, still["average"])
        self.assertEqual("idle", still["state"])
        self.assertEqual(1, still["transitions"])
        self.assertEqual(2, still["idle"])
        self.assertEqual(4, still["samples"])

        # [0, 20] returns to the threshold without counting the old idle sample.
        recovered = xapp._observe(20.0)
        self.assertEqual(10.0, recovered["average"])
        self.assertEqual("active", recovered["state"])
        self.assertEqual(2, recovered["transitions"])
        self.assertEqual(2, recovered["idle"])

        # Leaving "unknown" is not a transition.
        cold = _xapp(window_size=1, activity_threshold=10.0)
        cold_below = cold._observe(0.0)
        self.assertEqual("idle", cold_below["state"])
        self.assertEqual(0, cold_below["transitions"])
        self.assertEqual(1, cold_below["idle"])
        cold_healthy = cold._observe(10.0)
        self.assertEqual("active", cold_healthy["state"])
        self.assertEqual(1, cold_healthy["transitions"])
        self.assertEqual(1, cold_healthy["idle"])

    def test_metrics_report_the_average_and_current_state(self):
        xapp = _xapp(window_size=2, activity_threshold=10.0)
        xapp._observe(20.0)
        xapp._observe(0.0)

        payload = xapp._metrics_handler("metrics", "/metrics", "", "")["payload"]
        self.assertIn("oran_kpm_mon_tmt_uplink_throughput_average_kbps 10\n", payload)
        self.assertIn("oran_kpm_mon_tmt_samples_total 2\n", payload)
        self.assertIn("oran_kpm_mon_tmt_idle_samples_total 0\n", payload)
        self.assertIn('oran_kpm_mon_tmt_state{state="active"} 1\n', payload)
        self.assertIn(
            'oran_kpm_mon_tmt_state{state="idle"} 0\n', payload
        )
        self.assertIn('oran_kpm_mon_tmt_state{state="unknown"} 0\n', payload)
        self.assertIn("oran_kpm_mon_tmt_state_transitions_total 0\n", payload)
        self.assertIn("oran_kpm_mon_tmt_activity_threshold_kbps 10\n", payload)

    def test_rejects_invalid_window_and_threshold(self):
        with self.assertRaises(ValueError):
            _xapp(window_size=0)
        with self.assertRaises(ValueError):
            _xapp(activity_threshold=float("nan"))
        with self.assertRaises(ValueError):
            _xapp(activity_threshold=float("inf"))


if __name__ == "__main__":
    unittest.main()

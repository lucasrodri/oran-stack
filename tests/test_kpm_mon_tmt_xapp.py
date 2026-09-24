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


def _xapp(window_size=5, success_threshold=99.0):
    return StudentKpmXapp("", 8091, 4561, 30, window_size, success_threshold)


class KpmMonTmtClassifierTest(unittest.TestCase):
    def test_classifies_a_moving_average_as_healthy_or_below_threshold(self):
        xapp = _xapp(window_size=2, success_threshold=99.0)

        first = xapp._observe(100.0)
        self.assertEqual(100.0, first["average"])
        self.assertEqual("healthy", first["state"])
        self.assertEqual(0, first["transitions"])
        self.assertEqual(0, first["below_threshold"])

        # [100, 98] averages to the threshold and stays healthy.
        boundary = xapp._observe(98.0)
        self.assertEqual(99.0, boundary["average"])
        self.assertEqual("healthy", boundary["state"])
        self.assertEqual(0, boundary["transitions"])

        # The oldest sample leaves the window: [98, 96] -> 97.
        below = xapp._observe(96.0)
        self.assertEqual(97.0, below["average"])
        self.assertEqual("below_threshold", below["state"])
        self.assertEqual(1, below["transitions"])
        self.assertEqual(1, below["below_threshold"])

        still = xapp._observe(96.0)
        self.assertEqual(96.0, still["average"])
        self.assertEqual("below_threshold", still["state"])
        self.assertEqual(1, still["transitions"])
        self.assertEqual(2, still["below_threshold"])
        self.assertEqual(4, still["samples"])

        # [96, 102] returns to the threshold without counting the old miss.
        recovered = xapp._observe(102.0)
        self.assertEqual(99.0, recovered["average"])
        self.assertEqual("healthy", recovered["state"])
        self.assertEqual(2, recovered["transitions"])
        self.assertEqual(2, recovered["below_threshold"])

        # Leaving "unknown" is not a transition.
        cold = _xapp(window_size=1, success_threshold=99.0)
        cold_below = cold._observe(98.0)
        self.assertEqual("below_threshold", cold_below["state"])
        self.assertEqual(0, cold_below["transitions"])
        self.assertEqual(1, cold_below["below_threshold"])
        cold_healthy = cold._observe(99.0)
        self.assertEqual("healthy", cold_healthy["state"])
        self.assertEqual(1, cold_healthy["transitions"])
        self.assertEqual(1, cold_healthy["below_threshold"])

    def test_metrics_report_the_average_and_current_state(self):
        xapp = _xapp(window_size=2, success_threshold=99.0)
        xapp._observe(100.0)
        xapp._observe(96.0)

        payload = xapp._metrics_handler("metrics", "/metrics", "", "")["payload"]
        self.assertIn("oran_kpm_mon_tmt_success_rate_average 98\n", payload)
        self.assertIn("oran_kpm_mon_tmt_samples_total 2\n", payload)
        self.assertIn("oran_kpm_mon_tmt_below_threshold_total 1\n", payload)
        self.assertIn('oran_kpm_mon_tmt_state{state="healthy"} 0\n', payload)
        self.assertIn(
            'oran_kpm_mon_tmt_state{state="below_threshold"} 1\n', payload
        )
        self.assertIn('oran_kpm_mon_tmt_state{state="unknown"} 0\n', payload)
        self.assertIn("oran_kpm_mon_tmt_state_transitions_total 1\n", payload)
        self.assertIn("oran_kpm_mon_tmt_success_threshold 99\n", payload)

    def test_rejects_invalid_window_and_threshold(self):
        with self.assertRaises(ValueError):
            _xapp(window_size=0)
        with self.assertRaises(ValueError):
            _xapp(success_threshold=float("nan"))
        with self.assertRaises(ValueError):
            _xapp(success_threshold=float("inf"))


if __name__ == "__main__":
    unittest.main()

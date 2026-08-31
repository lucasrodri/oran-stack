import importlib.util
import pathlib
import unittest


MODULE_PATH = (
    pathlib.Path(__file__).parents[1]
    / "xapps"
    / "python"
    / "lib"
    / "load_classifier.py"
)
SPEC = importlib.util.spec_from_file_location("load_classifier", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
LoadClassifier = MODULE.LoadClassifier


class LoadClassifierTest(unittest.TestCase):
    def test_classifies_a_moving_average_and_counts_transitions(self):
        classifier = LoadClassifier(
            window_size=2,
            active_threshold_kbps=1000,
            busy_threshold_kbps=20000,
        )

        self.assertEqual("idle", classifier.observe(0)["state"])
        active = classifier.observe(4000)
        self.assertEqual("active", active["state"])
        self.assertEqual(2000, active["average_kbps"])

        busy = classifier.observe(40000)
        self.assertEqual("busy", busy["state"])
        self.assertEqual(2, busy["transitions"])

        self.assertEqual("busy", classifier.observe(10000)["state"])
        self.assertEqual("active", classifier.observe(0)["state"])
        idle = classifier.observe(0)
        self.assertEqual("idle", idle["state"])
        self.assertEqual(4, idle["transitions"])

    def test_rejects_invalid_configuration_and_non_finite_values(self):
        with self.assertRaises(ValueError):
            LoadClassifier(window_size=0)
        with self.assertRaises(ValueError):
            LoadClassifier(active_threshold_kbps=20, busy_threshold_kbps=10)

        classifier = LoadClassifier()
        with self.assertRaises(ValueError):
            classifier.observe(float("nan"))


if __name__ == "__main__":
    unittest.main()

import array
import importlib.util
import pathlib
import unittest


MODULE_PATH = (
    pathlib.Path(__file__).parents[1] / "scripts" / "zmq_iq_broker.py"
)
SPEC = importlib.util.spec_from_file_location("zmq_iq_broker", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _frame(*samples):
    values = array.array("f")
    for real, imag in samples:
        values.append(real)
        values.append(imag)
    return values.tobytes()


class SumUplinkTest(unittest.TestCase):
    def test_sums_equal_length_frames(self):
        downlink = _frame((1.0, 0.0), (0.0, 1.0))
        first = _frame((1.0, 2.0), (3.0, 4.0))
        second = _frame((0.5, -2.0), (-1.0, 1.0))

        summed = MODULE.sum_uplink(downlink, [first, second])

        self.assertEqual(_frame((1.5, 0.0), (2.0, 5.0)), summed)
        self.assertEqual(len(downlink), len(summed))

    def test_missing_ue_contributes_zeros(self):
        downlink = _frame((1.0, 0.0), (0.0, 1.0))
        present = _frame((1.0, 2.0), (3.0, 4.0))

        summed = MODULE.sum_uplink(downlink, [present, None])

        self.assertEqual(present, summed)

    def test_no_uplink_is_zero_fill(self):
        downlink = _frame((9.0, 8.0), (7.0, 6.0))

        summed = MODULE.sum_uplink(downlink, [None, None])

        self.assertEqual(b"\x00" * len(downlink), summed)

    def test_mismatched_length_is_ignored(self):
        downlink = _frame((1.0, 0.0), (0.0, 1.0))
        short = _frame((5.0, 5.0))

        summed = MODULE.sum_uplink(downlink, [short])

        self.assertEqual(b"\x00" * len(downlink), summed)

    def test_downlink_is_copied_per_ue(self):
        downlink = b"iq-frame"
        copies = MODULE.copy_downlink(downlink, 2)
        self.assertEqual([downlink, downlink], copies)
        self.assertEqual(2, len(copies))

    def test_erase_downlink_replaces_one_frame_with_silence(self):
        frame = _frame((1.0, 2.0))
        self.assertEqual(frame, MODULE.erase_downlink(frame, False))
        self.assertEqual(b"\x00" * len(frame), MODULE.erase_downlink(frame, True))

    def test_parse_ue_accepts_an_optional_loss_ratio(self):
        self.assertEqual(("ue", 2101, 2100, 0.0), MODULE._parse_ue("ue:2101:2100"))
        self.assertEqual(("ue", 2201, 2200, 0.05), MODULE._parse_ue("ue:2201:2200:0.05"))

    def test_helm_chart_copy_matches_the_script(self):
        chart_copy = (
            pathlib.Path(__file__).parents[1]
            / "helm"
            / "ran"
            / "files"
            / "zmq_iq_broker.py"
        )
        self.assertEqual(MODULE_PATH.read_bytes(), chart_copy.read_bytes())


if __name__ == "__main__":
    unittest.main()

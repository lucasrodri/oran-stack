import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "xapps" / "python"))

from lib.e2sm_rc_slice_quota import (  # noqa: E402
    DEDICATED_PRB_POLICY_RATIO,
    MAX_PRB_POLICY_RATIO,
    MIN_PRB_POLICY_RATIO,
    PLMN_IDENTITY,
    SD,
    SST,
    serving_plmn_octets,
    slice_level_prb_quota_message,
)


def _walk(node, found):
    if isinstance(node, dict):
        if "ranParameter-ID" in node:
            value_type = node["ranParameter-valueType"]
            if value_type[0] == "ranP-Choice-ElementFalse":
                found[node["ranParameter-ID"]] = value_type[1]["ranParameter-value"]
        for value in node.values():
            _walk(value, found)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _walk(value, found)


class SliceLevelPrbQuotaMessageTest(unittest.TestCase):
    def test_names_the_serving_cell_and_the_drb_slice_with_three_percentages(self):
        message = slice_level_prb_quota_message("00101", 1, 0, 0, 0, 0)
        found = {}
        _walk(message, found)

        self.assertEqual(("valueOctS", bytes([0x00, 0xF1, 0x10])), found[PLMN_IDENTITY])
        self.assertEqual(("valueOctS", bytes([1])), found[SST])
        self.assertEqual(("valueOctS", bytes([0, 0, 0])), found[SD])
        self.assertEqual(("valueInt", 0), found[MIN_PRB_POLICY_RATIO])
        self.assertEqual(("valueInt", 0), found[MAX_PRB_POLICY_RATIO])
        self.assertEqual(("valueInt", 0), found[DEDICATED_PRB_POLICY_RATIO])
        self.assertNotIn(4, found)

    def test_sd_is_three_big_endian_octets(self):
        message = slice_level_prb_quota_message("00101", 1, 0x123456, 0, 100, 0)
        found = {}
        _walk(message, found)

        self.assertEqual(("valueOctS", bytes([0x12, 0x34, 0x56])), found[SD])

    def test_plmn_follows_ts_24_008_for_two_and_three_digit_mnc(self):
        cases = {
            "00101": "00f110",
            "99999": "99f999",
            "001010": "000110",
            "310410": "130014",
            "123456": "216354",
        }
        for plmn, expected in cases.items():
            with self.subTest(plmn=plmn):
                self.assertEqual(expected, serving_plmn_octets(plmn).hex())

    def test_rejects_a_ratio_outside_0_to_100(self):
        with self.assertRaises(ValueError):
            slice_level_prb_quota_message("00101", 1, 0, 0, 101, 0)

    def test_rejects_a_non_integer_ratio(self):
        for bad in (5.9, "5", True):
            with self.subTest(ratio=bad), self.assertRaises(ValueError):
                slice_level_prb_quota_message("00101", 1, 0, 0, bad, 0)

    def test_requires_dedicated_le_min_le_max(self):
        with self.assertRaises(ValueError):
            slice_level_prb_quota_message("00101", 1, 0, 10, 5, 0)
        with self.assertRaises(ValueError):
            slice_level_prb_quota_message("00101", 1, 0, 1, 5, 100)
        slice_level_prb_quota_message("00101", 1, 0, 10, 50, 10)


if __name__ == "__main__":
    unittest.main()

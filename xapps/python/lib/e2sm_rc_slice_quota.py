"""E2SM-RC Style 2 Action 6 control message.

The DU treats this as a grant-size limit for one UE. The header names that UE
by its gNB-CU UE F1AP ID. The message names the slice and three percentages of
the cell's PRBs. The DU computes the PRB count.

A slice here is not a separate identifier. It is one policy member: the
serving cell's PLMN plus the S-NSSAI (SST and SD) of one of the UE's DRBs.
The DU rejects the request when that pair does not match, when a group has no
members, or when any ratio is missing or outside 0-100. This module also
rejects ratios that break dedicated <= min <= max before anything is sent.
"""

from .utils import plmn_string_to_bcd, plmn_to_bytes

# O-RAN.WG3.E2SM-RC section 8.4.3.6. Parameter 4 is reserved and is not used.
RRM_POLICY_RATIO_LIST = 1
RRM_POLICY_RATIO_GROUP = 2
RRM_POLICY = 3
RRM_POLICY_MEMBER_LIST = 5
RRM_POLICY_MEMBER = 6
PLMN_IDENTITY = 7
S_NSSAI = 8
SST = 9
SD = 10
MIN_PRB_POLICY_RATIO = 11
MAX_PRB_POLICY_RATIO = 12
DEDICATED_PRB_POLICY_RATIO = 13


def prb_policy_ratio(value):
    """Return a percentage the DU will accept."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 100:
        raise ValueError("PRB policy ratio must be an integer from 0 to 100")
    return value


def serving_plmn_octets(plmn):
    """Encode a PLMN string as the 3-octet identity the DU compares."""
    if not isinstance(plmn, str) or len(plmn) not in (5, 6) or not plmn.isdigit():
        raise ValueError("PLMN must be a 5- or 6-digit string")
    octets = plmn_to_bytes(plmn_string_to_bcd(plmn))
    if len(octets) != 3:
        raise ValueError("PLMN identity must be 3 octets")
    return octets


def _element_int(parameter_id, value):
    return {
        "ranParameter-ID": parameter_id,
        "ranParameter-valueType": (
            "ranP-Choice-ElementFalse",
            {"ranParameter-value": ("valueInt", value)},
        ),
    }


def _element_octets(parameter_id, value):
    return {
        "ranParameter-ID": parameter_id,
        "ranParameter-valueType": (
            "ranP-Choice-ElementFalse",
            {"ranParameter-value": ("valueOctS", value)},
        ),
    }


def _structure(parameter_id, parameters):
    return {
        "ranParameter-ID": parameter_id,
        "ranParameter-valueType": (
            "ranP-Choice-Structure",
            {"ranParameter-Structure": {"sequence-of-ranParameters": parameters}},
        ),
    }


def _list(parameter_id, items):
    return {
        "ranParameter-ID": parameter_id,
        "ranParameter-valueType": (
            "ranP-Choice-List",
            {"ranParameter-List": {"list-of-ranParameter": [
                {"sequence-of-ranParameters": item} for item in items
            ]}},
        ),
    }


def slice_level_prb_quota_message(plmn, sst, sd, min_ratio, max_ratio, dedicated_ratio):
    """One RRM policy ratio group for the UE's DRB slice.

    plmn is the serving cell PLMN, for example "00101". sst is 0..255 and sd
    is 0..16777215. The three ratios are integer percentages of the cell PRBs
    with dedicated <= min <= max.
    """
    sst = int(sst)
    sd = int(sd)
    if sst < 0 or sst > 255:
        raise ValueError("SST must be an integer from 0 to 255")
    if sd < 0 or sd > 0xFFFFFF:
        raise ValueError("SD must be an integer from 0 to 16777215")
    min_ratio = prb_policy_ratio(min_ratio)
    max_ratio = prb_policy_ratio(max_ratio)
    dedicated_ratio = prb_policy_ratio(dedicated_ratio)
    # 3GPP TS 28.541 RRMPolicyRatio: dedicated <= min <= max.
    if not dedicated_ratio <= min_ratio <= max_ratio:
        raise ValueError("PRB policy ratios must satisfy dedicated <= min <= max")

    member = _structure(RRM_POLICY_MEMBER, [
        _element_octets(PLMN_IDENTITY, serving_plmn_octets(plmn)),
        _structure(S_NSSAI, [
            _element_octets(SST, bytes([sst])),
            _element_octets(SD, sd.to_bytes(3, byteorder="big")),
        ]),
    ])
    group = _structure(RRM_POLICY_RATIO_GROUP, [
        _structure(RRM_POLICY, [
            _list(RRM_POLICY_MEMBER_LIST, [[member]]),
        ]),
        _element_int(MIN_PRB_POLICY_RATIO, min_ratio),
        _element_int(MAX_PRB_POLICY_RATIO, max_ratio),
        _element_int(DEDICATED_PRB_POLICY_RATIO, dedicated_ratio),
    ])
    return {
        "ric-controlMessage-formats": (
            "controlMessage-Format1",
            {"ranP-List": [_list(RRM_POLICY_RATIO_LIST, [[group]])]},
        )
    }

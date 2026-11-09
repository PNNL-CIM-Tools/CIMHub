"""RAW case identification and system-wide data: the values the master and the other mappers read.

The master document itself is built by the orchestrator (``importer/raw_to_cimtbl.py``). This module holds the
record's classification (``FIELDS``) and the case-level values: SBASE, BASFRQ and the zero-impedance threshold.
Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#master``.
"""

from __future__ import annotations

from typing import NamedTuple

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import Field, schema_defaults

NATIVE_CLASS = schema.CaseIdentificationRecord

FIELDS = {
    "new_case_flag": Field("structural", note="IC: 0 (base case) maps; 1 (add to the working case) raises, a change "
                                              "case is not a model"),
    "system_base_mva": Field("copied", (("BasePower", "basePower", "MVA"),), note="SBASE; blank: 100 (defaulted)"),
    "revision": Field("structural", note="REV: the reader reads 34 only"),
    "transformer_ratings_units": Field("mapped", note="XFRRAT: selects what transformer RATEn-k are (<= 0 MVA; > 0 "
                                                      "current as MVA at 1 pu voltage); read by R4"),
    "branch_ratings_units": Field("mapped", note="NXFRAT: the same for branch RATEn; read by R1"),
    "system_base_frequency": Field("copied", (("BaseFrequency", "frequency", "Hz"),),
                                   note="BASFRQ; blank: 60 (defaulted; the spec's 'present option setting', RAW-17)"),
    "titles": Field("untranscribed", note="the two title lines go on the master's comment; no CIM home"),
    "general": Field("structural", note="GENERAL: its THRSHZ is the zero-impedance threshold of the substation merge "
                                        "(plan 3.2; default 0.0001); the record itself is a solution option"),
    "gauss": Field("untranscribed", note="solution options; no home in the network profile parts"),
    "newton": Field("untranscribed", note="solution options; no home in the network profile parts"),
    "adjust": Field("untranscribed", note="solution options; no home in the network profile parts"),
    "tysl": Field("untranscribed", note="solution options; no home in the network profile parts"),
    "solver": Field("untranscribed", note="solution options; no home in the network profile parts"),
    "ratings": Field("structural", note="RATING records: one OperationalLimitType olt_rate<n> each, written with R1 "
                                        "(RAW-9)"),
}

#: BASFRQ's spec default is "the present option setting"; a blank takes PSS/E's shipped setting (RAW-17).
DEFAULT_BASE_FREQUENCY = 60.0
#: GENERAL THRSHZ's spec default: the largest |X| of a zero-impedance branch, in pu.
DEFAULT_ZERO_IMPEDANCE_THRESHOLD = 0.0001


class CaseValues(NamedTuple):
    """The case-level values; each ``*_defaulted`` says whether the file left the value blank."""

    base_mva: float
    base_mva_defaulted: bool
    base_frequency: float
    base_frequency_defaulted: bool
    zero_impedance_threshold: float
    zero_impedance_threshold_defaulted: bool


def case_record(native) -> schema.CaseIdentificationRecord:
    """The case's one identification record; IC other than 0 (a change case) raises."""
    case = native.first(NATIVE_CLASS)
    if case is None:
        raise ValueError("the RAW model has no case identification record")
    if case.new_case_flag not in (None, 0):
        raise ValueError(f"IC={case.new_case_flag}: a change case (data added to a working case) is not a model; "
                         "only a base case (IC=0) maps")
    return case


def _system_wide_value(text: str | None, keyword: str) -> float | None:
    """``KEYWORD=value`` from a system-wide record's text, or ``None`` when the record does not set it."""
    for item in (text or "").split(","):
        name, _, value = item.partition("=")
        if name.strip().upper() == keyword and value.strip():
            return float(value)
    return None


def case_values(native) -> CaseValues:
    """SBASE, BASFRQ and THRSHZ, each with whether it was defaulted."""
    case = case_record(native)
    base_mva = case.system_base_mva
    if base_mva is None:
        base_mva = float(schema_defaults(NATIVE_CLASS, "raw_default")["system_base_mva"])
    frequency = case.system_base_frequency
    threshold = _system_wide_value(case.general, "THRSHZ")
    return CaseValues(
        float(base_mva), case.system_base_mva is None,
        float(frequency if frequency is not None else DEFAULT_BASE_FREQUENCY), frequency is None,
        threshold if threshold is not None else DEFAULT_ZERO_IMPEDANCE_THRESHOLD, threshold is None,
    )

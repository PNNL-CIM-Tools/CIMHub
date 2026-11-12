"""BasePower, BaseFrequency and the rating-set types -> the case identification record (``EXPORT_MAPPING.md``)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_raw.exporter.ratings import rating_set_number

NATIVE_CLASS = schema.CaseIdentificationRecord
CIM_CLASSES = ()

REVISION = 34

_UNSET = Slot("unset", "solution options: no home in the network profile parts")
CASE_SLOTS = {
    "new_case_flag": Slot("rule", "IC 0: a base case"),
    "system_base_mva": Slot("written", "SBASE: BasePower.basePower (MVA), the one BasePower"),
    "revision": Slot("rule", "REV 34"),
    "transformer_ratings_units": Slot("rule", "XFRRAT 1 when the transformer ratings are CurrentLimits, else 0"),
    "branch_ratings_units": Slot("rule", "NXFRAT 1 when the branch and switch ratings are CurrentLimits, else 0"),
    "system_base_frequency": Slot("written", "BASFRQ: the network's base frequency (Hz)"),
    "titles": Slot("unset", "two blank lines: the importer lists the titles on the master's comment"),
    "general": Slot("unset", "solution options; THRSHZ only steered the import's substation merge"),
    "gauss": _UNSET,
    "newton": _UNSET,
    "adjust": _UNSET,
    "tysl": _UNSET,
    "solver": _UNSET,
    "ratings": Slot("written", "a RATING record per olt_rate<n> OperationalLimitType"),
}
RATING_SLOTS = {
    "rating_set_number": Slot("written", "n of the type's mRID olt_rate<n>"),
    "rating_name": Slot("written", "OperationalLimitType.name"),
    "rating_description": Slot("written", "OperationalLimitType.description"),
}
SLOTS = {NATIVE_CLASS: CASE_SLOTS, schema.RatingRecord: RATING_SLOTS}


def export(context) -> list[schema.CaseIdentificationRecord]:
    """The one case record."""
    base_powers = context.objects(cim.BasePower)
    if len(base_powers) != 1:
        raise ValueError(f"{len(base_powers)} BasePower objects; RAW's SBASE needs exactly one")
    return [schema.CaseIdentificationRecord(
        new_case_flag=0, system_base_mva=get_qty(base_powers[0], "basePower", "MVA"), revision=REVISION,
        transformer_ratings_units=1 if context.transformer_ratings_in_current else 0,
        branch_ratings_units=1 if context.branch_ratings_in_current else 0,
        system_base_frequency=context.network.base_frequency.to("Hz"), titles=["", ""],
        ratings=_ratings(context))]


def _ratings(context) -> list[schema.RatingRecord]:
    ratings = []
    for limit_type in context.objects(cim.OperationalLimitType):
        number = rating_set_number(limit_type)
        if number is not None:
            ratings.append(schema.RatingRecord(rating_set_number=number, rating_name=limit_type.name,
                                               rating_description=limit_type.description))
    return sorted(ratings, key=lambda rating: rating.rating_set_number)

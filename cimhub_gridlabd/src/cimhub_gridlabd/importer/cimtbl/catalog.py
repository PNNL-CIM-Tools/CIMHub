"""What the S2 catalog mappers share: the object header, conductor ratings, references and the provenance header.

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s2-catalogs``.
"""

from __future__ import annotations

from cimtables.document import Column, Row, Table

from cimhub_core.cimtbl import Field, cell
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit, slots

#: The object header every GridLAB-D object has (``glm_object``), but ``name``.
HEADER_FIELDS = {slot: Field("untranscribed", note="object header: a catalog object has no place or service state")
                 for slot in ("parent", "groupid", "latitude", "longitude", "in_svc", "out_svc", "rank", "flags")}

_SUMMER = ("rating_summer_continuous", "rating_summer_emergency")
_WINTER = ("rating_winter_continuous", "rating_winter_emergency")


def rating_fields(info_classes: tuple[str, ...]) -> dict[str, Field]:
    """The four seasonal ratings of a conductor class whose rows are ``info_classes`` (D9, S2-7)."""
    winter = Field("untranscribed", note="equal to summer in every deck that sets it; a different value raises (no "
                                         "season is mapped, S2-7)")
    return {
        "rating_summer_continuous": Field("copied", tuple((info, "ratedCurrent", "A") for info in info_classes),
                                          "also the normal CurrentLimit of the wire's AssetInfo OperationalLimitSet "
                                          "<mRID>_limits. Unset: GridLAB-D's create() constant is not filled (S2-7)"),
        "rating_summer_emergency": Field("structural", note="the emergency CurrentLimit of that set; unset: not "
                                                            "filled (S2-7)"),
        "rating_winter_continuous": winter,
        "rating_winter_emergency": winter,
    }


def written_columns(model: GlmModel, record, fields: dict[str, Field], cim_class: str) -> list[tuple[Column, str]]:
    """``(Column, cell)`` for each copied target on ``cim_class``, its unit the one the record writes the slot in."""
    pairs = []
    for slot, field in fields.items():
        if field.kind != "copied":
            continue
        for target, column, unit in field.targets:
            if target == cim_class:
                header = registry_unit(model.unit(record, slot)) if unit else None
                pairs.append((Column(column, header), cell(getattr(record, slot))))
    return pairs


def native_name(record, slot: str) -> str:
    return slots(type(record))[slot].native_name


def label(record) -> str:
    return f"{record.class_name} {record.name}"


def ratings(record) -> tuple[dict[str, float], list[str]]:
    """``({"norm": A, "emerg": A}, unset native names)`` of a conductor's summer ratings; a winter rating that
    differs from its summer one raises (S2-7)."""
    for summer, winter in zip(_SUMMER, _WINTER):
        value = getattr(record, winter)
        if value is not None and value != getattr(record, summer):
            raise ValueError(f"{label(record)}: {native_name(record, winter)}={value} differs from "
                             f"{native_name(record, summer)}={getattr(record, summer)}; no season is mapped (S2-7)")
    limits = {suffix: float(getattr(record, slot)) for suffix, slot in zip(("norm", "emerg"), _SUMMER)
              if getattr(record, slot) is not None}
    unset = [native_name(record, slot) for slot in _SUMMER if getattr(record, slot) is None]
    return limits, unset


def limit_tables(limit_sets: list[str], limits: list[Row]) -> list[Table]:
    """The ``OperationalLimitSet`` and ``CurrentLimit`` tables, before the wires that name the sets."""
    if not limit_sets:
        return []
    return [Table("OperationalLimitSet", [Column("mRID")], [Row([name]) for name in limit_sets]),
            Table("CurrentLimit", [Column("mRID"), Column("normalValue", "A"), Column("OperationalLimitType"),
                                   Column("OperationalLimitSet")], limits)]


_LIMIT_TYPE = {"norm": "olt_normal", "emerg": "olt_emergency"}

#: ``(mRID, durationKind, isInfiniteDuration)`` of the two ``OperationalLimitType``s every ``CurrentLimit`` names
#: (``shapes/common.cimtbl``; the DSS master writes the same two).
LIMIT_TYPES = (("olt_normal", "normal", "true"), ("olt_emergency", "emergency", "false"))


def limit_types() -> Table:
    """The master's ``OperationalLimitType`` table."""
    rows = [Row([limit_mrid, kind, kind, infinite, "absoluteValue"]) for limit_mrid, kind, infinite in LIMIT_TYPES]
    return Table("OperationalLimitType", [Column("mRID"), Column("name"), Column("durationKind"),
                                          Column("isInfiniteDuration"), Column("direction")], rows)


def limit_rows(info_mrid: str, limits: dict[str, float]) -> list[Row]:
    return [Row([f"{info_mrid}_{suffix}", cell(amps), _LIMIT_TYPE[suffix], f"{info_mrid}_limits"])
            for suffix, amps in limits.items()]


def referenced(model: GlmModel, record, slot: str, classes: tuple[type, ...]):
    """The object ``record.slot`` names, which must be one of ``classes``."""
    name = getattr(record, slot)
    try:
        target = model.by_name(str(name))
    except KeyError:
        raise ValueError(f"{label(record)}: {native_name(record, slot)} {name!r} names no object") from None
    if not isinstance(target, classes):
        allowed = ", ".join(cls.class_name for cls in classes)
        raise ValueError(f"{label(record)}: {native_name(record, slot)} {name!r} is a {target.class_name}, not a "
                         f"{allowed}")
    return target


def provenance(native: str, targets: str, count: int) -> str:
    return (f"GridLAB-D {native} -> {targets} (catalog).\nSource table: {native} (records: {count})\n"
            "Mapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s2-catalogs")

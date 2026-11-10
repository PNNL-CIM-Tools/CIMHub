"""RAW Transformer impedance correction tables -> ``impedance_correction.cimtbl``: an ``ImpedanceTapChangerTable``
per table, its points as ``ImpedanceTapChangerTablePoint`` rows (R4b-10). Each winding that uses a table links to it
through its ``ImpedanceTapChangerTabular`` in ``transformer.cimtbl``, which comes after this document.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#transformer-the-forms-r4-raised-on-r4b``.
"""

from __future__ import annotations

from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell
from cimhub_raw.importer.cimtbl.derived import cim_angle, impedance_deviation_percent, is_angle_table

NATIVE_CLASS = schema.ImpedanceCorrectionRecord
POINT_CLASS = schema.ImpedanceCorrectionPoint
PREFIX = "ict_"  # requested from the cimtbl-translate table owners (plan C3)

FIELDS = {
    "table_number": Field("structural", note="I: the key, ImpedanceTapChangerTable ict_<I>, named <I>; a winding's "
                                             "TABk names it (transformer.cimtbl)"),
    "points": Field("structural", note="the points (T, F), each an ImpedanceTapChangerTablePoint ict_<I>_<n> (n = "
                                       "1.. in file order); the 0, 0, 0 point that ends the table is not a point"),
}

POINT_FIELDS = {
    "t": Field("derived", note="Ti: an angle table's (first T < 0.5 or last T > 1.5, is_angle_table) angle = "
                               "cim_angle(T) (deg); else a ratio table's ratio = T x BASKV / ratedU of its users' "
                               "winding (users that disagree, or none, raise); step blank (PSS/E looks a table up "
                               "by angle or ratio)"),
    "f_real": Field("derived", note="Re(Fi): rEnd1 = xEnd1 = 100 x (F - 1) percent of the nominal impedance "
                                    "(impedance_deviation_percent; a 2-winding unit's r and x are on end 1)"),
    "f_imag": Field("structural", note="Im(Fi): a complex factor has no CIM form (rEnd and xEnd are real); nonzero "
                                       "raises"),
}

_PROVENANCE = """PSS/E RAW Transformer impedance correction tables -> ImpedanceTapChangerTable + its points.
Source table: Impedance correction (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#transformer-the-forms-r4-raised-on-r4b"""


class TableUser(NamedTuple):
    """A winding that uses a table: its bus's BASKV and its end's ratedU (kV), for a ratio table's conversion."""

    base_kv: float
    rated_kv: float
    record_id: str


def table_mrid(number: int) -> str:
    return f"{PREFIX}{number}"


def _ratio_scale(number: int, users: list[TableUser]) -> float:
    """BASKV / ratedU, the same for every user of ratio table ``number``; none, or two values, raise."""
    if not users:
        raise ValueError(f"impedance correction table {number}: a ratio table no winding uses, so no base converts "
                         "its T (no case has one yet)")
    scales = {user.base_kv / user.rated_kv for user in users}
    if len(scales) > 1:
        names = ", ".join(user.record_id for user in users)
        raise ValueError(f"impedance correction table {number}: a ratio table whose users ({names}) have different "
                         "BASKV / ratedU, so one table cannot hold their ratios")
    return scales.pop()


def map_impedance_correction(native, users: dict[int, list[TableUser]]) -> Document:
    """``users``: table number -> the windings that use it (``transformer.table_users``)."""
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda record: record.table_number)
    if not records:
        return Document(name="impedance_correction", statements=[], profile=CIM_PROFILE)
    table_rows, angle_rows, ratio_rows = [], [], []
    for record in records:
        number = record.table_number
        table = table_mrid(number)
        points = record.points or []
        if len(points) < 2:
            raise ValueError(f"impedance correction table {number}: {len(points)} point(s), at least 2 needed")
        complex_factors = [point.t for point in points if point.f_imag]
        if complex_factors:
            raise NotImplementedError(f"impedance correction table {number}: Im(F) != 0 at T {complex_factors}, a "
                                      "complex factor (no CIM form)")
        angles = is_angle_table([point.t for point in points])
        table_rows.append(Row([table, str(number)], comment="angle table" if angles else "ratio table"))
        scale = None if angles else _ratio_scale(number, users.get(number, []))
        for index, point in enumerate(points, start=1):
            deviation = cell(impedance_deviation_percent(point.f_real))
            key = cell(cim_angle(point.t)) if angles else cell(point.t * scale)
            (angle_rows if angles else ratio_rows).append(Row([f"{table}_{index}", table, key, deviation, deviation]))
    statements = [Table("ImpedanceTapChangerTable", [Column("mRID"), Column("name")], table_rows)]
    point_columns = [Column("identifier"), Column("ImpedanceTapChangerTable")]
    deviations = [Column("rEnd1"), Column("xEnd1")]
    if angle_rows:
        statements.append(Table("ImpedanceTapChangerTablePoint", point_columns + [Column("angle", "deg")] + deviations,
                                angle_rows, comment="angle tables: angle = cim_angle(T) (deg); rEnd1 = xEnd1 = "
                                                    "100 x (F - 1) percent"))
    if ratio_rows:
        statements.append(Table("ImpedanceTapChangerTablePoint", point_columns + [Column("ratio")] + deviations,
                                ratio_rows, comment="ratio tables: ratio = T x BASKV / ratedU (pu of the end's "
                                                    "ratedU); rEnd1 = xEnd1 = 100 x (F - 1) percent"))
    return Document(name="impedance_correction", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))

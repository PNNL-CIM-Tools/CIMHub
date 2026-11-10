"""ImpedanceTapChangerTable -> Impedance correction (``EXPORT_MAPPING.md#impedance-correction``).

The inverse of the importer's R4b-10: an angle point's T is ``raw_angle(angle)``, a ratio point's ratio × ratedU /
BASKV of the winding that uses the table, and F = 1 + rEnd1 / 100 (``impedance_factor``). TABk names the table by
the number ``table_numbers`` gives.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.impedance_table import get_impedance_table
from cimhub_raw.exporter.identity import keyed_numbers
from cimhub_raw.importer.cimtbl.derived import impedance_factor, raw_angle
from cimhub_raw.importer.cimtbl.impedance_correction import POINT_CLASS, PREFIX

NATIVE_CLASS = schema.ImpedanceCorrectionRecord
CIM_CLASSES = ()  # a table is not conducting equipment; its users are transformer ends (E4's)
REL_TOL = 1e-9

SLOTS = {
    NATIVE_CLASS: {
        "table_number": Slot("written", "I: the ict_<I> key, else the next number (X2)"),
        "points": Slot("written", "the table's points (get_impedance_table), by T ascending"),
    },
    POINT_CLASS: {
        "t": Slot("written", "Ti: an angle point's raw_angle(angle) (deg), or a ratio point's ratio x ratedU / BASKV "
                             "of its users' winding (users that disagree, or none, raise)"),
        "f_real": Slot("written", "Re(Fi): 1 + rEnd1 / 100 (impedance_factor); rEnd1 != xEnd1, or rEnd2/3, xEnd2/3 "
                                  "set, raise"),
        "f_imag": Slot("rule", "Im(Fi): 0 (CIM's deviations are real)"),
    },
}


def table_numbers(context) -> dict[cim.ImpedanceTapChangerTable, int]:
    """Each table's number I, from its mRID ict_<I> (else the next number)."""
    return keyed_numbers(context.objects(cim.ImpedanceTapChangerTable), PREFIX)


def export(context) -> list[schema.ImpedanceCorrectionRecord]:
    """One Impedance correction per ImpedanceTapChangerTable, by number."""
    records = [schema.ImpedanceCorrectionRecord(table_number=number, points=_points(table))
               for table, number in table_numbers(context).items()]
    return sorted(records, key=lambda record: record.table_number)


def _points(table) -> list[schema.ImpedanceCorrectionPoint]:
    points = get_impedance_table(table)
    kinds = {(point.angle is not None, point.ratio is not None) for point in points}
    if kinds == {(True, False)}:
        t_values = [raw_angle(point.angle) for point in points]
    elif kinds == {(False, True)}:
        scale = _ratio_scale(table)
        t_values = [point.ratio * scale for point in points]
    else:
        raise ValueError(f"{describe(table)}: each point needs an angle or a ratio, one kind for the whole table "
                         "(PSS/E's T is one)")
    rows = []
    for point, t in zip(points, t_values):
        deviation = point.r[0] or 0.0
        if not math.isclose(deviation, point.x[0] or 0.0, rel_tol=REL_TOL) or any(point.r[1:]) or any(point.x[1:]):
            raise ValueError(f"{describe(table)}: a point's deviations r {point.r}, x {point.x}; PSS/E's F scales end "
                             "1's r and x alike")
        rows.append(schema.ImpedanceCorrectionPoint(t=t, f_real=impedance_factor(deviation), f_imag=0.0))
    return sorted(rows, key=lambda row: row.t)


def _ratio_scale(table) -> float:
    """ratedU / BASKV of the windings that use a ratio table: the same for each; none raises (no base)."""
    scales = set()
    for tabular in table.ImpedanceTapChangerTabular:
        end = tabular.TransformerEnd
        base_kv = get_base_voltage(end.Terminal.TopologicalNode, "kV", form="LL")
        scales.add(required_qty(end, "ratedU", "kV") / base_kv)
    if not scales:
        raise ValueError(f"{describe(table)}: a ratio table no winding uses, so no base converts its ratios")
    if max(scales) - min(scales) > REL_TOL * max(scales):
        raise ValueError(f"{describe(table)}: its users' ratedU / BASKV differ {sorted(scales)}; one table holds one")
    return min(scales)

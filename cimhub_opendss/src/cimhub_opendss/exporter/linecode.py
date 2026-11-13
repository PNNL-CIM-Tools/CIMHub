"""PerLengthImpedance -> OpenDSS ``LineCode`` (``EXPORT_MAPPING.md#linecode``).

Every PerLengthImpedance is written, used or not (E3), per metre (B1). C = b / (2 pi f) at the network's base
frequency (E5), which is also the code's ``baseFreq``; an unset b is C = 0, so the engine's 3.4/1.6 nF default never
applies (skill rule 8).
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.derived.capacitance import c_from_b
from cimhub_core.getters import describe
from cimhub_core.getters.line_impedance import get_phase_impedance_code, get_sequence_impedance_code
from cimhub_opendss.dss_writer import format_float
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.PerLengthPhaseImpedance, cim.PerLengthSequenceImpedance)
NATIVE_CLASS = schema.Linecode
NAMESPACE = "LineCode"
UNIT = "m"  # B1
IMPEDANCE_UNIT, ADMITTANCE_UNIT = f"ohm/{UNIT}", f"nS/{UNIT}"  # nS with Hz gives nF (c_from_b)
#: slots the schema types as text (the reader keeps the file's text), so the writer's float format never sees them
TEXT_SLOTS = ("C1", "C0", "baseFreq")

_SEQUENCE = "sequence code"
_MATRIX = "phase code"
_NOT_IN_CIM = "not in CIM (untranscribed on import)"
SLOTS = {NATIVE_CLASS: {
    "name": Slot("written", "Names"),
    "nphases": Slot("written", f"{_MATRIX}: conductorCount; {_SEQUENCE}: 3"),
    "r1": Slot("written", f"{_SEQUENCE}: r (ohm/m)"),
    "x1": Slot("written", f"{_SEQUENCE}: x (ohm/m)"),
    "r0": Slot("written", f"{_SEQUENCE}: r0 (ohm/m); unset raises"),
    "x0": Slot("written", f"{_SEQUENCE}: x0 (ohm/m); unset raises"),
    "C1": Slot("rule", f"{_SEQUENCE}: c_from_b(bch) (nF/m); unset -> 0"),
    "C0": Slot("rule", f"{_SEQUENCE}: c_from_b(b0ch) (nF/m); unset -> 0"),
    "units": Slot("written", "m (B1)"),
    "rmatrix": Slot("written", f"{_MATRIX}: r, lower triangle (ohm/m)"),
    "xmatrix": Slot("written", f"{_MATRIX}: x, lower triangle (ohm/m)"),
    "cmatrix": Slot("rule", f"{_MATRIX}: c_from_b(b), lower triangle (nF/m); unset -> zeros"),
    "baseFreq": Slot("written", "network.base_frequency (Hz); a calculatedFrequency that differs raises"),
    "normamps": Slot("unset", "no rating on a PerLengthImpedance (D9); the Line carries its own"),
    "emergamps": Slot("unset", "no rating on a PerLengthImpedance (D9); the Line carries its own"),
    "faultrate": Slot("unset", _NOT_IN_CIM), "pctperm": Slot("unset", _NOT_IN_CIM),
    "repair": Slot("unset", _NOT_IN_CIM), "Kron": Slot("unset", _NOT_IN_CIM),
    "Rg": Slot("not mapped", "PerLengthImpedance.rg set raises (not imported either)"),
    "Xg": Slot("not mapped", "PerLengthImpedance.xg set raises (not imported either)"),
    "rho": Slot("unset", _NOT_IN_CIM), "neutral": Slot("unset", _NOT_IN_CIM),
    "B1": Slot("not mapped", "C1 carries the susceptance"), "B0": Slot("not mapped", "C0 carries the susceptance"),
    "Seasons": Slot("unset", _NOT_IN_CIM), "Ratings": Slot("unset", _NOT_IN_CIM),
    "LineType": Slot("unset", _NOT_IN_CIM),
    "like": Slot("not mapped", "the writer never writes like="),
}}


def linecode_name(code: cim.PerLengthImpedance, names: Names) -> str:
    """The code's DSS name, as its record and every Line write it."""
    return names.name(code, NAMESPACE)


def export(context) -> list[schema.Linecode]:
    """One LineCode per PerLengthImpedance."""
    frequency = context.network.base_frequency.to("Hz")
    return [_linecode(code, context.names, frequency) for code in context.objects(*CIM_CLASSES)]


def _linecode(code: cim.PerLengthImpedance, names: Names, frequency: float) -> schema.Linecode:
    calculated = get_qty(code, "calculatedFrequency", "Hz")
    if calculated is not None and not math.isclose(calculated, frequency):
        raise ValueError(f"{describe(code)}: calculatedFrequency {calculated} Hz differs from the network's "
                         f"{frequency} Hz, the deck's baseFreq")
    earth = [name for name in ("rg", "xg") if getattr(code, name) is not None]
    if earth:
        raise ValueError(f"{describe(code)}: {earth} set; the earth return is not mapped")
    slots = dict(name=linecode_name(code, names), units=UNIT, baseFreq=frequency)
    if isinstance(code, cim.PerLengthPhaseImpedance):
        slots.update(_matrix_slots(code, frequency))
    else:
        slots.update(_sequence_slots(code, frequency))
    for slot in TEXT_SLOTS:
        if slot in slots:
            slots[slot] = format_float(slots[slot])
    return NATIVE_CLASS(**slots)


def _matrix_slots(code: cim.PerLengthPhaseImpedance, frequency: float) -> dict:
    matrix = get_phase_impedance_code(code, IMPEDANCE_UNIT, ADMITTANCE_UNIT)
    if matrix.g is not None and any(value != 0 for value in matrix.g.values()):
        raise ValueError(f"{describe(code)}: g is set; a DSS line has no shunt conductance")
    keys = [(row, column) for row in range(1, matrix.conductor_count + 1) for column in range(1, row + 1)]
    return dict(
        nphases=matrix.conductor_count,
        rmatrix=[matrix.r[key] for key in keys],
        xmatrix=[matrix.x[key] for key in keys],
        cmatrix=[0.0 if matrix.b is None else c_from_b(matrix.b[key], frequency) for key in keys],
    )


def _sequence_slots(code: cim.PerLengthSequenceImpedance, frequency: float) -> dict:
    values = get_sequence_impedance_code(code, IMPEDANCE_UNIT, ADMITTANCE_UNIT)
    return dict(nphases=3, **sequence_slots(code, values, frequency))


def sequence_slots(owner, values, frequency: float) -> dict:
    """``r1 x1 r0 x0 C1 C0`` from a SequenceImpedance in ohm and nS per one length unit (a code's, or a
    lumped line's per km). An unset zero sequence raises; an unset b is C = 0; a nonzero g raises."""
    unset = [name for name in ("r0", "x0") if getattr(values, name) is None]
    if unset:
        raise ValueError(f"{describe(owner)}: {unset} unset; DSS would take its own zero-sequence default")
    if any(value not in (None, 0.0) for value in (values.g, values.g0)):
        raise ValueError(f"{describe(owner)}: gch or g0ch is set; a DSS line has no shunt conductance")
    return dict(
        r1=values.r, x1=values.x, r0=values.r0, x0=values.x0,
        C1=0.0 if values.b is None else c_from_b(values.b, frequency),
        C0=0.0 if values.b0 is None else c_from_b(values.b0, frequency),
    )

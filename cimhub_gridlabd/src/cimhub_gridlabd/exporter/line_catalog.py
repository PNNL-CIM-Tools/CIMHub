"""The line catalogs a deck's lines name: conductors, ``line_spacing``, ``line_configuration`` and
``triplex_line_configuration`` (``EXPORT_MAPPING.md#x1-lines-and-switches``; skill ``conductor-geometry``).

CIM's templates are shared by lines on different phases, while a GLM configuration names its conductors by phase
(``conductor_A``, ``z23``). So a template becomes one GLM object per way the lines use it (a ``GeometryKey`` or a
``MatrixKey``), named as the template when there is one way and ``<template>_<letters>`` otherwise:

- geometry (``WireConfiguration``): a ``line_configuration`` with ``conductor_X`` = the wire at the sequence number
  of the line's phase X, and a ``line_spacing`` with ``distance_XY`` and ``distance_XE`` as the spacing holds them
  (``get_stored_distances``; a pair or a height it leaves out is GridLAB-D's 0, no coupling). No impedance is ever
  computed from geometry. A split-phase line's is a ``triplex_line_configuration``: GridLAB-D places its conductors
  from ``diameter`` and ``insulation_thickness`` (D12 = d + 2t, D1N = D2N = d + t, the importer's S2-8 inverted).
- matrix (``PerLengthImpedance``): ``zXY`` = r + jx and ``cXY`` = C(b) (``c_from_b`` at the base frequency) by the
  line's phase letters; a neutral row is Kron-reduced out (GLM's matrix is phases only); a sequence code is
  expanded by the getter (``expand_sequence``: a transposed line, GLM has no sequence form). A triplex matrix's b is
  dropped and logged (X27): GridLAB-D's ``triplex_line`` has no shunt admittance (``triplex_line.cpp``), so no
  ``triplex_line_configuration`` slot holds it.

A conductor is one GLM class per configuration kind: ``triplex_line_conductor`` in a triplex configuration,
``underground_line_conductor`` where any of the configuration's wires is a cable, ``overhead_line_conductor``
otherwise.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.derived.capacitance import c_from_b
from cimhub_core.derived.kron import kron_reduce
from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters.line_impedance import get_line_phase_impedance_matrix
from cimhub_core.getters.spacing import get_stored_distances
from cimhub_core.getters.wire import get_configuration_wires, get_wire_info
from cimhub_gridlabd.exporter.units import glm_unit
from cimhub_gridlabd.schema import gridlabd as schema

#: GLM's conductor letter for a CIM phase: ABCN on a line, 12N on a triplex line
LETTER = {cim.SinglePhaseKind.A: "A", cim.SinglePhaseKind.B: "B", cim.SinglePhaseKind.C: "C",
          cim.SinglePhaseKind.N: "N", cim.SinglePhaseKind.s1: "1", cim.SinglePhaseKind.s2: "2"}
#: line_spacing's pair slots in its order, and its heights
PAIRS = ("AB", "AC", "BC", "AN", "BN", "CN")
MATRIX_INDEX = {"A": 1, "B": 2, "C": 3, "1": 1, "2": 2}
#: two stored triplex distances that should be equal (D1N, D2N) agree to GLM's six digits
TRIPLEX_REL_TOL = 1e-5
#: b is read per the length GLM's C is per, so ``c_from_b`` (nS gives nF) applies directly
SUSCEPTANCE_UNIT = "nS/mile"
#: Kersting (3rd ed., eq. 4.89): a copper tape shield's resistance is 18.826 / (d_s [in] x T [mil]) ohm/mile
TAPE_SHIELD_RESISTANCE = 18.826
#: a bare wire buried in an underground configuration has no jacket in CIM, but GridLAB-D needs an outer diameter
#: above the conductor's: the Java CIMHub exporter's 1.2 x diameter (the importer's canBury note)
BARE_BURIED_OUTER = 1.2
if glm_unit(schema.UndergroundLineConductor, "shield_resistance") != "ohm/mile" or glm_unit(
        schema.UndergroundLineConductor, "shield_diameter") != "in":
    raise ValueError("GLM shield_resistance/shield_diameter units changed; tape_shield_resistance must follow them")
if glm_unit(schema.LineConfiguration, "c11") != "nF/mile":
    raise ValueError("GLM line_configuration c11 is no longer in nF/mile; SUSCEPTANCE_UNIT must follow it")

_NOT_IN_CIM = "not in CIM; GridLAB-D's default"
_log = logging.getLogger(__name__)
_RATING = Slot("unset", "the ratings are each line's own (D9): written on the line")
_RATINGS = ("rating_summer_continuous", "rating_summer_emergency", "rating_winter_continuous",
            "rating_winter_emergency")


class GeometryKey(NamedTuple):
    configuration: cim.WireConfiguration
    conductors: tuple[tuple[str, int], ...]  # (GLM letter, sequence number), in the line's conductor order
    triplex: bool


class MatrixKey(NamedTuple):
    code: cim.PerLengthImpedance
    letters: tuple[str, ...]  # the line's conductor letters in sequence order, neutrals included
    triplex: bool


class Catalog(NamedTuple):
    """Every catalog record, and the configuration name each key is written under."""

    records: list
    names: dict  # GeometryKey | MatrixKey -> configuration name


def _conductor_slots(native_class: type, written: dict[str, Slot]) -> dict[str, Slot]:
    return with_default(native_class, {"name": Slot("written", "Names; <wire>_<class> when one WireInfo is two GLM "
                                                               "classes"), **written},
                        Slot("unset", _NOT_IN_CIM))


_RESISTANCE = Slot("written", "get_wire_info: rAC50 (GridLAB-D's 50 C value, the GLM importer's), else rAC25 (the "
                              "DSS importer's); neither raises")
_GMR = Slot("written", "get_wire_info.gmr; unset raises")
_DIAMETER = Slot("written", "2 x get_wire_info.radius; unset: unset (GridLAB-D reads it only for line capacitance)")
_SUMMER = {"rating_summer_continuous": Slot("written", "the wire's normal limit, else ratedCurrent"),
           "rating_summer_emergency": Slot("written", "the wire's emergency limit")}

SLOTS = {
    schema.OverheadLineConductor: _conductor_slots(schema.OverheadLineConductor, {
        "geometric_mean_radius": _GMR, "resistance": _RESISTANCE, "diameter": _DIAMETER, **_SUMMER}),
    schema.TriplexLineConductor: _conductor_slots(schema.TriplexLineConductor, {
        "geometric_mean_radius": _GMR, "resistance": _RESISTANCE, **_SUMMER}),
    schema.UndergroundLineConductor: _conductor_slots(schema.UndergroundLineConductor, {
        "conductor_gmr": _GMR, "conductor_resistance": _RESISTANCE, "conductor_diameter": _DIAMETER,
        "outer_diameter": Slot("written", "a cable's diameterOverJacket; a bare wire's BARE_BURIED_OUTER x its "
                                          "diameter (rule: CIM has no jacket, GridLAB-D needs one)"),
        "neutral_gmr": Slot("written", "neutralStrandGmr (ConcentricNeutralCableInfo)"),
        "neutral_diameter": Slot("written", "2 x neutralStrandRadius"),
        "neutral_resistance": Slot("written", "neutralStrandRDC20"),
        "neutral_strands": Slot("written", "neutralStrandCount"),
        "shield_thickness": Slot("written", "tapeThickness (TapeShieldCableInfo)"),
        "shield_diameter": Slot("written", "diameterOverScreen (TapeShieldCableInfo)"),
        "shield_gmr": Slot("written", "tape_shield_gmr: diameterOverScreen / 2, the Java exporter's (GridLAB-D tells "
                                      "a tape-shield cable by shield_gmr > 0)"),
        "shield_resistance": Slot("written", "tape_shield_resistance: Kersting eq. 4.89, the Java exporter's"),
        **_SUMMER}),
    schema.LineSpacing: with_default(schema.LineSpacing, {
        "name": Slot("written", "Names; <spacing>_<letters> when lines use it on different phases"),
        **{f"distance_{pair}": Slot("written", "get_stored_distances between the two phases' sequence numbers; "
                                               "absent: unset (GridLAB-D's 0, no coupling)") for pair in PAIRS},
        **{f"distance_{letter}E": Slot("written", "the stored height; an XYSpacing's y (a line with a "
                                                  "ySpacingOffset raises)") for letter in "ABCN"},
    }, Slot("unset", _NOT_IN_CIM)),
    schema.LineConfiguration: with_default(schema.LineConfiguration, {
        "name": Slot("written", "Names; <template>_<letters> when lines use it on different phases"),
        "spacing": Slot("written", "geometry: the line_spacing"),
        **{f"conductor_{letter}": Slot("written", "geometry: the wire at the phase's sequence number")
           for letter in "ABCN"},
        **{f"z{i}{j}": Slot("written", "matrix: r + jx (ohm/mile) by phase letter, neutrals Kron-reduced")
           for i in "123" for j in "123"},
        **{f"c{i}{j}": Slot("written", "matrix: c_from_b(b) (nF/mile) at the base frequency; b unset: unset (0)")
           for i in "123" for j in "123"},
        **{slot: _RATING for slot in _RATINGS},
    }, Slot("unset", _NOT_IN_CIM)),
    schema.TriplexLineConfiguration: with_default(schema.TriplexLineConfiguration, {
        "name": Slot("written", "Names, as line_configuration"),
        **{f"conductor_{letter}": Slot("written", "geometry: the wire at s1, s2, N") for letter in "12N"},
        "insulation_thickness": Slot("written", "t = D12 - D1N of the spacing (S2-8 inverted)"),
        "diameter": Slot("written", "d = 2 D1N - D12"),
        **{f"z{i}{j}": Slot("written", "matrix: r + jx (ohm/mile) on s1, s2, N Kron-reduced") for i in "12"
           for j in "12"},
        **{slot: _RATING for slot in _RATINGS},
    }, Slot("unset", _NOT_IN_CIM)),
}


def build_catalog(keys: list, names, frequency: float, lines_by_key: dict) -> Catalog:
    """The records of every key the lines use (``lines_by_key``: a line per MatrixKey, to read its matrix)."""
    configuration_names = _template_names(keys, lambda key: _template(key), lambda key: _letters(key), names)
    records = []
    conductors: dict[tuple[cim.WireInfo, type], None] = {}
    spacings: dict[tuple[cim.WireSpacing, tuple], None] = {}
    for key in keys:
        if isinstance(key, GeometryKey):
            for wire, conductor_class in key_wires(key):
                conductors.setdefault((wire, conductor_class))
            if not key.triplex:
                spacings.setdefault((_spacing(key.configuration), key.conductors))
    conductor_names = _template_names(list(conductors), lambda item: item[0],
                                      lambda item: item[1].class_name.split("_")[0], names)
    spacing_names = _template_names(list(spacings), lambda item: item[0],
                                    lambda item: "".join(letter for letter, _ in item[1]), names)
    for (wire, conductor_class), name in conductor_names.items():
        records.append(_conductor(wire, conductor_class, name))
    for (spacing, conductors_on), name in spacing_names.items():
        records.append(_line_spacing(spacing, conductors_on, name))
    for key in keys:
        name = configuration_names[key]
        if isinstance(key, MatrixKey):
            records.append(_matrix_configuration(key, lines_by_key[key], name, frequency))
        elif key.triplex:
            records.append(_triplex_configuration(key, name, conductor_names))
        else:
            records.append(_geometry_configuration(key, name, conductor_names,
                                                   spacing_names[(_spacing(key.configuration), key.conductors)]))
    return Catalog(records, configuration_names)


def _template(key):
    return key.configuration if isinstance(key, GeometryKey) else key.code


def _letters(key) -> str:
    return "".join(letter for letter, _ in key.conductors) if isinstance(key, GeometryKey) else "".join(key.letters)


def _template_names(items: list, template_of, suffix_of, names) -> dict:
    """Each item's GLM name: its template's, or ``<template>_<suffix>`` when several items share the template."""
    by_template = defaultdict(list)
    for item in items:
        by_template[template_of(item)].append(item)
    named = {}
    for template, shared in by_template.items():
        for item in shared:
            named[item] = names.name(template) if len(shared) == 1 else names.name(template,
                                                                                    suffix="_" + suffix_of(item))
    return named


def _spacing(configuration: cim.WireConfiguration) -> cim.WireSpacing:
    if configuration.WireSpacing is None:
        raise ValueError(f"WireConfiguration {configuration.mRID!r}: has no WireSpacing")
    return configuration.WireSpacing


def key_wires(key: GeometryKey) -> list[tuple[cim.WireInfo, type]]:
    wires = dict(get_configuration_wires(key.configuration))
    numbers = [number for _, number in key.conductors]
    missing = [number for number in numbers if number not in wires]
    if missing:
        raise ValueError(f"WireConfiguration {key.configuration.mRID!r}: has no wire at sequence numbers {missing}")
    if key.triplex:
        conductor_class = schema.TriplexLineConductor
    elif any(isinstance(wires[number], cim.CableInfo) for number in numbers):
        conductor_class = schema.UndergroundLineConductor
    else:
        conductor_class = schema.OverheadLineConductor
    return [(wires[number], conductor_class) for number in numbers]


def _conductor(wire: cim.WireInfo, conductor_class: type, name: str):
    if conductor_class is schema.UndergroundLineConductor:
        gmr_slot, resistance_slot, diameter_slot = "conductor_gmr", "conductor_resistance", "conductor_diameter"
    else:
        gmr_slot, resistance_slot, diameter_slot = "geometric_mean_radius", "resistance", "diameter"
    length_unit = glm_unit(conductor_class, gmr_slot)
    values = get_wire_info(wire, length_unit=length_unit,
                           resistance_unit=glm_unit(conductor_class, resistance_slot),
                           current_unit=glm_unit(conductor_class, "rating_summer_continuous"))
    resistance = values.r_ac50 if values.r_ac50 is not None else values.r_ac25
    if resistance is None or values.gmr is None:
        raise ValueError(f"{type(wire).__name__} {wire.mRID!r}: GridLAB-D needs its gmr and AC resistance")
    slots = {"name": name, gmr_slot: values.gmr, resistance_slot: resistance,
             "rating_summer_continuous": values.limits.normal if values.limits.normal is not None
             else values.rated_current,
             "rating_summer_emergency": values.limits.emergency}
    if conductor_class is not schema.TriplexLineConductor:
        radius = get_wire_info(wire, length_unit=glm_unit(conductor_class, diameter_slot)).radius
        slots[diameter_slot] = None if radius is None else 2 * radius
    if conductor_class is schema.UndergroundLineConductor:
        if values.cable is not None:
            slots.update(_cable_slots(wire))
        elif slots[diameter_slot] is None:
            raise ValueError(f"{type(wire).__name__} {wire.mRID!r}: a buried bare wire needs its radius")
        else:
            slots["outer_diameter"] = BARE_BURIED_OUTER * slots[diameter_slot]
    return conductor_class(**slots)


def _cable_slots(wire: cim.CableInfo) -> dict:
    inch = glm_unit(schema.UndergroundLineConductor, "outer_diameter")
    feet = glm_unit(schema.UndergroundLineConductor, "neutral_gmr")
    cable = get_wire_info(wire, length_unit=inch,
                          resistance_unit=glm_unit(schema.UndergroundLineConductor, "neutral_resistance")).cable
    in_feet = get_wire_info(wire, length_unit=feet).cable
    radius = cable.neutral_strand_radius
    slots = {"outer_diameter": cable.diameter_over_jacket, "neutral_gmr": in_feet.neutral_strand_gmr,
             "neutral_diameter": None if radius is None else 2 * radius,
             "neutral_resistance": cable.neutral_strand_r_dc20, "neutral_strands": cable.neutral_strand_count,
             "shield_thickness": cable.tape_thickness, "shield_diameter": cable.diameter_over_screen}
    if isinstance(wire, cim.TapeShieldCableInfo):
        # pint's mil is not an inch's thousandth; its thou is
        thickness_mil = get_wire_info(wire, length_unit="thou").cable.tape_thickness
        if cable.diameter_over_screen is None or thickness_mil is None:
            raise ValueError(f"TapeShieldCableInfo {wire.mRID!r}: GridLAB-D needs diameterOverScreen and tapeThickness")
        slots["shield_gmr"] = tape_shield_gmr(in_feet.diameter_over_screen)
        slots["shield_resistance"] = tape_shield_resistance(cable.diameter_over_screen, thickness_mil)
    return slots


def tape_shield_gmr(diameter_over_screen: float) -> float:
    """A tape shield's GMR, the radius of its thin cylinder (the Java exporter's), in the diameter's unit."""
    return diameter_over_screen / 2


def tape_shield_resistance(diameter_over_screen_inch: float, tape_thickness_mil: float) -> float:
    """A copper tape shield's resistance in ohm/mile (Kersting eq. 4.89), from d_s in inches and T in mils."""
    return TAPE_SHIELD_RESISTANCE / (diameter_over_screen_inch * tape_thickness_mil)


def _line_spacing(spacing: cim.WireSpacing, conductors: tuple[tuple[str, int], ...], name: str) -> schema.LineSpacing:
    stored = get_stored_distances(spacing, glm_unit(schema.LineSpacing, "distance_AB"))
    number_of = dict(conductors)
    slots = {"name": name}
    for pair in PAIRS:
        if pair[0] in number_of and pair[1] in number_of:
            numbers = tuple(sorted((number_of[pair[0]], number_of[pair[1]])))
            slots[f"distance_{pair}"] = stored.distances.get(numbers)
    for letter, number in conductors:
        slots[f"distance_{letter}E"] = stored.heights.get(number)
    return schema.LineSpacing(**slots)


def _geometry_configuration(key: GeometryKey, name: str, conductor_names: dict,
                            spacing_name: str) -> schema.LineConfiguration:
    slots = {"name": name, "spacing": spacing_name}
    for (letter, _), wire_and_class in zip(key.conductors, key_wires(key), strict=True):
        slots[f"conductor_{letter}"] = conductor_names[wire_and_class]
    return schema.LineConfiguration(**slots)


def _triplex_configuration(key: GeometryKey, name: str, conductor_names: dict) -> schema.TriplexLineConfiguration:
    number_of = dict(key.conductors)
    if sorted(number_of) != ["1", "2", "N"]:
        raise ValueError(f"WireConfiguration {key.configuration.mRID!r}: a triplex line needs s1, s2 and N, not "
                         f"{sorted(number_of)}")
    stored = get_stored_distances(_spacing(key.configuration),
                                  glm_unit(schema.TriplexLineConfiguration, "insulation_thickness"))

    def distance(first: str, second: str) -> float:
        pair = tuple(sorted((number_of[first], number_of[second])))
        if pair not in stored.distances:
            raise ValueError(f"WireConfiguration {key.configuration.mRID!r}: its spacing has no {first}-{second} "
                             f"distance")
        return stored.distances[pair]

    d12, d1n, d2n = distance("1", "2"), distance("1", "N"), distance("2", "N")
    if not math.isclose(d1n, d2n, rel_tol=TRIPLEX_REL_TOL):
        raise ValueError(f"WireConfiguration {key.configuration.mRID!r}: D1N {d1n} and D2N {d2n} differ; GridLAB-D's "
                         f"triplex spacing is symmetric")
    slots = {"name": name, "insulation_thickness": d12 - d1n, "diameter": 2 * d1n - d12}
    for (letter, _), wire_and_class in zip(key.conductors, key_wires(key), strict=True):
        slots[f"conductor_{letter}"] = conductor_names[wire_and_class]
    return schema.TriplexLineConfiguration(**slots)


def _matrix_configuration(key: MatrixKey, line: cim.ACLineSegment, name: str, frequency: float):
    configuration_class = schema.TriplexLineConfiguration if key.triplex else schema.LineConfiguration
    matrix = get_line_phase_impedance_matrix(line, glm_unit(configuration_class, "z11"), SUSCEPTANCE_UNIT,
                                             expand_sequence=True)
    neutrals = [index for index, letter in enumerate(key.letters, start=1) if letter == "N"]
    z = {pair: complex(matrix.r[pair], matrix.x[pair]) for pair in matrix.r}
    if neutrals:
        z = kron_reduce(z, neutrals)
    kept = [letter for letter in key.letters if letter != "N"]
    slots = {"name": name}
    for (row, column), value in z.items():
        first, second = MATRIX_INDEX[kept[row - 1]], MATRIX_INDEX[kept[column - 1]]
        complex_value = schema.Complex(real=value.real, imag=value.imag)
        slots[f"z{first}{second}"] = slots[f"z{second}{first}"] = complex_value
    if matrix.b is not None and not key.triplex:
        phase_rows = [index for index, letter in enumerate(key.letters, start=1) if letter != "N"]
        for (row, column), susceptance in matrix.b.items():
            if row in phase_rows and column in phase_rows:
                first, second = MATRIX_INDEX[key.letters[row - 1]], MATRIX_INDEX[key.letters[column - 1]]
                slots[f"c{first}{second}"] = slots[f"c{second}{first}"] = c_from_b(susceptance, frequency)
    elif matrix.b is not None and any(matrix.b.values()):
        _log.warning("%s: a triplex matrix's b is not written; GridLAB-D's triplex_line has no shunt admittance "
                     "(X27)", name)
    return configuration_class(**slots)

"""The RAW exporter, sub-slice by sub-slice (``docs/EXPORT_MAPPING.md``): E0 (framework, case data, zone, area,
bus), E1 (branch, series capacitor, switch, multi-section line, ratings), E2 (load, fixed and switched shunt), E3
(generator), E4 (transformer, impedance correction).

Each case and atom goes RAW -> ``.cimtbl`` -> CIM -> RAW records, and every exported table is compared with the RAW
as read, record by record (by key) and slot by slot. ``unset`` slots are skipped; blanks on both sides are filled
with the schema's ``raw_default``. What differs must be exactly the expected differences below.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.export_slots import check_slots
from cimhub_core.graph_model import _get_identifier
from cimhub_raw.exporter import (area_interchange, branch, bus, case_identification, fixed_shunt, generator,
                                 impedance_correction, load, multi_section_line, switch, switched_shunt, transformer,
                                 zone)
from cimhub_raw.exporter.cim_to_raw import EXPORT_ORDER, RawExporter, export_context, export_tables
from cimhub_raw.exporter.identity import keyed_ids
from cimhub_raw.exporter.ratings import ratings_in_current
from cimhub_raw.importer.cimtbl import area_interchange as import_area
from cimhub_raw.importer.cimtbl import branch as import_branch
from cimhub_raw.importer.cimtbl import bus as import_bus
from cimhub_raw.importer.cimtbl import case_identification as import_case
from cimhub_raw.importer.cimtbl import fixed_shunt as import_fixed_shunt
from cimhub_raw.importer.cimtbl import generator as import_generator
from cimhub_raw.importer.cimtbl import impedance_correction as import_impedance_correction
from cimhub_raw.importer.cimtbl import load as import_load
from cimhub_raw.importer.cimtbl import multi_section_line as import_multi_section_line
from cimhub_raw.importer.cimtbl import switch as import_switch
from cimhub_raw.importer.cimtbl import switched_shunt as import_switched_shunt
from cimhub_raw.importer.cimtbl import transformer as import_transformer
from cimhub_raw.importer.cimtbl import zone as import_zone
from cimhub_raw.importer.cimtbl.derived import band_fractions, mva_from_per_unit, per_unit_from_mva, reactive_band
from cimhub_raw.importer.cimtbl.records import raw_defaults
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.raw34_writer import Raw34Writer

TESTS = Path(__file__).parent
FIXTURES = sorted([*TESTS.glob("atoms/*/*.raw"), *TESTS.glob("cases/*/*.raw")])
E0_MODULES = (case_identification, zone, area_interchange, bus)
E1_MODULES = (*E0_MODULES, branch, switch, multi_section_line)
E2_MODULES = (*E1_MODULES, load, fixed_shunt, switched_shunt)
E3_MODULES = (*E2_MODULES, generator)
E4_MODULES = (*E3_MODULES, transformer, impedance_correction)
LANDED = E4_MODULES
REL_TOL = 1e-9

#: export slots written although the importer lists the field untranscribed
NOT_UNSET = {
    (schema.BusRecord, "area"),  # recovered by the R5 trace
    (schema.SwitchRecord, "x"),  # 0.0001: the format gives a system switching device's X no default
}

#: blanks the importer fills outside the schema's raw_default (RAW-17: "the present option setting"; a transformer's
#: RMA/RMI and VMA/VMI defaults hang on CW and COD, R4: every blank one in the fixtures is a COD 0 winding under CW 1)
IMPORT_DEFAULTS = {
    schema.CaseIdentificationRecord: {"system_base_frequency": import_case.DEFAULT_BASE_FREQUENCY,
                                      "branch_ratings_units": 0, "transformer_ratings_units": 0},
    schema.TransformerRecord: {f"{slot}{k}": value for k in (1, 2, 3)
                               for slot, value in (("rma", 1.1), ("rmi", 0.9), ("vma", 1.1), ("vmi", 0.9))},
}

_ZONE_1 = ("ZoneRecord", "1", "<extra>")  # a zone the buses name without a Zone record: synthesized on import
_ISOLATED = {("BusRecord", "303", "area"), ("BusRecord", "303", "bus_type")}  # IDE 4, untraced: 1 and blank

#: fixture stem -> {(record class, key, slot)}: the expected differences (EXPORT_MAPPING.md), besides MET off a tie
#: (``_metered_off_a_tie``)
EXPECTED = {
    "areas": _ISOLATED,
    "facts_vsc": _ISOLATED,
    "two_terminal": _ISOLATED,
    # bus 3 untraced (area 2); load 2 A's ZONE off its bus's (E2-1); load 3 1's blank AREA and ZONE: its group's, its bus's
    "loads": {_ZONE_1, ("ZoneRecord", "2", "<extra>"), ("BusRecord", "3", "area"), ("LoadRecord", "2_A", "zone"),
              ("LoadRecord", "3_1", "area"), ("LoadRecord", "3_1", "zone")},
    "plant_and_facts": {_ZONE_1, ("SwitchedShuntRecord", "3", "vswlo")},  # no plant: VSWLO 0 listed (R2b-1)
    "mixed_base": {_ZONE_1, ("BranchRecord", "2_3_1", "length")},  # a series capacitor's LEN (R1b-2)
    # NXFRAT 1 with nothing rated: the flag says nothing, and comes back 0
    "two_bus_node_breaker": {_ZONE_1, ("CaseIdentificationRecord", "0", "branch_ratings_units")},
    "generators": {_ZONE_1, ("GeneratorRecord", "5_1", "rated_mva")},  # a blank MBASE comes back SBASE
    # WMOD 2 comes back 1 with its WPF and a connection-only plant's RMPCT blank (R3c-1, R3c-3); WMOD 3's listed
    # IREG and VS are not written (R3c-2); a connection's ZR (R3c-3)
    "renewables": {_ZONE_1, *(("GeneratorRecord", "2_W", slot) for slot in ("wmod", "wpf", "rmpct")),
                   ("GeneratorRecord", "4_W1", "wmod"), ("GeneratorRecord", "5_S", "regulated_bus_number"),
                   ("GeneratorRecord", "5_S", "regulated_voltage_setpoint"), ("GeneratorRecord", "6_S2", "zr")},
    "step_up": {_ZONE_1, ("GeneratorRecord", "2_G2", "gtap")},  # GTAP without a step-up (R3b-4)
    # CW, CZ, CM 2 and 3 come back 1 with their values in pu (A, B, E); a 3-winding unit's pair bases come back SBASE
    "transformers": {_ZONE_1,
                     *(("TransformerRecord", "1_2_0_1", slot) for slot in ("cw", "cz", "cm", "mag1", "mag2", "r1_2",
                                                                          "x1_2", "windv1", "windv2", "rma1", "rmi1")),
                     *(("TransformerRecord", "2_6_0_1", slot) for slot in ("cw", "cz", "r1_2", "x1_2")),
                     *(("TransformerRecord", "6_7_4_2", f"{kind}{pair}") for pair in ("1_2", "2_3", "3_1")
                       for kind in ("r", "x", "sbase")), ("TransformerRecord", "6_7_4_2", "cz")},
    # R4b: a voltage control's extended steps (Q, R4b-5), 0 deg off a shifter's grid (K, R4b-3), CW 2 (N), COD 0
    # ranges no tap holds come back blank (O, R4b-4; P's were blank), a negative CONT positive (S, R4b-8)
    "forms_r4b": {_ZONE_1, ("TransformerRecord", "1_6_0_Q", "ntp1"), ("TransformerRecord", "1_6_0_Q", "rma1"),
                  *(("TransformerRecord", key, slot) for key in ("2_5_0_K", "6_7_0_O")
                    for slot in ("rma1", "rmi1")),
                  *(("TransformerRecord", "3_4_0_N", slot) for slot in ("cw", "windv1", "windv2", "rma1", "rmi1")),
                  ("TransformerRecord", "5_6_0_S", "cont1")},
    **{stem: {_ZONE_1} for stem in ("switches", "line_shunts", "multi_section_line", "fixed_shunts",
                                    "switched_shunts")},
    # areas and zones named by their own number come back blank
    "IEEE118_all_hydro_25_clean_4_subs": {(record, key, slot) for record, slot in
                                          (("ZoneRecord", "zone_name"), ("AreaInterchangeRecord", "name"))
                                          for key in ("1", "2", "3")},
    "240busWECC_2018_PSS": {("CaseIdentificationRecord", "0", "ratings")},  # gains the twelve default RATINGs
}


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _network(path: Path):
    native = Raw34Reader(str(path)).read_all()
    # the model name must not be a document stem (the multi_section_line atom)
    return native, raw_to_cim(native, name=f"{path.stem}_case")


def _round_trip(path: Path, modules):
    native, network = _network(path)
    return native, export_tables(network, modules)


def _atom(folder: str, stem: str) -> Path:
    return TESTS / "atoms" / folder / f"{stem}.raw"


def _get(network, cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)


def _metered_off_a_tie(native) -> set[tuple[str, str, str]]:
    """MET / METERED 2 on a device inside one AREA comes back 1: off a tie the metered end has no CIM home
    (RAW-22)."""
    area = {record.bus_number: record.area for record in native.list_by_class(schema.BusRecord)}
    return {(native_class.__name__, str(_get_identifier(record)), "metered_end")
            for native_class in (schema.BranchRecord, schema.SwitchRecord)
            for record in native.list_by_class(native_class)
            if (record.metered_end or 1) >= 2 and area[record.from_bus_number] == area[record.to_bus_number]}


def _own_bus_swreg(native) -> set[tuple[str, str, str]]:
    """SWREG 0 (the shunt's own bus) comes back I (E2-2); MODSW 6 leaves SWREG blank."""
    return {("SwitchedShuntRecord", str(_get_identifier(record)), "swreg")
            for record in native.list_by_class(schema.SwitchedShuntRecord)
            if not record.swreg and record.modsw != import_switched_shunt.FACTS}


def _own_bus_ireg(native) -> set[tuple[str, str, str]]:
    """IREG 0 (the plant's own bus) comes back I (E3-4); WMOD 3 writes no IREG (R3c-2)."""
    return {("GeneratorRecord", str(_get_identifier(record)), "regulated_bus_number")
            for record in native.list_by_class(schema.GeneratorRecord)
            if not record.regulated_bus_number and record.wmod != import_generator.FIXED_POWER_FACTOR}


def _nominal_zero(native) -> set[tuple[str, str, str]]:
    """NOMVk 0 (the bus's BASKV) comes back as BASKV, the end's ratedU (R4)."""
    return {("TransformerRecord", str(_get_identifier(record)), f"nomv{k}")
            for record in native.list_by_class(schema.TransformerRecord)
            for k in ((1, 2, 3) if record.k else (1, 2)) if not getattr(record, f"nomv{k}")}


def _same(left, right) -> bool:
    if isinstance(left, schema.ImpedanceCorrectionPoint) and isinstance(right, schema.ImpedanceCorrectionPoint):
        return all(_same(getattr(left, slot), getattr(right, slot)) for slot in ("t", "f_real", "f_imag"))
    if isinstance(left, list) or isinstance(right, list):  # RATE1..RATE12, a table's points
        return left is not None and right is not None and len(left) == len(right) and all(map(_same, left, right))
    if isinstance(left, float) or isinstance(right, float):
        return left is not None and right is not None and math.isclose(float(left), float(right), rel_tol=REL_TOL)
    return left == right


def _value(record, slot: str, defaults: dict):
    value = getattr(record, slot)
    if isinstance(value, str):
        value = value.strip()
    return defaults.get(slot) if value in (None, "") else value


def _ratings(case) -> list[tuple]:
    return [(rating.rating_set_number, rating.rating_name, rating.rating_description) for rating in case.ratings or []]


def _differences(native, exported, modules) -> set[tuple[str, str, str]]:
    """``(record class, key, slot)`` of every compared slot that differs, and ``(class, key, '<missing>'/'<extra>')``
    for a record on one side only."""
    found = set()
    for module in modules:
        native_class = module.NATIVE_CLASS
        slots = module.SLOTS[native_class]
        defaults = {**raw_defaults(native_class), **IMPORT_DEFAULTS.get(native_class, {})}
        original = {str(_get_identifier(record)): record for record in native.list_by_class(native_class)}
        written = {str(_get_identifier(record)): record for record in exported.list_by_class(native_class)}
        name = native_class.__name__
        found |= {(name, key, "<missing>") for key in original.keys() - written.keys()}
        found |= {(name, key, "<extra>") for key in written.keys() - original.keys()}
        for key in original.keys() & written.keys():
            for slot, how in slots.items():
                if how.kind == "unset":
                    continue
                if native_class is schema.CaseIdentificationRecord and slot == "ratings":
                    if _ratings(original[key]) != _ratings(written[key]):
                        found.add((name, key, slot))
                elif not _same(_value(original[key], slot, defaults), _value(written[key], slot, defaults)):
                    found.add((name, key, slot))
    return found


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.stem)
def test_round_trip(path):
    native, exported = _round_trip(path, LANDED)
    assert _differences(native, exported, LANDED) == (EXPECTED.get(path.stem, set()) | _metered_off_a_tie(native)
                                                      | _own_bus_swreg(native) | _own_bus_ireg(native)
                                                      | _nominal_zero(native))


def test_e0_wecc240_gains_the_default_rating_records():
    _, exported = _round_trip(TESTS / "cases" / "WECC240" / "240busWECC_2018_PSS.raw", E0_MODULES)
    case = exported.first(schema.CaseIdentificationRecord)
    assert _ratings(case) == [(n, f"RATE{n}", f"RATING SET {n}") for n in range(1, 13)]


@pytest.mark.parametrize("path", [TESTS / "cases" / "WECC240" / "240busWECC_2018_PSS.raw",
                                  _atom("branch", "mixed_base"), _atom("branch", "switches"), _atom("load", "loads"),
                                  _atom("shunt", "switched_shunts"), _atom("shunt", "plant_and_facts"),
                                  _atom("generator", "generators"), _atom("generator", "renewables"),
                                  _atom("generator", "step_up"), _atom("transformer", "transformers"),
                                  _atom("transformer", "forms_r4b")],
                         ids=lambda path: path.stem)
def test_written_case_reads_back(tmp_path, path):
    _, exported = _round_trip(path, LANDED)
    written = tmp_path / "out.raw"
    Raw34Writer().write(exported, str(written))
    again = Raw34Reader(str(written)).read_all()
    for module in LANDED:
        assert ([vars(record) for record in again.list_by_class(module.NATIVE_CLASS)]
                == [vars(record) for record in exported.list_by_class(module.NATIVE_CLASS)])


def test_to_model_raises_on_equipment_not_yet_exported():
    # E4 exports IEEE14 whole; the two-terminal DC line's converters are E6's (their transformers are left out)
    native = Raw34Reader(str(TESTS / "cases" / "IEEE14" / "IEEE_14_bus.raw")).read_all()
    assert len(RawExporter().to_model(raw_to_cim(native, name="IEEE14")).list_by_class(schema.TransformerRecord)) == 3
    native = Raw34Reader(str(_atom("dc", "two_terminal"))).read_all()
    with pytest.raises(ValueError, match=r"no RAW export yet for \{'CsConverter': 8\}$"):
        RawExporter().to_model(raw_to_cim(native, name="two_terminal_case"))


@pytest.mark.parametrize("module", EXPORT_ORDER, ids=lambda module: module.__name__.rsplit(".", 1)[1])
def test_slots_are_complete(module):
    for native_class, slots in module.SLOTS.items():
        check_slots(slots, native_class)


@pytest.mark.parametrize("exporter, importer", [(case_identification, import_case), (zone, import_zone),
                                                (area_interchange, import_area), (bus, import_bus),
                                                (branch, import_branch), (switch, import_switch),
                                                (multi_section_line, import_multi_section_line), (load, import_load),
                                                (fixed_shunt, import_fixed_shunt),
                                                (switched_shunt, import_switched_shunt),
                                                (generator, import_generator), (transformer, import_transformer),
                                                (impedance_correction, import_impedance_correction)],
                         ids=lambda module: module.__name__.rsplit(".", 1)[1])
def test_untranscribed_on_import_is_unset_on_export(exporter, importer):
    untranscribed = {slot for slot, field in importer.FIELDS.items() if field.kind == "untranscribed"}
    unset = {slot for slot, how in exporter.SLOTS[exporter.NATIVE_CLASS].items() if how.kind == "unset"}
    written = {slot for native_class, slot in NOT_UNSET if native_class is exporter.NATIVE_CLASS}
    assert untranscribed - written <= unset


# E1


class _Device:
    """A hashable stand-in with an mRID, as ``keyed_ids`` reads a device."""

    def __init__(self, mrid: str):
        self.mRID = mrid


def test_e1_keyed_ids():
    device = _Device

    keyed, reversed_pair, unkeyed, long_id = device("ln_1_2_A"), device("ln_2_1_B"), device("x"), device("ln_1_2_ABC")
    ids = keyed_ids([(keyed, "ln_", (1, 2)), (reversed_pair, "ln_", (2, 1)), (unkeyed, "ln_", (2, 1)),
                     (long_id, "ln_", (1, 2))], 2)
    assert ids == {keyed: "A", reversed_pair: "B", long_id: "1", unkeyed: "2"}
    with pytest.raises(ValueError, match="both have buses \\(1, 2\\) and ID 'A'"):
        keyed_ids([(keyed, "ln_", (1, 2)), (device("ln_2_1_A"), "ln_", (2, 1))], 2)


def test_e1_a_section_in_a_substation_is_grouped_in_its_line():
    _, network = _network(_atom("branch", "mixed_base"))
    line = _get(network, cim.Line, "msl_1_4_&1")
    assert sorted(device.mRID for device in line.Equipments) == ["ln_1_2_1", "ln_3_4_1"]
    assert [device.mRID for device in line.AdditionalGroupedEquipment] == ["sc_2_3_1"]  # contained by its substation
    [record] = multi_section_line.export(export_context(network))
    assert (record.i, record.dum1, record.dum2, record.j, record.line_id) == (1, 2, 3, 4, "&1")


def test_e1_a_grouped_section_at_the_end_of_the_path():
    _, network = _network(_atom("branch", "multi_section_line"))
    line, end = _get(network, cim.Line, "msl_1_4_&1"), _get(network, cim.ACLineSegment, "ln_1_2_1")
    line.Equipments.remove(end)
    line.AdditionalGroupedEquipment.append(end)
    [record] = multi_section_line.export(export_context(network))
    assert (record.i, record.dum1, record.dum2, record.j) == (1, 2, 3, 4)


def test_e1_a_line_that_is_not_one_path_writes_no_record():
    _, network = _network(_atom("branch", "multi_section_line"))
    line, parallel = _get(network, cim.Line, "msl_1_4_&1"), _get(network, cim.ACLineSegment, "ln_1_4_2")
    parallel.EquipmentContainer = line
    line.Equipments.append(parallel)  # 1-2-3-4-1: a loop
    assert export_tables(network, (multi_section_line,)).list_by_class(schema.MultiSectionLineRecord) == []


def test_e1_name_longer_than_forty_raises():
    _, network = _network(TESTS / "cases" / "IEEE14" / "IEEE_14_bus.raw")
    _get(network, cim.ACLineSegment, "ln_1_2_1").name = "N" * 41
    with pytest.raises(ValueError, match="longer than RAW's 40 characters"):
        export_tables(network, (branch,))


def test_e1_line_conductance_raises():
    _, network = _network(TESTS / "cases" / "IEEE14" / "IEEE_14_bus.raw")
    line = _get(network, cim.ACLineSegment, "ln_1_2_1")
    line.gch = cim.Conductance(0.001)
    with pytest.raises(ValueError, match="ACLineSegment 'ln_1_2_1': gch is set"):
        export_tables(network, (branch,))


def test_e1_line_shunt_out_of_service_with_its_line_in_raises():
    _, network = _network(_atom("branch", "line_shunts"))
    shunt = next(iter(branch.line_shunts(export_context(network))))
    shunt.inService = False
    with pytest.raises(ValueError, match="a line shunt switches with its line"):
        export_tables(network, (branch,))


def test_e1_switch_on_one_connectivity_node_raises():
    _, network = _network(_atom("substation", "two_bus_node_breaker"))
    device = next(iter(network.graph[cim.Breaker].values()))
    device.Terminals[1].ConnectivityNode = None
    with pytest.raises(ValueError, match="a ConnectivityNode on one terminal only"):
        export_tables(network, (switch,))


def test_e1_ratings_in_mva_and_current_in_one_case_raise():
    _, in_current = _network(_atom("branch", "switches"))
    _, in_mva = _network(_atom("substation", "node_breaker_forms"))
    rated = [device for network in (in_current, in_mva)
             for cim_class in switch.CIM_CLASSES for device in network.graph.get(cim_class, {}).values()
             if any(terminal.OperationalLimitSet for terminal in device.Terminals)]
    with pytest.raises(ValueError, match="ratings in MVA .* and in current"):
        ratings_in_current(rated)


# E2


def _switched_shunts():
    _, network = _network(_atom("shunt", "switched_shunts"))
    return network, {shunt.mRID: shunt for shunt in network.graph[cim.LinearShuntCompensator].values()}


def test_e2_line_shunts_stay_on_their_branches():
    _, network = _network(_atom("branch", "line_shunts"))
    assert network.graph[cim.LinearShuntCompensator]
    assert fixed_shunt.export(export_context(network)) == []


def test_e2_derived_inverses():
    assert mva_from_per_unit(per_unit_from_mva(19.0, 100.0), 100.0) == pytest.approx(19.0)
    target, deadband = reactive_band(0.25, 0.75, -30.0, 50.0)
    vars_per_mvar = 1e6
    assert band_fractions(target / vars_per_mvar, deadband / vars_per_mvar, -30.0, 50.0) == pytest.approx((0.25, 0.75))
    with pytest.raises(ValueError, match="has no width"):
        band_fractions(0.0, 1.0, 5.0, 5.0)


def test_e2_nonlinear_shunt_raises():
    _, network = _network(_atom("shunt", "fixed_shunts"))
    network.add_to_graph(cim.NonlinearShuntCompensator(name="nonlinear"))
    with pytest.raises(ValueError, match="'NonlinearShuntCompensator': 1"):
        RawExporter().to_model(network)


def test_e2_exponent_load_raises():
    _, network = _network(_atom("load", "loads"))
    response = next(iter(network.graph[cim.LoadResponseCharacteristic].values()))
    response.exponentModel, response.pVoltageExponent, response.qVoltageExponent = True, 1.0, 2.0
    with pytest.raises(ValueError, match="an exponent load response"):
        export_tables(network, (load,))


def test_e2_shunt_rated_off_its_bus_voltage_raises():
    _, network = _network(_atom("shunt", "fixed_shunts"))
    next(iter(network.graph[cim.LinearShuntCompensator].values())).nomU = cim.Voltage(240.0, "kV")
    with pytest.raises(ValueError, match="nomU 240.0 kV is not its BaseVoltage"):
        export_tables(network, (fixed_shunt,))


def test_e2_one_control_on_two_buses_raises():
    network, shunts = _switched_shunts()
    shunts["swsh_3_b2"].RegulatingControl = shunts["swsh_1_b1"].RegulatingControl
    with pytest.raises(ValueError, match="controls shunts on buses"):
        export_tables(network, (switched_shunt,))


def test_e2_two_controls_on_one_bus_raise():
    network, shunts = _switched_shunts()
    control = shunts["swsh_3_b2"].RegulatingControl
    second = cim.RegulatingControl(name="second", mode=control.mode, enabled=False, Terminal=control.Terminal)
    network.add_to_graph(second)
    shunts["swsh_3_b2"].RegulatingControl = second
    with pytest.raises(ValueError, match="bus 3: .* both control switched shunts"):
        export_tables(network, (switched_shunt,))


def test_e2_more_blocks_than_the_record_holds_raise(monkeypatch):
    network, _ = _switched_shunts()
    monkeypatch.setattr(switched_shunt, "BLOCKS", 2)
    with pytest.raises(ValueError, match="controls 3 shunts; a switched shunt has 2 blocks"):
        export_tables(network, (switched_shunt,))


def test_e2_block_conductance_raises():
    network, shunts = _switched_shunts()
    shunts["swsh_2_b1"].gPerSection = cim.Conductance(1e-5)
    with pytest.raises(ValueError, match="swsh_2_b1'.*has no G"):
        export_tables(network, (switched_shunt,))


def test_e2_blocks_in_and_out_of_service_raise():
    network, shunts = _switched_shunts()
    shunts["swsh_1_b1"].inService = False
    with pytest.raises(ValueError, match="its blocks are in and out of service"):
        export_tables(network, (switched_shunt,))


# E3


def _generators(stem: str):
    _, network = _network(_atom("generator", stem))
    devices = {device.mRID: device for cim_class in generator.CIM_CLASSES
               for device in network.graph.get(cim_class, {}).values()}
    return network, devices


def test_e3_step_ups_are_the_machines_transformers():
    network, _ = _generators("step_up")
    found = generator.step_ups(export_context(network))
    assert {transformer.mRID: device.mRID for transformer, device in found.items()} == {
        "sm_1_1_xf": "sm_1_1", "sm_2_G1_xf": "sm_2_G1", "sm_4_1_xf": "sm_4_1", "pec_2_PV_xf": "pec_2_PV"}


def test_e3_plant_members_that_disagree_raise():
    network, devices = _generators("generators")
    control = devices["sm_2_G"].RegulatingControl
    second = cim.RegulatingControl(name="second", mode=control.mode, enabled=True, Terminal=control.Terminal,
                                   targetValue=control.targetValue * 1.01)
    network.add_to_graph(second)
    devices["pec_2_PV"].RegulatingControl = second
    with pytest.raises(ValueError, match=r"plant 2: its machines' controls disagree on \(IREG, VS\)"):
        export_tables(network, (generator,))


def test_e3_a_plant_control_off_voltage_raises():
    network, devices = _generators("generators")
    devices["sm_1_1"].RegulatingControl.mode = cim.RegulatingControlModeKind.reactivePower
    with pytest.raises(ValueError, match="mode .*reactivePower.*a plant regulates voltage"):
        export_tables(network, (generator,))


def test_e3_two_machines_behind_one_step_up_raise():
    network, devices = _generators("step_up")
    devices["sm_2_G2"].Terminals[0].TopologicalNode = devices["sm_2_G1"].Terminals[0].TopologicalNode
    with pytest.raises(ValueError, match="a step-up's node holds the machine and one transformer"):
        export_tables(network, (generator,))


def test_e3_a_step_up_out_of_service_raises():
    network, _ = _generators("step_up")
    _get(network, cim.PowerTransformer, "sm_1_1_xf").inService = False
    with pytest.raises(ValueError, match="sm_1_1_xf'.*out of service"):
        export_tables(network, (generator,))


def test_e3_a_step_up_tap_that_moves_raises():
    network, _ = _generators("step_up")
    tap = _get(network, cim.RatioTapChanger, "sm_2_G1_xf_tap1")
    tap.highStep, tap.stepVoltageIncrement = 2, cim.PerCent(1.0)
    with pytest.raises(ValueError, match="steps 1..2.*GTAP is one fixed ratio"):
        export_tables(network, (generator,))


def test_e3_a_step_up_rated_off_its_bus_voltage_raises():
    network, _ = _generators("step_up")
    _get(network, cim.PowerTransformerEnd, "sm_1_1_xf_2").ratedU = cim.Voltage(20.0, "kV")
    with pytest.raises(ValueError, match="sm_1_1_xf_2'.*ratedU 20.0 kV is not its node's BaseVoltage"):
        export_tables(network, (generator,))


def test_e3_reversed_p_limits_come_back_as_written():
    # PB above PT on a unit out of service: the local set has 2 in one case; mapped as written (user 2026-11-09)
    network, devices = _generators("generators")
    unit = devices["sm_1_1"].GeneratingUnit
    unit.minOperatingP, unit.maxOperatingP = cim.ActivePower(1.1, "MW"), cim.ActivePower(0.62, "MW")
    record = next(record for record in export_tables(network, (generator,)).list_by_class(schema.GeneratorRecord)
                  if record.gen_id == "1" and record.bus_number == 1)
    assert (record.min_p_output, record.max_p_output) == pytest.approx((1.1, 0.62))


# E4


def test_e4_step_ups_and_converter_transformers_are_left_out():
    _, network = _network(_atom("generator", "step_up"))
    assert len(network.graph[cim.PowerTransformer]) == 4  # E3's
    assert export_tables(network, (transformer,)).list_by_class(schema.TransformerRecord) == []
    native, network = _network(_atom("dc", "two_terminal"))
    exported = export_tables(network, (transformer,)).list_by_class(schema.TransformerRecord)
    assert len(network.graph[cim.PowerTransformer]) == 11  # 8 of them the DC converters' (E6)
    assert sorted(str(_get_identifier(record)) for record in exported) == sorted(
        str(_get_identifier(record)) for record in native.list_by_class(schema.TransformerRecord))


def test_e4_an_end_on_an_unnumbered_node_raises():
    _, network = _network(TESTS / "cases" / "IEEE14" / "IEEE_14_bus.raw")
    _get(network, cim.PowerTransformerEnd, "xf_4_7_0_1_2").Terminal.TopologicalNode.busNumber = None
    with pytest.raises(ValueError, match="xf_4_7_0_1'.*neither a generator step-up .E3. nor a converter"):
        export_tables(network, (transformer,))


def test_e4_two_windings_out_raise():
    _, network = _network(_atom("transformer", "transformers"))
    for end in ("xf_1_2_3_1_2", "xf_1_2_3_1_3"):
        _get(network, cim.PowerTransformerEnd, end).Terminal.connected = False
    with pytest.raises(ValueError, match="windings \\[2, 3\\] disconnected"):
        export_tables(network, (transformer,))


def test_e4_a_moving_tap_on_winding_2_of_two_raises():
    _, network = _network(_atom("transformer", "forms_r4b"))
    tap = _get(network, cim.RatioTapChanger, "xf_6_7_0_M_tap2")
    tap.highStep, tap.stepVoltageIncrement = 2, cim.PerCent(1.0)
    with pytest.raises(ValueError, match="xf_6_7_0_M_tap2'.*has only a fixed ratio"):
        export_tables(network, (transformer,))


def test_e4_a_shifter_under_a_voltage_control_raises():
    _, network = _network(_atom("transformer", "forms_r4b"))
    _get(network, cim.TapChangerControl, "xf_2_5_0_J_ctrl1").mode = cim.RegulatingControlModeKind.voltage
    with pytest.raises(ValueError, match="xf_2_5_0_J_ptap1'.*a phase tap changer under a voltage control"):
        export_tables(network, (transformer,))


def test_e4_a_three_winding_tabular_raises():
    _, network = _network(_atom("transformer", "forms_r4b"))
    tabular = _get(network, cim.ImpedanceTapChangerTabular, "xf_2_5_0_K_ztab1")
    end = _get(network, cim.PowerTransformerEnd, "xf_1_2_3_G_1")
    end.ImpedanceTapChanger, tabular.TransformerEnd = tabular, end
    with pytest.raises(ValueError, match="xf_2_5_0_K_ztab1'.*on a 3-winding unit"):
        export_tables(network, (transformer,))


def test_e4_a_table_point_scaling_r_and_x_apart_raises():
    _, network = _network(_atom("transformer", "forms_r4b"))
    table = _get(network, cim.ImpedanceTapChangerTable, "ict_1")
    table.ImpedanceTapChangerTablePoint[0].xEnd1 = cim.PerCent(5.0)
    with pytest.raises(ValueError, match="ict_1'.*PSS/E's F scales end 1's r and x alike"):
        export_tables(network, (impedance_correction,))


def test_e4_impedance_off_the_bus_base_moves_by_the_voltage():
    # L: NOMV1 240 kV on the 230 kV bus, CZ 1. The end holds ohms on 240 kV; RAW's X is on 230 kV
    native, network = _network(_atom("transformer", "forms_r4b"))
    [original] = [record for record in native.list_by_class(schema.TransformerRecord) if record.circuit == "L"]
    end = _get(network, cim.PowerTransformerEnd, "xf_2_6_0_L_1")
    assert end.x.to("ohm") == pytest.approx(original.x1_2 * 230.0 ** 2 / 100.0)
    [record] = [record for record in export_tables(network, (transformer,)).list_by_class(schema.TransformerRecord)
                if record.circuit == "L"]
    assert (record.nomv1, record.x1_2) == (pytest.approx(240.0), pytest.approx(original.x1_2))


def test_e4_a_winding_at_its_rating_off_the_bus_base():
    # the import writes no tap at ratio NOMV, so a winding without one is at its ratedU: WINDV = ratedU / BASKV
    _, network = _network(TESTS / "cases" / "IEEE14" / "IEEE_14_bus.raw")
    _get(network, cim.PowerTransformerEnd, "xf_4_7_0_1_2").ratedU = cim.Voltage(130.0, "kV")
    [record] = [record for record in export_tables(network, (transformer,)).list_by_class(schema.TransformerRecord)
                if (record.i, record.j) == (4, 7)]
    assert (record.nomv2, record.windv2) == (pytest.approx(130.0), pytest.approx(130.0 / 138.0))

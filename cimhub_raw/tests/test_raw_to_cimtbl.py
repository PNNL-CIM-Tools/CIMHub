"""R0-R6: the master, zone, area interchange, bus, substation, branch, switch, multi-section line, load, fixed
shunt, switched shunt, generator, transformer and equipment terminal documents, tie flows and inter-area transfers,
and their bind under cim18v17 (BusBranchModel).

Goldens: ``tests/goldens/IEEE14/``, and IEEE118's substation and equipment terminal documents in
``tests/goldens/IEEE118/`` (``CIMHUB_UPDATE_GOLDENS=1`` rewrites them; review the diff).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_raw.importer.cimtbl import (
    area_interchange,
    branch,
    bus,
    case_identification,
    equipment_terminal,
    facts_device,
    fixed_shunt,
    generator,
    impedance_correction,
    interarea_transfer,
    load,
    multi_section_line,
    owner,
    substation,
    switch,
    switched_shunt,
    transformer,
    two_terminal_dc,
    vsc_dc,
    zone,
)
from cimhub_raw.importer.cimtbl.derived import (
    block_sections,
    cim_angle,
    converter_tap,
    converter_transformer_ohms,
    generation_p_q,
    impedance_deviation_percent,
    is_angle_table,
    ka_from_rating,
    kv_from_per_unit,
    load_p_q,
    magnetizing_siemens,
    net_import,
    ohms_from_per_unit,
    per_unit_from_mva,
    phase_tap,
    ratio_tap,
    siemens_from_per_unit,
    transformer_ohms,
    vars_from_mvar,
    volts_from_per_unit,
    watts_from_mw,
    winding_unit_kv,
    zip_mix,
)
from cimhub_raw.importer.raw_to_cimtbl import RawImporter, raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader

TESTS = Path(__file__).parent
IEEE14 = TESTS / "cases" / "IEEE14" / "IEEE_14_bus.raw"
WECC240 = TESTS / "cases" / "WECC240" / "240busWECC_2018_PSS.raw"
IEEE118 = TESTS / "cases" / "IEEE118" / "IEEE118_all_hydro_25_clean_4_subs.raw"
NODE_BREAKER = TESTS / "atoms" / "substation" / "two_bus_node_breaker.raw"
FORMS_ATOM = TESTS / "atoms" / "substation" / "node_breaker_forms.raw"
GOLDENS = TESTS / "goldens" / "IEEE14"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _objects(network, class_name: str) -> dict:
    """mRID (or identifier) -> object, for one CIM class of a bound network."""
    for cls, objects in network.graph.items():
        if cls.__name__ == class_name:
            return {getattr(obj, "mRID", None) or obj.identifier: obj for obj in objects.values()}
    return {}


@pytest.fixture(scope="module")
def ieee14_documents():
    return RawImporter("IEEE14").to_cimtbl(Raw34Reader(IEEE14).read_all())


@pytest.mark.parametrize("module", [case_identification, zone, area_interchange, bus, owner, branch, switch,
                                    multi_section_line, load, fixed_shunt, switched_shunt, generator, transformer,
                                    interarea_transfer, substation, equipment_terminal, impedance_correction,
                                    facts_device, vsc_dc, two_terminal_dc],
                         ids=lambda module: module.__name__.rsplit(".", 1)[1])
def test_classification_is_complete(module):
    check_fields(module.FIELDS, module.NATIVE_CLASS)


@pytest.mark.parametrize(("fields", "native_class"), [
    (substation.NODE_FIELDS, substation.NODE_CLASS), (substation.DEVICE_FIELDS, substation.DEVICE_CLASS),
    (impedance_correction.POINT_FIELDS, impedance_correction.POINT_CLASS),
], ids=["substation_node", "substation_switching_device", "impedance_correction_point"])
def test_substation_record_classification_is_complete(fields, native_class):
    check_fields(fields, native_class)


def test_kv_from_per_unit():
    assert kv_from_per_unit(1.1, 138.0) == pytest.approx(151.8)
    assert kv_from_per_unit(0.0, 345.0) == 0.0


def test_ka_from_rating():
    """The spec's MVA = sqrt(3) x E x I: 100 MVA at 100 kV is 0.57735 kA."""
    assert ka_from_rating(100.0, 100.0) == pytest.approx(0.577350269)


# -- goldens -----------------------------------------------------------------------------------------


def test_master_matches_golden(ieee14_documents):
    assert_matches_golden(ieee14_documents.master, GOLDENS / "IEEE14.cimtbl")


@pytest.mark.parametrize("part", ["zone", "area_interchange", "bus", "branch", "load", "fixed_shunt", "generator",
                                  "transformer"])
def test_part_matches_golden(ieee14_documents, part):
    document = next(doc for doc in ieee14_documents.parts if doc.name == part)
    assert_matches_golden(document, GOLDENS / f"{part}.cimtbl")


def test_import_order_is_the_mapping_order(ieee14_documents):
    assert [part.name for part in ieee14_documents.parts] == ["zone", "area_interchange", "bus", "branch", "load",
                                                              "fixed_shunt", "generator", "transformer"]


# -- the bound networks ------------------------------------------------------------------------------


@pytest.mark.parametrize(("case", "name", "substations", "buses"),
                         [(IEEE14, "IEEE14", 11, 14), (WECC240, "WECC240", 134, 243),
                          (NODE_BREAKER, "node_breaker", 2, 2), (IEEE118, "IEEE118", 108, 118),
                          (FORMS_ATOM, "forms", 3, 5)],
                         ids=["IEEE14", "WECC240", "node_breaker", "IEEE118", "forms"])
def test_binds(case, name, substations, buses):
    network = raw_to_cim(Raw34Reader(case).read_all(), name=name)
    assert len(_objects(network, "Substation")) == substations
    assert len(_objects(network, "TopologicalNode")) == buses
    assert len([key for key in _objects(network, "BusbarSection") if not key.startswith("bb_s")]) == buses
    assert len(_objects(network, "VoltageLimit")) == 4 * buses
    assert len(_objects(network, "SvVoltage")) == buses


@pytest.fixture(scope="module")
def wecc240():
    with cim_scope():
        native = Raw34Reader(WECC240).read_all()
        return native, raw_to_cim(native, name="WECC240")


def test_values_in_si(wecc240):
    """Every bus's limits and solved voltage in SI equal pu x BASKV; the node keeps the bus number."""
    native, network = wecc240
    nodes = _objects(network, "TopologicalNode")
    limits = _objects(network, "VoltageLimit")
    voltages = {sv.TopologicalNode.mRID: sv for sv in _objects(network, "SvVoltage").values()}
    for record in native.list_by_class(schema.BusRecord):
        number, base_v = str(record.bus_number), record.base_voltage * 1000
        assert nodes[number].busNumber == record.bus_number
        assert nodes[number].BaseVoltage.nominalVoltage.to("V") == pytest.approx(base_v)
        assert limits[f"bb_{number}_nvhi"].normalValue.to("V") == pytest.approx(
            record.normal_voltage_magnitude_high_limit * base_v)
        assert limits[f"bb_{number}_evlo"].normalValue.to("V") == pytest.approx(
            record.emergency_voltage_magnitude_low_limit * base_v)
        assert voltages[number].v.to("V") == pytest.approx(record.voltage_magnitude * base_v)
        assert float(voltages[number].angle) == pytest.approx(record.voltage_angle)


def test_busbar_terminal_holds_the_limits(wecc240):
    _, network = wecc240
    busbar = _objects(network, "BusbarSection")["bb_1001"]
    terminal = busbar.Terminals[0]
    assert terminal.mRID == "bb_1001_T1"
    assert terminal.TopologicalNode.mRID == "1001"
    assert _objects(network, "OperationalLimitSet")["bb_1001_limits"].Terminal is terminal
    assert busbar.BaseVoltage is terminal.TopologicalNode.BaseVoltage


def test_substations_split_at_zones(wecc240):
    """Bus 1001 (zone 10) joins buses of zone 3 through a transformer; the substation stops at the zone."""
    native, network = wecc240
    zones = {record.bus_number: record.zone for record in native.list_by_class(schema.BusRecord)}
    for node in _objects(network, "TopologicalNode").values():
        substation = node.ConnectivityNodeContainer
        assert substation.Region.mRID == f"srgn_{zones[node.busNumber]}"


def test_a_zone_no_record_names_is_synthesized():
    document = zone.map_zone(Raw34Reader(NODE_BREAKER).read_all(), "rgn_x")
    assert [table.comment for table in document.statements] == [
        "synthesized: zones that buses name but the Zone data does not"]


def test_the_master_lists_what_is_not_mapped(ieee14_documents):
    assert "not mapped" not in ieee14_documents.master.comment  # every IEEE14 table maps since R4
    master = RawImporter("node_breaker").to_cimtbl(Raw34Reader(NODE_BREAKER).read_all()).master
    assert "not mapped" not in master.comment  # the SUBSTATION section maps since R6


# -- R1: branches, switches, multi-section lines ----------------------------------------------------------


BRANCH_ATOMS = TESTS / "atoms" / "branch"


def _network(path, name="atom"):
    return raw_to_cim(Raw34Reader(path).read_all(), name=name)


def test_wecc240_branches_in_ohms(wecc240):
    """Every branch's r, x and bch in SI equal the pu value on BASKV and SBASE; X < 0 is a series capacitor."""
    native, network = wecc240
    base_kv = {record.bus_number: record.base_voltage for record in native.list_by_class(schema.BusRecord)}
    lines, capacitors = _objects(network, "ACLineSegment"), _objects(network, "SeriesCompensator")
    for record in native.list_by_class(schema.BranchRecord):
        z_base = base_kv[record.from_bus_number] ** 2 / 100.0
        if record.x < 0:
            equipment = capacitors[f"sc_{record.ID}"]
            assert equipment.compensatorType.name == "capacitor"
        else:
            equipment = lines[f"ln_{record.ID}"]
            assert equipment.bch.to("S") == pytest.approx(record.b / z_base)
        assert equipment.r.to("ohm") == pytest.approx(record.r * z_base)
        assert equipment.x.to("ohm") == pytest.approx(record.x * z_base)
        assert equipment.inService is (record.status == 1)
    assert (len(lines), len(capacitors)) == (320, 9)


def test_wecc240_ratings_on_terminal_1(wecc240):
    native, network = wecc240
    limits = _objects(network, "ApparentPowerLimit")
    assert len([mrid for mrid in limits if not mrid.startswith("xf_")]) == 281  # and 42 transformers' (R4)
    limit = limits["ln_2000_2202_1_rate2"]
    assert limit.normalValue.to("MVA") == pytest.approx(986.0)
    assert limit.OperationalLimitType.mRID == "olt_rate2"
    terminal = limit.OperationalLimitSet.Terminal
    assert (terminal.mRID, terminal.sequenceNumber, terminal.TopologicalNode.mRID) == ("ln_2000_2202_1_T1", 1, "2000")


def test_a_branch_inside_a_substation_is_contained():
    """IEEE14 7-9 joins two buses that transformers merge into sub_4; 1-2 joins two substations."""
    lines = _objects(_network(IEEE14, "IEEE14"), "ACLineSegment")
    assert lines["ln_7_9_1"].EquipmentContainer.mRID == "sub_4"
    assert lines["ln_1_2_1"].EquipmentContainer is None


def test_line_shunts_ratings_and_length():
    network = _network(BRANCH_ATOMS / "line_shunts.raw")
    line = _objects(network, "ACLineSegment")["ln_1_2_1"]
    assert line.length.to("km") == pytest.approx(12.5)
    shunts = _objects(network, "LinearShuntCompensator")
    z_base = 115.0 ** 2 / 100.0
    assert shunts["cap_1_2_1_i"].bPerSection.to("S") == pytest.approx(-0.05 / z_base)
    assert shunts["cap_1_2_1_i"].gPerSection.to("S") == pytest.approx(0.01 / z_base)
    assert shunts["cap_1_2_1_j"].bPerSection.to("S") == pytest.approx(0.02 / z_base)
    assert shunts["cap_1_2_1_j"].Terminals[0].TopologicalNode.mRID == "2"
    assert sorted(_objects(network, "ApparentPowerLimit")) == ["ln_1_2_1_rate1", "ln_1_2_1_rate2"]


def test_switches_by_stype_with_current_ratings():
    network = _network(BRANCH_ATOMS / "switches.raw")
    connector = _objects(network, "Switch")["sw_101_102_1"]
    breaker = _objects(network, "Breaker")["sw_102_103_1"]
    disconnector = _objects(network, "Disconnector")["sw_103_104_1"]
    assert (connector.open, connector.normalOpen) == (False, False)
    assert (breaker.open, breaker.normalOpen) == (True, False)
    assert (disconnector.open, disconnector.normalOpen) == (False, True)
    assert {connector.EquipmentContainer.mRID, breaker.EquipmentContainer.mRID} == {"sub_101"}
    limit = _objects(network, "CurrentLimit")["sw_101_102_1_rate1"]
    assert limit.normalValue.to("kA") == pytest.approx(ka_from_rating(200.0, 138.0))


def test_multi_section_line_holds_its_sections():
    network = _network(BRANCH_ATOMS / "multi_section_line.raw")
    line = _objects(network, "Line")["msl_1_4_&1"]
    assert sorted(equipment.mRID for equipment in line.Equipments) == ["ln_1_2_1", "ln_2_3_1", "ln_4_3_1"]
    assert _objects(network, "ACLineSegment")["ln_1_4_2"].EquipmentContainer is None


def test_a_multi_section_line_with_a_missing_section_raises():
    native = Raw34Reader(BRANCH_ATOMS / "multi_section_line.raw").read_all()
    del native.graph[schema.BranchRecord]["2_3_1"]
    with pytest.raises(ValueError, match="dummy bus 2 has 1 branches"):
        RawImporter("atom").to_cimtbl(native)


def test_an_unknown_switch_type_raises():
    native = Raw34Reader(BRANCH_ATOMS / "switches.raw").read_all()
    first = native.graph[schema.SwitchRecord]["101_102_1"]
    native.graph[schema.SwitchRecord]["101_102_1"] = dataclasses.replace(first, stype=4)
    native.graph[schema.SwitchRecord]["101_102_1"].ID = "101_102_1"
    with pytest.raises(ValueError, match="stype=4 has no mapping"):
        RawImporter("atom").to_cimtbl(native)


def test_a_series_capacitor_with_charging_raises():
    native = Raw34Reader(WECC240).read_all()
    first = native.graph[schema.BranchRecord]["2404_3893_1"]
    native.graph[schema.BranchRecord]["2404_3893_1"] = dataclasses.replace(first, b=0.1)
    native.graph[schema.BranchRecord]["2404_3893_1"].ID = "2404_3893_1"
    with pytest.raises(ValueError, match="SeriesCompensator has no bch"):
        RawImporter("WECC240").to_cimtbl(native)


# -- R2: loads, fixed shunts, switched shunts -------------------------------------------------------------


LOAD_ATOMS = TESTS / "atoms" / "load"
SHUNT_ATOMS = TESTS / "atoms" / "shunt"


def _replace_record(native, cls, key, **changes):
    """Put a changed copy of one native record back under its key, with its composite ID."""
    record = dataclasses.replace(native.graph[cls][key], **changes)
    record.ID = key
    native.graph[cls][key] = record


def _load(**powers):
    values = dict(constant_real_power=0.0, constant_imag_power=0.0, constant_current_real_power=0.0,
                  constant_current_imag_power=0.0, constant_admittance_real_power=0.0,
                  constant_admittance_imag_power=0.0)
    record = schema.LoadRecord(bus_number=1, **{**values, **powers})
    record.ID = "1_1"
    return record


def test_load_p_q_and_zip_mix():
    """YQ < 0 is inductive, so q = QL + IQ - YQ; the fractions of each side sum to 1."""
    record = _load(constant_real_power=5.0, constant_imag_power=1.0, constant_current_real_power=3.0,
                   constant_current_imag_power=1.0, constant_admittance_real_power=2.0,
                   constant_admittance_imag_power=-2.0)
    assert load_p_q(record) == (10.0, 4.0)
    assert zip_mix(record) == (0.5, 0.3, 0.2, 0.25, 0.25, 0.5)
    assert zip_mix(_load(constant_real_power=4.0)) == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)  # q all 0: constant power


def test_zip_mix_of_cancelling_components_raises():
    with pytest.raises(ValueError, match="q components .* cancel to 0"):
        zip_mix(_load(constant_imag_power=2.0, constant_admittance_imag_power=2.0))


def test_per_unit_and_volts():
    assert per_unit_from_mva(19.0, 100.0) == pytest.approx(0.19)
    assert volts_from_per_unit(1.02, 345.0) == pytest.approx(351900.0)


@pytest.mark.parametrize(("binit", "blocks", "sections"), [
    (600.0, [(5, 200.0)], [3.0]),
    (13.0, [(10, 1.0), (5, 1.5)], [10.0, 2.0]),                       # 10 x 1 Mvar, then 2 of the 1.5 Mvar steps
    (-15.0, [(2, -15.0), (3, 10.0), (2, 25.0)], [1.0, 0.0, 0.0]),     # a reactor block first
    (40.0, [(2, -15.0), (3, 10.0), (2, 25.0)], [0.0, 3.0, 0.4]),      # capacitors in input order
    (31.25, [(4, 12.5)], [2.5]),                                      # continuous: a fraction of a step
    (0.0, [(5, 200.0)], [0.0]),
])
def test_block_sections(binit, blocks, sections):
    assert block_sections(binit, blocks, "x") == pytest.approx(sections)


def test_block_sections_beyond_the_blocks_raises():
    with pytest.raises(ValueError, match="BINIT=1001.0 is beyond its blocks"):
        block_sections(1001.0, [(5, 200.0)], "x")


def test_wecc240_loads(wecc240):
    """p and q in SI equal the RAW sums; each load reaches its own area's ControlArea through its group."""
    native, network = wecc240
    loads = _objects(network, "ConformLoad")
    for record in native.list_by_class(schema.LoadRecord):
        load_object = loads[f"ld_{record.ID}"]
        assert load_object.p.to("MW") == pytest.approx(record.constant_current_real_power)
        assert load_object.q.to("MVAr") == pytest.approx(-record.constant_admittance_imag_power)
        sub_area = load_object.LoadGroup.SubLoadArea
        assert sub_area.mRID == f"sla_{record.area}_{record.zone}"
        assert sub_area.LoadArea.ControlArea.mRID == f"ca_{record.area}"
        assert load_object.LoadResponse.pConstantCurrent == 1.0
    assert (len(loads), len(_objects(network, "LoadArea")), len(_objects(network, "SubLoadArea"))) == (139, 4, 14)
    assert sorted(_objects(network, "LoadResponseCharacteristic")) == ["zip_0_1_0_0_0_1", "zip_0_1_0_1_0_0"]


def test_wecc240_switched_shunts(wecc240):
    """One block each: b in S = B1 / BASKV^2, sections = BINIT / B1, a voltage control on its own busbar."""
    native, network = wecc240
    base_kv = {record.bus_number: record.base_voltage for record in native.list_by_class(schema.BusRecord)}
    shunts = _objects(network, "LinearShuntCompensator")
    for record in native.list_by_class(schema.SwitchedShuntRecord):
        shunt = shunts[f"swsh_{record.ID}_b1"]
        kv = base_kv[record.bus_number]
        assert shunt.bPerSection.to("S") == pytest.approx(record.b1 / kv ** 2)
        assert (shunt.maximumSections, shunt.sections) == (record.n1, pytest.approx(record.binit / record.b1))
        control = shunt.RegulatingControl
        assert control.Terminal.mRID == f"bb_{record.swreg}_T1"
        assert (control.mode.name, control.discrete, control.enabled) == ("voltage", True, True)
        assert control.targetValue == pytest.approx(kv * 1000.0)
    assert len([control for control in _objects(network, "RegulatingControl") if control.startswith("cc_")]) == 7


def test_ieee14_fixed_shunt():
    shunt = _objects(_network(IEEE14, "IEEE14"), "LinearShuntCompensator")["cap_9_1"]
    assert shunt.bPerSection.to("S") == pytest.approx(19.0 / 138.0 ** 2)
    assert (shunt.sections, shunt.inService, shunt.EquipmentContainer.mRID) == (1, True, "sub_4")


def test_load_atom():
    network = _network(LOAD_ATOMS / "loads.raw")
    loads = _objects(network, "ConformLoad")
    fixed = _objects(network, "NonConformLoad")["ld_2_1"]
    assert (fixed.LoadGroup.mRID, fixed.inService, fixed.p.to("MW")) == ("nclg_1_1", False, pytest.approx(4.0))
    mixed = loads["ld_1_2"].LoadResponse
    assert (mixed.pConstantPower, mixed.pConstantCurrent, mixed.pConstantImpedance) == (0.5, 0.3, 0.2)
    assert (mixed.qConstantPower, mixed.qConstantCurrent, mixed.qConstantImpedance) == (0.25, 0.25, 0.5)
    elsewhere = loads["ld_2_A"]  # on bus 2 (area 1, zone 1), assigned to area 2, zone 2
    assert elsewhere.LoadGroup.SubLoadArea.LoadArea.ControlArea.mRID == "ca_2"
    assert elsewhere.LoadGroup.mRID == "clg_2_2"
    assert loads["ld_3_1"].LoadGroup.mRID == "clg_2_2"  # blank AREA and ZONE: bus 3's


def test_load_atom_comments():
    document = next(part for part in RawImporter("atom").to_cimtbl(
        Raw34Reader(LOAD_ATOMS / "loads.raw").read_all()).parts if part.name == "load")
    rows = {row.cells[0]: row for statement in document.statements for row in statement.rows}
    assert rows["ld_2_A"].comment == "untranscribed: zone=2 (bus 2 is in zone 1)"
    assert rows["ld_3_1"].comment.startswith("defaulted: area=2, zone=2")


def test_fixed_shunt_atom():
    shunts = _objects(_network(SHUNT_ATOMS / "fixed_shunts.raw"), "LinearShuntCompensator")
    z_base = 115.0 ** 2 / 100.0
    assert shunts["cap_1_1"].gPerSection.to("S") == pytest.approx(0.015 / z_base)
    assert shunts["cap_1_1"].bPerSection.to("S") == pytest.approx(0.2 / z_base)
    assert (shunts["cap_1_2"].bPerSection.to("S") < 0, shunts["cap_1_2"].inService) == (True, False)


def test_switched_shunt_atom():
    network = _network(SHUNT_ATOMS / "switched_shunts.raw")
    shunts = _objects(network, "LinearShuntCompensator")
    controls = _objects(network, "RegulatingControl")
    assert [shunts[f"swsh_1_b{block}"].sections for block in (1, 2, 3)] == [1.0, 0.0, 0.0]
    assert {shunts[f"swsh_1_b{block}"].RegulatingControl.mRID for block in (1, 2, 3)} == {"cc_1"}
    assert controls["cc_1"].Terminal.mRID == "bb_4_T1"  # remote: SWREG 4, 115 kV
    assert controls["cc_1"].targetValue == pytest.approx(1.01 * 115000.0)
    assert controls["cc_1"].targetDeadband == pytest.approx(0.06 * 115000.0)
    assert (controls["cc_2"].discrete, shunts["swsh_2_b1"].sections) == (False, 2.5)  # continuous
    assert controls["cc_3"].enabled is False  # locked
    assert [shunts[f"swsh_3_b{block}"].controlEnabled for block in (1, 2)] == [False, False]
    assert [shunts[f"swsh_3_b{block}"].sections for block in (1, 2)] == [10.0, 2.0]


@pytest.mark.parametrize(("changes", "error", "message"), [
    ({"modsw": 3}, NotImplementedError, "MODSW 3 .plant reactive power"),
    ({"modsw": 6}, NotImplementedError, "MODSW 6 .FACTS"),
    ({"nreg": 2}, ValueError, "node 2 of bus 4, which has no SUBSTATION block"),
    ({"n2": None, "b2": None}, ValueError, "a block after the first zero"),
    ({"binit": 1000.0}, ValueError, "BINIT=1000.0 is beyond its blocks"),
])
def test_a_switched_shunt_outside_r2_raises(changes, error, message):
    native = Raw34Reader(SHUNT_ATOMS / "switched_shunts.raw").read_all()
    _replace_record(native, schema.SwitchedShuntRecord, "1", **changes)
    with pytest.raises(error, match=message):
        RawImporter("atom").to_cimtbl(native)


def test_a_load_in_an_area_without_a_record_raises():
    native = Raw34Reader(LOAD_ATOMS / "loads.raw").read_all()
    _replace_record(native, schema.LoadRecord, "1_1", area=7)
    with pytest.raises(ValueError, match="AREA 7 has no area-interchange record"):
        RawImporter("atom").to_cimtbl(native)


# -- fail fast ---------------------------------------------------------------------------------------


def test_a_change_case_raises():
    native = Raw34Reader(IEEE14).read_all()
    case = native.first(schema.CaseIdentificationRecord)
    native.graph[schema.CaseIdentificationRecord] = {"CASE": dataclasses.replace(case, new_case_flag=1)}
    with pytest.raises(ValueError, match="IC=1: a change case"):
        RawImporter("IEEE14").to_cimtbl(native)


def test_a_bus_without_base_voltage_raises():
    native = Raw34Reader(IEEE14).read_all()
    first = native.graph[schema.BusRecord]["1"]
    native.graph[schema.BusRecord]["1"] = dataclasses.replace(first, base_voltage=0.0)
    with pytest.raises(ValueError, match="bus 1: BASKV=0.0 is no base voltage"):
        RawImporter("IEEE14").to_cimtbl(native)


# -- R3: generators ----------------------------------------------------------------------------------

GENERATOR_ATOMS = TESTS / "atoms" / "generator"


def test_ohms_from_per_unit():
    """kV^2 / MVA is ohm: 0.01 pu on 13.8 kV and 100 MVA is 0.019044 ohm."""
    assert ohms_from_per_unit(0.01, 13.8, 100.0) == pytest.approx(0.019044)


def test_generation_p_q_keeps_zero_positive():
    record = schema.GeneratorRecord(bus_number=1, p_output=0.0, q_output=-3.5)
    p, q = generation_p_q(record)
    assert (str(p), q) == ("0.0", 3.5)


def test_wecc240_generators(wecc240):
    """p = -PG and the limits in SI; WMOD picks the class; one control per plant on IREG's busbar; each unit in its
    bus's ControlArea."""
    native, network = wecc240
    buses = {record.bus_number: record for record in native.list_by_class(schema.BusRecord)}
    machines, converters = _objects(network, "SynchronousMachine"), _objects(network, "PowerElectronicsConnection")
    for record in native.list_by_class(schema.GeneratorRecord):
        if record.wmod == 1:
            equipment = converters[f"pec_{record.ID}"]
            unit = equipment.PowerElectronicsUnit[0]
            assert unit.maxP.to("MW") == pytest.approx(record.max_p_output)
            membership = _objects(network, "ControlAreaPowerElectronicsUnit")[f"capu_{record.ID}"]
            assert membership.PowerElectronicsUnit is unit
        else:
            equipment = machines[f"sm_{record.ID}"]
            assert equipment.GeneratingUnit.minOperatingP.to("MW") == pytest.approx(record.min_p_output)
            assert float(equipment.qPercent) == record.rmpct
            membership = equipment.GeneratingUnit.ControlAreaGeneratingUnit[0]
        assert membership.ControlArea.mRID == f"ca_{buses[record.bus_number].area}"
        assert equipment.p.to("MW") == pytest.approx(-record.p_output)
        assert equipment.q.to("MVAr") == pytest.approx(-record.q_output)
        assert (equipment.maxQ.to("MVAr"), equipment.ratedS.to("MVA")) == (pytest.approx(record.max_q_output),
                                                                           pytest.approx(record.rated_mva))
        assert equipment.inService is (record.status == 1)
        control = equipment.RegulatingControl
        regulated = buses[record.regulated_bus_number]
        assert (control.mRID, control.Terminal.mRID) == (f"gc_{record.bus_number}", f"bb_{regulated.bus_number}_T1")
        assert control.targetValue == pytest.approx(record.regulated_voltage_setpoint * regulated.base_voltage * 1000)
    assert (len(machines), len(converters)) == (109, 37)
    plants = {control for control in _objects(network, "RegulatingControl") if control.startswith("gc_")}
    assert len(plants) == 56
    swing = [machine.mRID for machine in machines.values() if machine.referencePriority == 1]
    assert sorted(swing) == ["sm_3933_CG", "sm_3933_NB", "sm_3933_ND", "sm_3933_NG", "sm_3933_NH"]


def test_ieee14_swing_machine():
    machines = _objects(_network(IEEE14, "IEEE14"), "SynchronousMachine")
    assert {mrid: machine.referencePriority for mrid, machine in machines.items()} == {
        "sm_1_1": 1, "sm_2_1": None, "sm_3_1": None, "sm_6_1": None, "sm_8_1": None}


def test_generator_atom():
    network = _network(GENERATOR_ATOMS / "generators.raw")
    machines = _objects(network, "SynchronousMachine")
    controls = _objects(network, "RegulatingControl")
    swing = machines["sm_1_1"]
    assert (swing.referencePriority, swing.RegulatingControl.Terminal.mRID) == (1, "bb_1_T1")
    assert swing.r.to("ohm") == pytest.approx(0.003 * 230.0 ** 2 / 200.0)
    plant = controls["gc_2"]  # a machine and a converter on bus 2, regulating remote bus 3 (230 kV)
    converter = _objects(network, "PowerElectronicsConnection")["pec_2_PV"]
    assert machines["sm_2_G"].RegulatingControl is plant and converter.RegulatingControl is plant
    assert (plant.Terminal.mRID, plant.targetValue) == ("bb_3_T1", pytest.approx(1.01 * 230000.0))
    assert (converter.inService, converter.PowerElectronicsUnit[0].mRID) == (False, "pecu_2_PV")
    assert machines["sm_2_G"].GeneratingUnit.minOperatingP.to("MW") == pytest.approx(-40.0)  # pumping
    assert (controls["gc_4"].enabled, machines["sm_4_1"].controlEnabled) == (False, False)  # an IDE 1 bus
    blank = machines["sm_5_1"]  # every field defaulted
    assert (blank.ratedS.to("MVA"), blank.maxQ.to("MVAr"), blank.p.to("MW")) == (pytest.approx(100.0),
                                                                                 pytest.approx(9999.0), 0.0)


def test_generator_atom_comments():
    document = next(part for part in RawImporter("atom").to_cimtbl(
        Raw34Reader(GENERATOR_ATOMS / "generators.raw").read_all()).parts if part.name == "generator")
    rows = {row.cells[0]: row for statement in document.statements for row in statement.rows}
    assert rows["sm_5_1"].comment.startswith("defaulted: gen_id=1, p_output=0.0")
    assert "rated_mva=100.0" in rows["sm_5_1"].comment


@pytest.mark.parametrize(("key", "changes", "error", "message"), [
    ("2_G", {"wmod": 2}, NotImplementedError, "WMOD 2 .renewable, Q limits from WPF"),
    ("2_G", {"wmod": 4}, NotImplementedError, "WMOD 4 .infeed"),
    ("2_G", {"xt": 0.1}, NotImplementedError, "an implicit step-up transformer"),
    ("2_G", {"nreg": 2}, ValueError, r"disagree on \(IREG, NREG, VS, RMPCT\)"),  # NREG is a plant quantity
    ("2_PV", {"regulated_voltage_setpoint": 1.0}, ValueError, "plant 2: generators 2_G and 2_PV disagree"),
    ("2_PV", {"rmpct": 50.0}, ValueError, "plant 2: generators 2_G and 2_PV disagree"),
    ("1_1", {"regulated_bus_number": 3}, ValueError, "plant 1: a swing bus regulates remote bus 3"),
    ("2_G", {"regulated_bus_number": 99}, ValueError, "plant 2: IREG 99 is no bus"),
    ("1_1", {"wmod": 1}, ValueError, "plant 1: a swing bus with no SynchronousMachine"),
])
def test_a_generator_outside_r3_raises(key, changes, error, message):
    native = Raw34Reader(GENERATOR_ATOMS / "generators.raw").read_all()
    if key == "2_G" and "regulated_bus_number" in changes:  # a plant's records agree, so change both
        _replace_record(native, schema.GeneratorRecord, "2_PV", **changes)
    _replace_record(native, schema.GeneratorRecord, key, **changes)
    with pytest.raises(error, match=message):
        RawImporter("atom").to_cimtbl(native)


# -- R4: transformers --------------------------------------------------------------------------------------

TRANSFORMER_ATOMS = TESTS / "atoms" / "transformer"


def test_transformer_ohms_by_impedance_code():
    """CZ 1 on SBASE and BASKV; CZ 2 on the pair's SBASE and NOMV; CZ 3 a load loss in W and |Z|."""
    bases = dict(base_kv=345.0, nominal_kv=340.0, pair_mva=200.0, system_mva=100.0, record_id="x")
    assert transformer_ohms(0.001, 0.05, 1, **bases) == (pytest.approx(1.19025), pytest.approx(59.5125))
    assert transformer_ohms(0.002, 0.08, 2, **bases) == (pytest.approx(1.156), pytest.approx(46.24))
    r, x = transformer_ohms(400000.0, 0.1, 3, **bases)  # 0.4 MW on 200 MVA is r = 0.002 pu
    assert (r, x) == (pytest.approx(1.156), pytest.approx(0.1 * 0.99980 * 578.0, rel=1e-5))
    with pytest.raises(ValueError, match="CZ 3 .Z. = 0.001 pu is less than its load-loss r"):
        transformer_ohms(400000.0, 0.001, 3, **bases)


def test_magnetizing_siemens_by_admittance_code():
    bases = dict(base_kv=230.0, nominal_kv=220.0, pair_mva=50.0, system_mva=100.0, record_id="x")
    assert magnetizing_siemens(0.001, -0.003, 1, **bases) == (pytest.approx(0.1 / 230.0 ** 2),
                                                              pytest.approx(-0.3 / 230.0 ** 2))
    g, b = magnetizing_siemens(30000.0, 0.005, 2, **bases)  # 0.03 MW on 50 MVA is g = 0.0006 pu
    assert (g, b) == (pytest.approx(0.0006 * 50.0 / 220.0 ** 2), pytest.approx(-0.0049639 * 50.0 / 220.0 ** 2,
                                                                                rel=1e-5))
    with pytest.raises(ValueError, match="CM 2 exciting current 0.0001 pu is less than"):
        magnetizing_siemens(30000.0, 0.0001, 2, **bases)
    assert (siemens_from_per_unit(1.0, 10.0, 100.0), vars_from_mvar(-2.5)) == (1.0, -2500000.0)


def test_winding_unit_kv():
    assert [winding_unit_kv(cw, 345.0, 340.0, "x") for cw in (1, 2, 3)] == [345.0, 1.0, 340.0]


@pytest.mark.parametrize(("windv", "rma", "rmi", "ntp", "units", "expected"), [
    (1.0, 1.1, 0.9, 989, (500.0, 500.0), (495, 1.0, 0.2 / 988 * 100, 495.0)),  # WECC240: ratio 1 on a step
    (1.00345, 1.1, 0.9, 30, (345.0, 345.0), (15, 0.9 + 14 * 0.2 / 29, 0.2 / 29 * 100, 16.00025)),  # ratio 1 at 15.5
    (0.978, 1.5, 0.51, 159, (138.0, 138.0), (79, 0.51 + 78 * 0.99 / 158, 0.99 / 158 * 100, 75.6909091)),  # IEEE14
    (345.0, 360.0, 320.0, 33, (1.0, 340.0), (17, 340.0, 1.25 / 340 * 100, 21.0)),  # CW 2, NOMV 340: kV units
    (1.2, 1.3, 1.1, 5, (1.0, 1.0), (1, 1.1, 5.0, 3.0)),  # ratio 1 below RMI: the neutral is step 1
])
def test_ratio_tap(windv, rma, rmi, ntp, units, expected):
    unit_kv, rated_kv = units
    tap = ratio_tap(windv, rma, rmi, ntp, unit_kv=unit_kv, rated_kv=rated_kv, record_id="x")
    neutral_step, neutral, increment, step = expected
    assert tap.neutral_step == neutral_step
    assert tap.neutral_kv == pytest.approx(neutral * unit_kv)
    assert (tap.increment_percent, tap.step) == (pytest.approx(increment), pytest.approx(step))


@pytest.mark.parametrize(("windv", "rma", "rmi", "ntp", "message"), [
    (1.0, 1.1, 0.9, 1, "NTP 1 gives no tap range"),
    (1.0, 0.9, 1.1, 33, "RMA 0.9 is not above RMI 1.1"),
])
def test_ratio_tap_raises(windv, rma, rmi, ntp, message):
    with pytest.raises(ValueError, match=message):
        ratio_tap(windv, rma, rmi, ntp, unit_kv=1.0, rated_kv=1.0, record_id="x")


def test_wecc240_transformers(wecc240):
    """End 1 in ohm equals pu x BASKV^2 / SBASE, end 2 zero; the tap gives back WINDV, RMA and RMI; COD gives the
    control's state; CONT its terminal; RATE1-3 a limit on terminal 1."""
    native, network = wecc240
    base_kv = {record.bus_number: record.base_voltage for record in native.list_by_class(schema.BusRecord)}
    transformers = _objects(network, "PowerTransformer")
    rated = 0
    for record in native.list_by_class(schema.TransformerRecord):
        equipment = transformers[f"xf_{record.ID}"]
        ends = sorted(equipment.PowerTransformerEnd, key=lambda end: end.endNumber)
        z_base = base_kv[record.i] ** 2 / 100.0
        assert ends[0].r.to("ohm") == pytest.approx(record.r1_2 * z_base)
        assert ends[0].x.to("ohm") == pytest.approx(record.x1_2 * z_base)
        assert (float(ends[1].r), float(ends[1].x), float(ends[0].b)) == (0.0, 0.0, 0.0)
        assert [end.ratedU.to("kV") for end in ends] == [record.nomv1, record.nomv2]
        assert [end.Terminal.TopologicalNode.busNumber for end in ends] == [record.i, record.j]
        tap = ends[0].RatioTapChanger
        rated_kv = ends[0].ratedU.to("kV")
        increment = float(tap.stepVoltageIncrement) / 100
        neutral = tap.neutralU.to("kV") / rated_kv
        assert neutral + (tap.step - tap.neutralStep) * increment == pytest.approx(record.windv1)
        assert neutral + (tap.highStep - tap.neutralStep) * increment == pytest.approx(record.rma1)
        assert neutral + (tap.lowStep - tap.neutralStep) * increment == pytest.approx(record.rmi1)
        control = tap.TapChangerControl
        assert (tap.ltcFlag, tap.controlEnabled, control.enabled) == ((record.cod1 != 0,) + (record.cod1 > 0,) * 2)
        assert control.Terminal.mRID == f"bb_{record.cont1}_T1"
        assert control.targetValue == pytest.approx((record.vma1 + record.vmi1) / 2 * base_kv[record.cont1] * 1000)
        limit_sets = equipment.Terminals[0].OperationalLimitSet if record.rate1_3 else []
        rated += bool(limit_sets)
        assert [limit.normalValue.to("MVA") for limit_set in limit_sets for limit in limit_set.OperationalLimitValue] == \
            ([pytest.approx(record.rate1_3)] if record.rate1_3 else [])
    assert (len(transformers), rated) == (122, 42)
    controlled = [mrid for mrid, control in _objects(network, "TapChangerControl").items() if control.enabled]
    assert sorted(controlled) == ["xf_6103_6104_0_1_ctrl1", "xf_6302_6304_0_1_ctrl1"]


def test_ieee14_transformer_with_cont_0():
    """CONT 0 names the winding's own terminal; NOMV 0 rates the end at BASKV; WINDV off a step is a float step."""
    tap = _objects(_network(IEEE14, "IEEE14"), "RatioTapChanger")["xf_4_7_0_1_tap1"]
    assert tap.TapChangerControl.Terminal.mRID == "xf_4_7_0_1_T1"
    assert (tap.TapChangerControl.enabled, tap.ltcFlag) == (False, False)
    assert tap.TransformerEnd.ratedU.to("kV") == 138.0
    assert (tap.neutralStep, tap.step) == (79, pytest.approx(75.6909091))


def test_transformer_atom():
    network = _network(TRANSFORMER_ATOMS / "transformers.raw")
    ends = _objects(network, "PowerTransformerEnd")
    controls = _objects(network, "TapChangerControl")
    a = ends["xf_1_2_0_1_1"]  # CW 2, CZ 2, CM 2, NOMV1 340 on a 345 kV bus
    assert (a.ratedU.to("kV"), a.BaseVoltage.mRID, a.r.to("ohm")) == (340.0, "bv_345kv", pytest.approx(1.156))
    assert a.b.to("S") == pytest.approx(-(0.005 ** 2 - 0.00075 ** 2) ** 0.5 * 200.0 / 340.0 ** 2)
    assert (a.RatioTapChanger.neutralStep, a.RatioTapChanger.step) == (17, 21.0)
    assert (a.PowerTransformer.vectorGroup, controls["xf_1_2_0_1_ctrl1"].Terminal.mRID) == ("YNd1", "bb_5_T1")
    b = controls["xf_2_6_0_1_ctrl1"]  # COD -1: the tap changes under load, its control out of service
    assert (b.enabled, b.TapChanger[0].ltcFlag, b.TapChanger[0].controlEnabled) == (False, True, False)
    c = controls["xf_6_7_0_1_ctrl1"]  # COD 2: a Mvar band through its own winding
    assert (c.mode.name, c.Terminal.mRID, c.targetValue, c.targetDeadband) == ("reactivePower", "xf_6_7_0_1_T1",
                                                                               5.0e6, 30.0e6)
    mesh = _objects(network, "TransformerMeshImpedance")
    assert sorted(mesh) == [f"xf_{key}_mesh_{pair}" for key in ("1_2_3_1", "6_7_4_2") for pair in ("12", "13", "23")]
    assert mesh["xf_1_2_3_1_mesh_13"].FromTransformerEnd is ends["xf_1_2_3_1_1"]
    assert mesh["xf_1_2_3_1_mesh_23"].r.to("ohm") == pytest.approx(0.002 * 230.0 ** 2 / 100.0)  # from end 2
    assert mesh["xf_6_7_4_2_mesh_23"].x.to("ohm") == pytest.approx(0.07 * 34.5 ** 2 / 30.0)  # CZ 2 on SBASE2-3
    d = ends["xf_1_2_3_1_1"]
    assert (d.r, d.ratedS, d.g.to("S")) == (None, None, pytest.approx(0.0005 * 100.0 / 345.0 ** 2))
    assert controls["xf_1_2_3_1_ctrl2"].targetValue == pytest.approx(1.01 * 230000.0)
    limits = {limit.mRID: limit.normalValue.to("MVA") for limit in _objects(network, "ApparentPowerLimit").values()}
    assert limits == {"xf_1_2_0_1_1_rate1": 250.0, "xf_1_2_0_1_1_rate2": 300.0, "xf_1_2_3_1_1_rate1": 400.0,
                      "xf_1_2_3_1_3_rate1": 80.0, "xf_6_7_0_1_1_rate1": 60.0}
    assert _objects(network, "OperationalLimitSet")["xf_1_2_3_1_3_ratings"].Terminal.mRID == "xf_1_2_3_1_T3"


def test_transformer_atom_comments():
    document = next(part for part in RawImporter("atom").to_cimtbl(
        Raw34Reader(TRANSFORMER_ATOMS / "transformers.raw").read_all()).parts if part.name == "transformer")
    rows = {row.cells[0]: row for statement in document.statements for row in statement.rows}
    assert rows["xf_6_7_4_2"].comment.startswith("defaulted: nomv1=0.0, ang1=0.0")
    assert "cod3=0" in rows["xf_6_7_4_2"].comment
    assert rows["xf_1_2_0_1"].comment is None  # a 2-winding unit's 3-winding slots are never defaulted
    assert document.statements[0].comment == ("untranscribed: o1, o2, o3, o4, f1, f2, f3, f4, zcod, vmstar, anstar\n"
                                              "untranscribed off a tie: NMETR (a tie's TieFlows record it; CIM 18 "
                                              "gap, RAW-22)")


@pytest.mark.parametrize(("key", "changes", "error", "message"), [
    ("1_2_0_1", {"cod1": -5}, NotImplementedError, "COD1 -5 .asymmetric phase shift"),
    ("1_2_0_1", {"cod1": 4}, NotImplementedError, "COD1 4 .DC line control: phase 2"),
    ("1_2_3_1", {"tab2": 1}, NotImplementedError, "TAB2 = 1 on a 3-winding unit"),
    ("1_2_0_1", {"tab1": 7}, ValueError, "TAB1 7 names no impedance correction table"),
    ("6_7_0_1", {"cr1": 0.01}, ValueError, "CR1/CX1 .load-drop compensation. on COD1 2, not a voltage control"),
    ("1_2_0_1", {"cnxa1": 30.0}, NotImplementedError, "CNXA1 = 30.0"),
    ("1_2_0_1", {"nod1": 2}, ValueError, "which has no SUBSTATION block"),
    ("1_2_0_1", {"status": 2}, ValueError, "STAT 2 .one winding out. on a 2-winding unit"),
    ("1_2_0_1", {"cont1": 99}, ValueError, "CONT1 99 is no bus"),
    ("1_2_0_1", {"ntp1": 1}, ValueError, "NTP 1 gives no tap range"),
    ("1_2_0_1", {"cod1": 3, "rma1": 30.0, "rmi1": -30.0, "vma1": 10.0, "vmi1": 5.0, "ang1": 40.0}, ValueError,
     "ANG 40.0 is outside RMI..RMA"),
    ("1_2_0_1", {"rma1": None}, ValueError, "RMA1 is blank and has no default .CW 2, COD1 1"),
    ("6_7_0_1", {"vma1": None}, ValueError, "VMA1 is blank and has no default .CW 1, COD1 2"),
    ("2_6_0_1", {"x1_2": 0.0001}, ValueError, "CZ 3 .Z. = 0.0001 pu is less than its load-loss r"),
])
def test_a_transformer_outside_r4b_raises(key, changes, error, message):
    native = Raw34Reader(TRANSFORMER_ATOMS / "transformers.raw").read_all()
    _replace_record(native, schema.TransformerRecord, key, **changes)
    with pytest.raises(error, match=message):
        RawImporter("atom").to_cimtbl(native)


# -- R4b: the transformer forms R4 raised on ---------------------------------------------------------------------

R4B_ATOM = TRANSFORMER_ATOMS / "forms_r4b.raw"


def test_ratio_tap_extends_to_a_windv_outside_its_range():
    tap = ratio_tap(1.15, 1.1, 0.9, 33, unit_kv=345.0, rated_kv=345.0, record_id="x")
    assert (tap.low_step, tap.high_step, tap.neutral_step, tap.step) == (1, 41, 17, pytest.approx(41.0))
    below = ratio_tap(0.85, 1.1, 0.9, 33, unit_kv=1.0, rated_kv=1.0, record_id="x")
    assert (below.low_step, below.high_step, below.step) == (-7, 33, pytest.approx(-7.0))


@pytest.mark.parametrize(("angle", "rma", "rmi", "ntp", "expected"), [
    (7.5, 30.0, -30.0, 33, (17, -1.875, 21.0, 0.0)),  # 0 deg on the grid
    (-10.0, 40.0, -30.0, 32, (14, -70.0 / 31, 14 - 10.0 * 31 / 70.0, -30.0 + 13 * 70.0 / 31)),  # off the grid
])
def test_phase_tap(angle, rma, rmi, ntp, expected):
    tap = phase_tap(angle, rma, rmi, ntp, "x")
    assert (tap.neutral_step, tap.increment_degrees, tap.step, tap.zero_offset_degrees) == \
        (expected[0], *(pytest.approx(value) for value in expected[1:]))


@pytest.mark.parametrize(("args", "message"), [
    ((0.0, 30.0, -30.0, 1), "NTP 1 gives no tap range"),
    ((0.0, -30.0, 30.0, 33), "RMA -30.0 is not above RMI 30.0"),
    ((31.0, 30.0, -30.0, 33), "ANG 31.0 is outside RMI..RMA"),
])
def test_phase_tap_raises(args, message):
    with pytest.raises(ValueError, match=message):
        phase_tap(*args, "x")


def test_r4b_derived_values():
    assert (cim_angle(30.0), cim_angle(-13.5), str(cim_angle(0.0))) == (-30.0, 13.5, "0.0")
    assert (watts_from_mw(110.0), impedance_deviation_percent(1.2)) == (110.0e6, pytest.approx(20.0))
    assert (is_angle_table([-30.0, 40.0]), is_angle_table([0.9, 1.1]), is_angle_table([0.94, 1.6])) == \
        (True, False, True)


@pytest.fixture(scope="module")
def r4b_network():
    return _network(R4B_ATOM)


def test_r4b_fixed_phase_shifts(r4b_network):
    """phaseShift = cim_angle(ANGk) on each end; a phase shifter's angle is on its tap, not its end (R4b-2)."""
    ends = _objects(r4b_network, "PowerTransformerEnd")
    shifts = {mrid: float(end.phaseShift) for mrid, end in ends.items() if end.phaseShift is not None}
    assert shifts == {"xf_1_2_0_F_1": -30.0, "xf_1_2_3_G_2": 13.5}


def test_r4b_phase_shifters(r4b_network):
    """COD +-3: a PhaseTapChangerLinear over NTP steps and an activePower control on its own terminal (R4b-3)."""
    taps = _objects(r4b_network, "PhaseTapChangerLinear")
    j, k = taps["xf_2_5_0_J_ptap1"], taps["xf_2_5_0_K_ptap1"]
    assert (j.lowStep, j.highStep, j.neutralStep, j.step) == (1, 33, 17, 21.0)
    assert float(j.stepPhaseShiftIncrement) == -1.875
    assert (j.neutralStep - j.step) * float(j.stepPhaseShiftIncrement) == pytest.approx(7.5)  # back to ANG
    assert (j.TransformerEnd.mRID, j.ltcFlag, j.controlEnabled) == ("xf_2_5_0_J_1", True, True)
    control = j.TapChangerControl
    assert (control.mode.name, control.Terminal.mRID, control.targetValue, control.targetDeadband) == \
        ("activePower", "xf_2_5_0_J_T1", 110.0e6, 20.0e6)
    assert (k.controlEnabled, k.TapChangerControl.enabled) == (False, False)  # COD -3
    assert (k.neutralStep - k.step) * float(k.stepPhaseShiftIncrement) == pytest.approx(-10.0)
    fixed = k.TransformerEnd.RatioTapChanger  # its off-nominal WINDV1 1.02: a fixed ratio (R4b-4)
    assert (fixed.lowStep, fixed.highStep, fixed.neutralU.to("kV"), fixed.TapChangerControl) == \
        (1, 1, pytest.approx(234.6), None)


def test_r4b_fixed_ratios(r4b_network):
    """A winding without a usable tap range gets a one-step RatioTapChanger at WINDV in kV (R4b-4)."""
    taps = _objects(r4b_network, "RatioTapChanger")
    fixed = {mrid: tap.neutralU.to("kV") for mrid, tap in taps.items() if tap.lowStep == tap.highStep}
    assert fixed == {"xf_2_5_0_K_tap1": pytest.approx(234.6), "xf_3_4_0_N_tap2": pytest.approx(13.2),
                     "xf_3_7_0_P_tap1": pytest.approx(82.8), "xf_6_7_0_M_tap2": pytest.approx(35.3625),
                     "xf_6_7_0_O_tap1": pytest.approx(120.75)}
    assert taps["xf_6_7_0_O_tap1"].TapChangerControl.enabled is False  # COD 0 keeps its control, disabled
    assert taps["xf_6_7_0_M_tap2"].TapChangerControl is None  # winding 2 has no COD data
    q = taps["xf_1_6_0_Q_tap1"]  # COD 1, WINDV 1.15 above RMA 1.1: the range extends to it (R4b-5)
    assert (q.lowStep, q.highStep, q.step) == (1, 41, pytest.approx(41.0))


def test_r4b_one_winding_out(r4b_network):
    """STAT 2/3/4: the unit stays in service, the out winding's terminal is disconnected (R4b-6)."""
    terminals = _objects(r4b_network, "Terminal")
    disconnected = sorted(mrid for mrid, terminal in terminals.items() if terminal.connected is False)
    assert disconnected == ["xf_1_2_3_G_T3", "xf_1_2_4_H_T2", "xf_1_3_4_I_T1"]
    assert all(_objects(r4b_network, "PowerTransformer")[f"xf_{key}"].inService for key in ("1_2_3_G", "1_2_4_H"))


def test_r4b_voltage_control_terminals_and_line_drop(r4b_network):
    """CONT 0 names the own terminal (R4b-7), a negative CONT bus |CONT| (R4b-8); CR/CX in ohm (R4b-9)."""
    controls = _objects(r4b_network, "TapChangerControl")
    assert controls["xf_2_7_0_R_ctrl1"].Terminal.mRID == "xf_2_7_0_R_T1"
    assert controls["xf_5_6_0_S_ctrl1"].Terminal.mRID == "bb_2_T1"
    t = controls["xf_5_7_0_T_ctrl1"]
    assert (t.lineDropCompensation, t.lineDropR.to("ohm"), t.lineDropX.to("ohm")) == \
        (True, pytest.approx(0.01 * 34.5 ** 2 / 100.0), pytest.approx(0.05 * 34.5 ** 2 / 100.0))


def test_r4b_impedance_tables(r4b_network):
    """One shared table per RAW table; angle points in CIM's sign, ratio points per ratedU; rEnd1 = xEnd1 =
    100 x (F - 1); each winding with TABk links its end to its table (R4b-10)."""
    tables = _objects(r4b_network, "ImpedanceTapChangerTable")
    points = {name: sorted(table.ImpedanceTapChangerTablePoint,
                           key=lambda point: float(point.angle) if point.angle is not None else point.ratio)
              for name, table in tables.items()}
    assert [float(point.angle) for point in points["ict_1"]] == [-40.0, -30.0, -20.0, -10.0, 0.0, 10.0, 30.0]
    assert [float(point.rEnd1) for point in points["ict_1"]] == pytest.approx([30.0, 20.0, 12.0, 5.0, 0.0, 5.0, 20.0])
    assert [point.ratio for point in points["ict_2"]] == pytest.approx([t * 230.0 / 240.0 for t in (0.9, 1.0, 1.1)])
    assert all(float(point.xEnd1) == float(point.rEnd1) for table in points.values() for point in table)
    tabulars = _objects(r4b_network, "ImpedanceTapChangerTabular")
    assert {mrid: (tabular.TransformerEnd.mRID, tabular.ImpedanceTapChangerTable.mRID)
            for mrid, tabular in tabulars.items()} == {"xf_2_5_0_K_ztab1": ("xf_2_5_0_K_1", "ict_1"),
                                                      "xf_2_6_0_L_ztab1": ("xf_2_6_0_L_1", "ict_2")}


def test_r4b_row_comments():
    documents = RawImporter("atom").to_cimtbl(Raw34Reader(R4B_ATOM).read_all())
    rows = {row.cells[0]: row.comment for part in documents.parts if part.name == "transformer"
            for statement in part.statements for row in statement.rows}
    assert rows["xf_2_5_0_K_ptap1"].startswith("untranscribed: rma1=40.0, rmi1=-30.0 (0 deg lies 0.645")
    assert rows["xf_2_5_0_J_ptap1"] is None
    assert rows["xf_6_7_0_O_tap1"] == ("fixed: untranscribed: rma1=1.0, rmi1=1.0, ntp1=33 (RMI..RMA holds no WINDV; "
                                       "unused at COD 0)")
    assert rows["xf_1_6_0_Q_tap1"] == "untranscribed: rma1=1.1, rmi1=0.9 (steps extended to the WINDV)"
    assert rows["xf_5_6_0_S_ctrl1"] == "untranscribed: cont1=-2 (bus 2 taken as on winding 1's side)"
    assert rows["xf_2_7_0_R_ctrl1"] == "CONT 0: regulates its own terminal"


@pytest.mark.parametrize(("changes", "error", "message"), [
    ({"points": [schema.ImpedanceCorrectionPoint(0.9, 0.95, 0.01), schema.ImpedanceCorrectionPoint(1.1, 1.0, 0.0)]},
     NotImplementedError, r"Im\(F\) != 0 at T \[0.9\]"),
    ({"points": [schema.ImpedanceCorrectionPoint(0.9, 0.95, 0.0)]}, ValueError, "1 point.s., at least 2 needed"),
])
def test_an_impedance_table_outside_r4b_raises(changes, error, message):
    native = Raw34Reader(R4B_ATOM).read_all()
    _replace_record(native, schema.ImpedanceCorrectionRecord, "2", **changes)
    with pytest.raises(error, match=message):
        RawImporter("atom").to_cimtbl(native)


def test_a_ratio_table_with_disagreeing_users_raises():
    native = Raw34Reader(R4B_ATOM).read_all()
    _replace_record(native, schema.TransformerRecord, "6_7_0_M", tab1=2)  # NOMV 0 on 115 kV: BASKV / ratedU = 1
    with pytest.raises(ValueError, match="table 2: a ratio table whose users .* have different BASKV / ratedU"):
        RawImporter("atom").to_cimtbl(native)


# -- R5: areas, tie flows and inter-area transfer ----------------------------------------------------------------

AREA_ATOM = TESTS / "atoms" / "area" / "areas.raw"


def test_net_import():
    """PDES is a desired export; netInterchange is positive into the area. 0 stays 0.0, not -0.0."""
    assert net_import(50.0) == -50.0
    assert net_import(-50.0) == 50.0
    assert str(net_import(0.0)) == "0.0"


def _traced_areas(network) -> dict[str, str]:
    """TopologicalNode mRID -> ControlArea mRID by the export rule (R5): seeds from generating units and tie flows,
    spread across devices with no tie flow."""
    areas: dict[str, str] = {}
    for membership in _objects(network, "ControlAreaGeneratingUnit").values():
        for machine in membership.GeneratingUnit.RotatingMachine:
            areas[machine.Terminals[0].TopologicalNode.mRID] = membership.ControlArea.mRID
    for membership in _objects(network, "ControlAreaPowerElectronicsUnit").values():
        connection = membership.PowerElectronicsUnit.PowerElectronicsConnection
        areas[connection.Terminals[0].TopologicalNode.mRID] = membership.ControlArea.mRID
    devices: dict[str, list] = {}
    for terminal in _objects(network, "Terminal").values():
        devices.setdefault(terminal.ConductingEquipment.mRID, []).append(terminal)
    neighbours: dict[str, set[str]] = {}
    for terminals in devices.values():
        flows = [flow for terminal in terminals for flow in terminal.TieFlow]
        if flows:
            home = next(flow.ControlArea.mRID for flow in flows if flow.positiveFlowIn)
            for terminal in terminals:
                outside = [flow for flow in terminal.TieFlow if not flow.positiveFlowIn]
                areas[terminal.TopologicalNode.mRID] = outside[0].ControlArea.mRID if outside else home
        elif len(terminals) > 1:
            nodes = {terminal.TopologicalNode.mRID for terminal in terminals}
            for node in nodes:
                neighbours.setdefault(node, set()).update(nodes - {node})
    stack = list(areas)
    while stack:
        node = stack.pop()
        for neighbour in neighbours.get(node, ()):
            if neighbour not in areas:
                areas[neighbour] = areas[node]
                stack.append(neighbour)
    return areas


@pytest.mark.parametrize(("case", "untraced"), [(IEEE14, set()), (WECC240, set()), (AREA_ATOM, {303})],
                         ids=["IEEE14", "WECC240", "areas"])
def test_the_trace_recovers_every_bus_area(case, untraced):
    """The export rule gives each bus its RAW AREA, except the buses the importer lists as untraced."""
    native = Raw34Reader(case).read_all()
    traced = _traced_areas(raw_to_cim(native, name="case"))
    expected = {str(record.bus_number): f"ca_{record.area}" for record in native.list_by_class(schema.BusRecord)
                if record.bus_number not in untraced}
    assert traced == expected
    node_rows = {row.cells[0]: row for part in RawImporter("case").to_cimtbl(native).parts if part.name == "bus"
                 for statement in part.statements if statement.cim_class == "TopologicalNode" for row in statement.rows}
    listed = {int(node) for node, row in node_rows.items() if "untranscribed: area=" in (row.comment or "")}
    assert listed == untraced


def _tie_pairs(network) -> dict[str, list[tuple[str, bool]]]:
    """Terminal mRID -> its tie flows as (ControlArea mRID, positiveFlowIn)."""
    pairs: dict[str, list[tuple[str, bool]]] = {}
    for flow in _objects(network, "TieFlow").values():
        pairs.setdefault(flow.Terminal.mRID, []).append((flow.ControlArea.mRID, flow.positiveFlowIn))
    return {terminal: sorted(flows) for terminal, flows in pairs.items()}


def test_wecc240_tie_flows(wecc240):
    """Each tie branch has its pair on the metered terminal (MET), the bus's area out and the other end's in."""
    native, network = wecc240
    area = {record.bus_number: record.area for record in native.list_by_class(schema.BusRecord)}
    expected = {}
    for record in native.list_by_class(schema.BranchRecord):
        buses = (record.from_bus_number, record.to_bus_number)
        if area[buses[0]] != area[buses[1]]:
            metered = record.metered_end
            expected[f"ln_{record.ID}_T{metered}"] = sorted([(f"ca_{area[buses[metered - 1]]}", False),
                                                             (f"ca_{area[buses[2 - metered]]}", True)])
    assert len(expected) == 23
    assert _tie_pairs(network) == expected


def test_area_atom():
    network = _network(AREA_ATOM)
    assert _tie_pairs(network) == {
        "ln_102_201_1_T1": [("ca_1", False), ("ca_2", True)],  # MET 1: bus I metered, J home
        "ln_102_201_2_T2": [("ca_1", True), ("ca_2", False)],  # MET 2
        "ln_202_301_1_T1": [("ca_2", False), ("ca_3", True)],  # MET blank: 1
        "sw_102_301_1_T2": [("ca_1", True), ("ca_3", False)],  # METERED 2
        "xf_202_302_0_1_T2": [("ca_2", True), ("ca_3", False)],  # NMETR 1: winding 1 home
        "xf_101_202_302_1_T1": [("ca_1", False), ("ca_3", True)],  # NMETR 3: windings 1 and 2 metered
        "xf_101_202_302_1_T2": [("ca_2", False), ("ca_3", True)],
    }
    areas = _objects(network, "ControlArea")
    assert {mrid: area.netInterchange.to("MW") for mrid, area in areas.items()} == {"ca_1": -50.0, "ca_2": 50.0,
                                                                                    "ca_3": 0.0}
    assert len(areas["ca_1"].TieFlow) == 4  # ln_102_201_1, ln_102_201_2, sw_102_301_1, xf_101_202_302_1


def test_area_atom_comments():
    documents = RawImporter("atom").to_cimtbl(Raw34Reader(AREA_ATOM).read_all())
    assert "not mapped" not in documents.master.comment
    control_areas = next(part for part in documents.parts if part.name == "area_interchange").statements[0]
    assert control_areas.comment == (
        "untranscribed: bus_number\nderived: netInterchange = -PDES (net_import)\nuntranscribed: inter-area "
        "transfers (CIM 18 gap): 1 -> 2 '1' 30.0 MW; 1 -> 2 'A' 20.0 MW; 3 -> 2 '1' 0.0 MW\n(defaulted: "
        "transfer_id, power_transfer)")


@pytest.mark.parametrize(("cls", "key", "changes", "message"), [
    (schema.BranchRecord, "102_201_1", {"metered_end": 3}, "metered_end"),
    (schema.SwitchRecord, "102_301_1", {"metered_end": 0}, "metered_end"),
    (schema.TransformerRecord, "202_302_0_1", {"nmetr": 3}, "NMETR 3 names no winding of a 2-winding tie"),
    (schema.InterareaTransferRecord, None, {"to_area": 9}, "to_area 9 has no area-interchange record"),
])
def test_an_area_form_outside_r5_raises(cls, key, changes, message):
    native = Raw34Reader(AREA_ATOM).read_all()
    key = key or next(iter(native.graph[cls]))
    _replace_record(native, cls, key, **changes)
    with pytest.raises(ValueError, match=message):
        RawImporter("atom").to_cimtbl(native)


def test_a_tie_to_an_area_with_no_record_raises():
    native = Raw34Reader(AREA_ATOM).read_all()
    _replace_record(native, schema.BusRecord, "302", area=9)
    with pytest.raises(ValueError, match="AREA 9 has no area-interchange record"):
        RawImporter("atom").to_cimtbl(native)


def test_non_tie_metered_ends_are_not_checked():
    """MET is read only on a tie: an internal branch's MET 3 maps (and stays untranscribed)."""
    native = Raw34Reader(AREA_ATOM).read_all()
    _replace_record(native, schema.BranchRecord, "101_102_1", metered_end=3)
    RawImporter("atom").to_cimtbl(native)


# -- node-breaker substations (R6) -------------------------------------------------------------------


def _placements(network) -> dict[str, str]:
    """Equipment Terminal mRID -> its ConnectivityNode, leaving out the substation switching devices' and node
    busbars' own Terminals."""
    return {key: terminal.ConnectivityNode.mRID for key, terminal in _objects(network, "Terminal").items()
            if terminal.ConnectivityNode is not None and not key.startswith(("sw_s", "bb_s"))}


def _statement(document, cim_class: str):
    return next(statement for statement in document.statements if getattr(statement, "cim_class", None) == cim_class
                and not statement.update)


@pytest.fixture(scope="module")
def ieee118():
    with cim_scope():
        native = Raw34Reader(IEEE118).read_all()
        return RawImporter("IEEE118").to_cimtbl(native), raw_to_cim(native, name="IEEE118")


@pytest.fixture(scope="module")
def forms():
    with cim_scope():
        native = Raw34Reader(FORMS_ATOM).read_all()
        return RawImporter("forms").to_cimtbl(native), raw_to_cim(native, name="forms")


@pytest.mark.parametrize("case", [NODE_BREAKER, IEEE118, FORMS_ATOM], ids=["node_breaker", "IEEE118", "forms"])
def test_a_node_sits_in_its_bus_and_substation(case):
    """Every Terminal on a ConnectivityNode is on that node's TopologicalNode, and every node is in its bus's
    substation."""
    network = raw_to_cim(Raw34Reader(case).read_all(), name="case")
    terminals = [terminal for terminal in _objects(network, "Terminal").values() if terminal.ConnectivityNode]
    assert terminals
    assert all(terminal.ConnectivityNode.TopologicalNode is terminal.TopologicalNode for terminal in terminals)
    for node in _objects(network, "ConnectivityNode").values():
        assert node.ConnectivityNodeContainer is node.TopologicalNode.ConnectivityNodeContainer


def test_two_bus_node_breaker_atom():
    network = raw_to_cim(Raw34Reader(NODE_BREAKER).read_all(), name="node_breaker")
    assert _placements(network) == {"ln_1_2_1_T1": "sub_s1_n3", "ln_1_2_2_T1": "sub_s1_n4",
                                    "ln_1_2_1_T2": "sub_s2_n3", "ln_1_2_2_T2": "sub_s2_n4"}
    breakers = _objects(network, "Breaker")
    assert len(breakers) == 7
    assert not any(breaker.open or breaker.normalOpen for breaker in breakers.values())


@pytest.mark.parametrize("part", ["substation", "equipment_terminal"])
def test_ieee118_part_matches_golden(ieee118, part):
    documents, _ = ieee118
    document = next(doc for doc in documents.parts if doc.name == part)
    assert_matches_golden(document, TESTS / "goldens" / "IEEE118" / f"{part}.cimtbl")


def test_ieee118_substation_blocks(ieee118):
    documents, network = ieee118
    assert "not mapped" not in documents.master.comment
    buses = _objects(network, "TopologicalNode")
    # buses 5 and 38 have no node data: their transformers merge them into the blocks' substations
    assert {bus: buses[bus].ConnectivityNodeContainer.mRID for bus in ("5", "8", "37", "38", "49", "100")} == {
        "5": "sub_s8", "8": "sub_s8", "37": "sub_s37", "38": "sub_s37", "49": "sub_s49", "100": "sub_s100"}
    assert {key: station.name for key, station in _objects(network, "Substation").items()
            if key.startswith("sub_s")} == {"sub_s8": "STATION_8", "sub_s37": "EASTLI", "sub_s49": "PHILO",
                                            "sub_s100": "GLEN L"}
    assert len(_objects(network, "ConnectivityNode")) == 42
    placements = _placements(network)
    assert len(placements) == 36
    assert placements["xf_38_37_0_1_T2"] == "sub_s37_n3"  # written '2' at the transformer's second winding
    assert placements["swsh_37_b1_T1"] == "sub_s37_n7"
    assert placements["ln_9_8_1_T2"] == "sub_s8_n3"  # the record at the line's to bus lists it first
    assert not _objects(network, "Location")
    assert not [key for key in _objects(network, "BusbarSection") if key.startswith("bb_s")]  # no NREG, NODk


def test_ieee118_main_and_transfer_bus(ieee118):
    """Block 100: the transfer bus (node 2) is out of service, its ten disconnectors and its breaker open."""
    documents, network = ieee118
    disconnectors = _objects(network, "Disconnector")
    assert len(disconnectors) == 10
    assert all(switch.open and switch.normalOpen for switch in disconnectors.values())
    assert _objects(network, "Breaker")["sw_s100_1_2_1"].open
    document = next(part for part in documents.parts if part.name == "substation")
    nodes = _statement(document, "ConnectivityNode")
    assert {row.cells[0]: row.comment for row in nodes.rows if row.comment} == {
        "sub_s100_n2": "untranscribed: status=0"}
    assert "no Location: blocks 8, 37, 49, 100 at LATI = LONG = 0 (the default)" in document.comment


def test_forms_atom_placements(forms):
    _, network = forms
    assert _placements(network) == {
        "sm_1_G_T1": "sub_s10_n2", "pec_1_PV_T1": "sub_s10_n2", "ln_1_3_A_T1": "sub_s10_n3",
        "cap_1_3_A_i_T1": "sub_s10_n3", "xf_1_2_0_1_T1": "sub_s10_n4", "xf_1_2_4_T_T1": "sub_s10_n5",
        "cap_2_1_T1": "sub_s10_n12", "ld_2_L1_T1": "sub_s10_n12", "swsh_2_b1_T1": "sub_s10_n13",
        "ln_5_2_1_T2": "sub_s10_n14", "xf_1_2_0_1_T2": "sub_s10_n15", "xf_1_2_4_T_T2": "sub_s10_n16"}
    terminals = _objects(network, "Terminal")
    assert terminals["cap_1_3_A_j_T1"].ConnectivityNode is None  # the line's other end, at free bus 3
    # free bus 4 joins the block's substation through the 3-winding transformer; its NI 0 record places nothing
    assert _objects(network, "TopologicalNode")["4"].ConnectivityNodeContainer.mRID == "sub_s10"
    assert terminals["xf_1_2_4_T_T3"].ConnectivityNode is None


def test_forms_atom_regulated_nodes(forms):
    """NREG and NOD1 name the node's busbar terminal; one busbar per regulated node (RAW-11)."""
    _, network = forms
    controls = {**_objects(network, "RegulatingControl"), **_objects(network, "TapChangerControl")}
    assert {key: controls[key].Terminal.mRID for key in ("gc_1", "cc_2", "xf_1_2_0_1_ctrl1")} == {
        "gc_1": "bb_s10_n1_T1", "cc_2": "bb_s10_n11_T1", "xf_1_2_0_1_ctrl1": "bb_s10_n11_T1"}
    terminals = _objects(network, "Terminal")
    assert {key: terminals[f"{key}_T1"].ConnectivityNode.mRID for key in _objects(network, "BusbarSection")
            if key.startswith("bb_s")} == {"bb_s10_n1": "sub_s10_n1", "bb_s10_n11": "sub_s10_n11"}


def test_forms_atom_location_and_devices(forms):
    _, network = forms
    location = _objects(network, "Substation")["sub_s10"].Location
    [point] = location.PositionPoints
    assert (point.xPosition, point.yPosition) == ("-119.1", "46.2")  # x = LONG, y = LATI
    assert location.CoordinateSystem.crsUrn == "urn:ogc:def:crs:OGC:1.3:CRS84"
    assert list(_objects(network, "Switch")) == ["sw_s10_1_4_1"]  # TYPE 1, a generic connector
    breakers = _objects(network, "Breaker")
    assert (breakers["sw_s10_11_13_1"].open, breakers["sw_s10_11_13_1"].normalOpen) == (True, True)
    assert (breakers["sw_s10_11_14_1"].open, breakers["sw_s10_11_14_1"].normalOpen) == (False, True)
    assert list(_objects(network, "ApparentPowerLimit")) == ["sw_s10_1_2_1_rate1"]


def test_forms_atom_comments(forms):
    documents, _ = forms
    parts = {part.name: part for part in documents.parts}
    nodes = _statement(parts["substation"], "ConnectivityNode")
    assert {row.cells[0]: row.comment for row in nodes.rows if row.comment} == {
        "sub_s10_n17": "untranscribed: vm=1.02, va=-2.5"}
    assert "untranscribed: grounding_resistance" in parts["substation"].comment
    terminals = next(statement for statement in parts["equipment_terminal"].statements)
    assert terminals.comment == ("each named equipment terminal on its node; 1 record with NI 0 (no node-breaker "
                                 "model) places nothing")
    stations = _statement(parts["bus"], "Substation")
    assert stations.rows[0].comment == "SUBSTATION block 10: buses 1, 2, 4; xf_1_2_0_1, xf_1_2_4_T"


def _second_block(native, bus: int) -> None:
    """Add block 20, holding one node of ``bus``."""
    block = native.graph[schema.SubstationRecord]["10"]
    native.graph[schema.SubstationRecord]["20"] = dataclasses.replace(block, substation_number=20)
    node = dataclasses.replace(native.graph[schema.SubstationNodeRecord]["10_17"], substation_number=20,
                               node_number=1, bus_number=bus)
    node.ID = "20_1"
    native.graph[schema.SubstationNodeRecord]["20_1"] = node


def _system_switch_named_by_a_terminal(native) -> None:
    """A system switching device 1-3 'Z', and the B record at bus 1 changed to name it."""
    native.graph[schema.SwitchRecord]["1_3_Z"] = schema.SwitchRecord(from_bus_number=1, to_bus_number=3, circuit="Z",
                                                                     stype=2)
    native.graph[schema.SwitchRecord]["1_3_Z"].ID = "1_3_Z"
    _replace_record(native, schema.EquipmentTerminalRecord, "10_1_B_3__A", identifier="Z")


_LOAD_TERMINAL = "10_2_L___L1"


@pytest.mark.parametrize(("change", "error", "message"), [
    (lambda native: _second_block(native, 2), ValueError, "bus 2 also has nodes in block 10"),
    (lambda native: _second_block(native, 4), ValueError, r"holding SUBSTATION blocks \[10, 20\]"),
    (lambda native: _replace_record(native, schema.BusRecord, "2", zone=2), ValueError, r"are in zones \[1, 2\]"),
    (lambda native: _replace_record(native, schema.StationSwitchingDeviceRecord, "10_1_2_1", to_node=1), ValueError,
     "NI = NJ = 1"),
    (lambda native: _replace_record(native, schema.StationSwitchingDeviceRecord, "10_1_2_1", to_node=99),
     ValueError, "node 99 is not in SUBSTATION block 10"),
    (lambda native: _replace_record(native, schema.EquipmentTerminalRecord, _LOAD_TERMINAL, node_number=1),
     ValueError, "has no node 1 of bus 2"),
    (lambda native: _replace_record(native, schema.EquipmentTerminalRecord, _LOAD_TERMINAL, identifier="L9"),
     ValueError, "names no load"),
    (lambda native: _replace_record(native, schema.EquipmentTerminalRecord, "10_1_M___PV", identifier="G"),
     ValueError, "Terminal sm_1_G_T1 is already placed"),
    (lambda native: _replace_record(native, schema.EquipmentTerminalRecord, _LOAD_TERMINAL, node_number=0),
     ValueError, r"NI 0 \(no node-breaker model\), but bus 2 has nodes"),
    (lambda native: _replace_record(native, schema.EquipmentTerminalRecord, _LOAD_TERMINAL, terminal_type="I"),
     NotImplementedError, r"TYP I \(induction machine, phase 2\)"),
    (lambda native: _replace_record(native, schema.EquipmentTerminalRecord, _LOAD_TERMINAL, terminal_type="X"),
     ValueError, "is no equipment form"),
    (_system_switch_named_by_a_terminal, ValueError, "names a system switching device"),
    (lambda native: _replace_record(native, schema.SwitchedShuntRecord, "2", nreg=9), ValueError,
     "SUBSTATION block 10 has no node 9 of bus 2"),
    (lambda native: _replace_record(native, schema.TransformerRecord, "1_2_0_1", cont1=0), ValueError,
     "NOD1 11 names a node, but CONT1 is 0"),
], ids=["bus in two blocks", "two blocks in one substation", "block across zones", "NI = NJ", "node outside block",
        "node of another bus", "unknown equipment", "placed twice", "NI 0 at a bus with nodes", "phase-2 form",
        "unknown form", "system switching device", "NREG with no node", "NOD with CONT 0"])
def test_a_node_breaker_form_outside_r6_raises(change, error, message):
    native = Raw34Reader(FORMS_ATOM).read_all()
    change(native)
    with pytest.raises(error, match=message):
        RawImporter("atom").to_cimtbl(native)


# -- P2a: shunt FACTS devices and VSC DC lines -------------------------------------------------------------------

DC_ATOM = TESTS / "atoms" / "dc" / "facts_vsc.raw"


@pytest.fixture(scope="module")
def dc_network():
    return _network(DC_ATOM)


def test_p2a_facts_devices(dc_network):
    """A StaticSynchronousCompensator per shunt-only device: ratedI from SHMX, a voltage control on FCREG (P2-2)."""
    devices = _objects(dc_network, "StaticSynchronousCompensator")
    remote, local, out = devices["fd_STATCOM-REM"], devices["fd_STATCOM-LOC"], devices["fd_STATCOM-OUT"]
    assert remote.ratedI.to("kA") == pytest.approx(ka_from_rating(50.0, 115.0))
    assert remote.Terminals[0].TopologicalNode.mRID == "302"
    control = remote.RegulatingControl
    assert (control.mode.name, control.Terminal.mRID, control.targetValue) == ("voltage", "bb_301_T1",
                                                                              pytest.approx(1.01 * 230000.0))
    assert (local.RegulatingControl.Terminal.mRID, local.inService) == ("bb_202_T1", True)
    assert (out.inService, out.ratedI.to("kA")) == (False, 0.0)


def test_p2a_vsc_dc_topology(dc_network):
    """A DCLine holds the segment and its two DCTopologicalNodes; each converter's one DC terminal sits on its own
    node (P2-1)."""
    segment = _objects(dc_network, "DCLineSegment")["vsc_VSC-TIE_seg"]
    assert (segment.resistance.to("ohm"), segment.inService, segment.EquipmentContainer.mRID) == \
        (1.58, True, "vsc_VSC-TIE")
    node = _objects(dc_network, "DCTopologicalNode")["vsc_VSC-TIE_n1"]
    assert sorted(terminal.mRID for terminal in node.DCTerminals) == ["vsc_VSC-TIE_c1_DC1", "vsc_VSC-TIE_seg_DC1"]
    converter_terminal = _objects(dc_network, "ACDCConverterDCTerminal")["vsc_VSC-TIE_c1_DC1"]
    assert converter_terminal.polarity.name == "positive"
    assert _objects(dc_network, "DCLineSegment")["vsc_VSC-OUT_seg"].inService is False


def test_p2a_vsc_converters(dc_network):
    """TYPE, MODE and their setpoints, losses, qShare, PccTerminal, the Q curve and the ratings (P2-3)."""
    converters = _objects(dc_network, "VsConverter")
    mw = converters["vsc_VSC-TIE_c1"]  # TYPE 2, MODE 1 on its own bus
    assert (mw.pPccControl.name, mw.targetPpcc.to("MW"), mw.qPccControl.name) == ("pPcc", -96.0, "voltagePcc")
    assert mw.targetUpcc.to("kV") == pytest.approx(1.02 * 230.0)
    assert (mw.idleLoss.to("kW"), float(mw.switchingLoss), mw.PccTerminal.mRID) == (1600.0, 3400.0, "bb_102_T1")
    (curve,) = mw.CapabilityCurve
    assert (curve.curveStyle.name, [(point.xvalue, point.y1value, point.y2value) for point in curve.CurveDatas]) == \
        ("constantYValue", [(0.0, -100.0, 200.0)])
    limits = {limit.mRID: limit.normalValue for limit in (*_objects(dc_network, "ApparentPowerLimit").values(),
                                                           *_objects(dc_network, "CurrentLimit").values())}
    assert (limits["vsc_VSC-TIE_c1_smax"].to("MVA"), limits["vsc_VSC-TIE_c1_imax"].to("A")) == (360.0, 1032.0)
    voltage = converters["vsc_VSC-TIE_c2"]  # TYPE 1, MODE 2
    assert (voltage.pPccControl.name, voltage.targetUdc.to("kV"), voltage.qPccControl.name,
            voltage.targetPowerFactorPcc, voltage.CapabilityCurve) == ("udc", 300.0, "powerFactorPcc", 0.95, [])
    remote = converters["vsc_VSC-OUT_c1"]  # MDC 0, VSREG 201, RMPCT 60
    assert (remote.inService, remote.PccTerminal.mRID, float(remote.qShare)) == (False, "bb_201_T1", 60.0)
    assert (converters["vsc_VSC-OUT_c2"].pPccControl, converters["vsc_VSC-OUT_c2"].inService) == (None, False)


def test_p2a_vsc_tie_flows(dc_network):
    """A tie's TieFlow pair is on the MW-control converter's terminal; the TYPE 1 converter is home (R5)."""
    flows = {flow.mRID: (flow.ControlArea.mRID, flow.positiveFlowIn, flow.Terminal.mRID)
             for flow in _objects(dc_network, "TieFlow").values() if "VSC" in flow.mRID}
    assert flows == {"tf_1_vsc_VSC-TIE_c1_T1": ("ca_1", False, "vsc_VSC-TIE_c1_T1"),
                     "tf_2_vsc_VSC-TIE_c1_T1": ("ca_2", True, "vsc_VSC-TIE_c1_T1")}


def test_p2a_row_comments():
    """What CIM cannot hold is listed on its row when it is not the default."""
    parts = {part.name: part for part in RawImporter("atom").to_cimtbl(Raw34Reader(DC_ATOM).read_all()).parts}
    rows = {row.cells[0]: row.comment for part in (parts["facts_device"], parts["vsc_dc"])
            for statement in part.statements for row in statement.rows}
    assert rows["fd_STATCOM-REM"] == "untranscribed: trmx=0.0, rmpct=75.0"
    assert rows["fd_STATCOM-LOC"] is None
    assert (rows["vsc_VSC-TIE_c1"], rows["vsc_VSC-TIE_c2"]) == ("untranscribed: pwf_1=0.5",
                                                                "untranscribed: minloss_2=1110.0")
    assert rows["vsc_VSC-OUT_c2"] == "untranscribed: dcset_2=100.0"


@pytest.mark.parametrize(("cls", "key", "changes", "error", "message"), [
    (schema.FactsDeviceRecord, "STATCOM-LOC", {"jbus": 201}, NotImplementedError, "J 201, a series element"),
    (schema.FactsDeviceRecord, "STATCOM-LOC", {"mode": 2}, ValueError, "mode"),
    (schema.FactsDeviceRecord, "STATCOM-LOC", {"remot": 999}, ValueError, "FCREG 999 is no bus"),
    (schema.VscDcRecord, "VSC-TIE", {"converter_type_2": 2}, ValueError, "exactly one TYPE 1"),
    (schema.VscDcRecord, "VSC-TIE", {"mode_1": 3}, ValueError, "mode_1"),
    (schema.VscDcRecord, "VSC-OUT", {"vsreg_1": 999}, ValueError, "VSREG 999 is no bus"),
])
def test_a_p2a_record_outside_the_spec_raises(cls, key, changes, error, message):
    native = Raw34Reader(DC_ATOM).read_all()
    native.graph[cls][key] = dataclasses.replace(native.graph[cls][key], **changes)
    with pytest.raises(error, match=message):
        RawImporter("atom").to_cimtbl(native)


# -- P2b: two-terminal DC lines behind their converter transformers ------------------------------------------------

DC2_ATOM = TESTS / "atoms" / "dc" / "two_terminal.raw"


@pytest.fixture(scope="module")
def dc2_network():
    return _network(DC2_ATOM)


def test_converter_transformer_derived_values():
    """r, x on end 1 = per-bridge ohms / (NB x TR^2); the tap's grid steps by STP from TMN (P2-5)."""
    assert converter_transformer_ohms(7.6004, 2, 0.5) == pytest.approx(15.2008)
    tap, top = converter_tap(1.0625, 1.1375, 0.8625, 0.0125, ebas_kv=230.0, record_id="x")
    assert (tap.low_step, tap.high_step, tap.neutral_step, tap.step, top) == \
        (1, 23, 12, pytest.approx(17.0), pytest.approx(1.1375))
    assert tap.increment_percent == pytest.approx(1.25)
    _, off_grid_top = converter_tap(1.024, 1.12, 0.88, 0.0125, ebas_kv=230.0, record_id="x")
    assert off_grid_top == pytest.approx(1.1175)


def test_p2b_converters_behind_their_transformers(dc2_network):
    """Each CsConverter sits on its internal valve-side node; its transformer joins that node to the AC bus."""
    converters, transformers = _objects(dc2_network, "CsConverter"), _objects(dc2_network, "PowerTransformer")
    inverter = converters["dc2_DC-TIE_i"]
    assert inverter.Terminals[0].TopologicalNode.mRID == "dc2_DC-TIE_i_int"
    assert [terminal.TopologicalNode.mRID for terminal in transformers["dc2_DC-TIE_i_xf"].Terminals] == \
        ["201", "dc2_DC-TIE_i_int"]
    ends = _objects(dc2_network, "PowerTransformerEnd")
    end_1, end_2 = ends["dc2_DC-TIE_i_xf_1"], ends["dc2_DC-TIE_i_xf_2"]
    assert (end_1.ratedU.to("kV"), end_2.ratedU.to("kV"), end_1.x.to("ohm")) == \
        (230.0, 115.0, pytest.approx(7.6004 / (2 * 0.5 ** 2)))
    assert end_2.BaseVoltage.nominalVoltage.to("kV") == 115.0
    tap = end_1.RatioTapChanger
    assert (tap.neutralStep, tap.step, tap.ltcFlag, tap.TapChangerControl) == (12, pytest.approx(17.0), True, None)
    assert (inverter.numberOfValves, inverter.operatingMode.name, float(inverter.maxGamma)) == (12, "inverter", 18.0)


def test_p2b_controls(dc2_network):
    """MDC and SETVL's sign set the rectifier's order and where targetPpcc sits; the inverter holds VSCHD."""
    converters = _objects(dc2_network, "CsConverter")
    tie_r, tie_i = converters["dc2_DC-TIE_r"], converters["dc2_DC-TIE_i"]  # MDC 1, SETVL -250: inverter power
    assert (tie_r.pPccControl.name, tie_r.targetPpcc) == ("activePower", None)
    assert (tie_i.pPccControl.name, tie_i.targetPpcc.to("MW"), tie_i.targetUdc.to("kV")) == ("dcVoltage", -250.0,
                                                                                             475.0)
    assert converters["dc2_DC-B2B_r"].targetPpcc.to("MW") == 150.0  # SETVL > 0: rectifier power
    current = converters["dc2_DC-CURRENT_r"]  # MDC 2
    assert (current.pPccControl.name, current.targetIdc.to("A")) == ("dcCurrent", 1000.0)
    blocked = converters["dc2_DC-BLOCKED_r"]  # MDC 0
    assert (blocked.inService, blocked.pPccControl, converters["dc2_DC-BLOCKED_i"].inService) == (False, None, False)
    assert _objects(dc2_network, "DCLineSegment")["dc2_DC-B2B_seg"].resistance.to("ohm") == 0.0


def test_p2b_tie_flows(dc2_network):
    """METER I: the inverter is metered, so its transformer's AC terminal carries the pair (R5)."""
    flows = {flow.mRID: (flow.ControlArea.mRID, flow.positiveFlowIn, flow.Terminal.mRID)
             for flow in _objects(dc2_network, "TieFlow").values() if "dc2" in flow.mRID}
    assert flows == {"tf_2_dc2_DC-TIE_i_xf_T1": ("ca_2", False, "dc2_DC-TIE_i_xf_T1"),
                     "tf_1_dc2_DC-TIE_i_xf_T1": ("ca_1", True, "dc2_DC-TIE_i_xf_T1")}


def test_p2b_row_comments():
    part = next(part for part in RawImporter("atom").to_cimtbl(Raw34Reader(DC2_ATOM).read_all()).parts
                if part.name == "two_terminal_dc")
    rows = {row.cells[0]: row.comment for statement in part.statements for row in statement.rows}
    assert rows["dc2_DC-BLOCKED"] == "untranscribed: delti=0.1, setvl=-413.1"
    assert rows["dc2_DC-CURRENT"] == "untranscribed: vcmod=118.1, delti=0.17"
    assert rows["dc2_DC-B2B_r"] == "untranscribed: icr=201"
    assert rows["dc2_DC-TIE_r_xf_tap1"] == "untranscribed: tmxr=1.12 (the STP grid tops out at 1.1175)"


@pytest.mark.parametrize(("changes", "error", "message"), [
    ({"ifr": 101, "itr": 102}, NotImplementedError, "IFR / ITR name an AC transformer"),
    ({"xcapi": 2.0}, NotImplementedError, "XCAPI 2.0, capacitor commutated"),
    ({"mdc": 3}, ValueError, "mdc"),
    ({"meter": "X"}, ValueError, "meter"),
    ({"ipi": 999}, ValueError, "inverter IPI 999 is no bus"),
    ({"stpr": 0.0}, ValueError, "STP 0.0 must be positive"),
])
def test_a_p2b_record_outside_the_spec_raises(changes, error, message):
    native = Raw34Reader(DC2_ATOM).read_all()
    cls = schema.TwoTerminalDCRecord
    native.graph[cls]["DC-TIE"] = dataclasses.replace(native.graph[cls]["DC-TIE"], **changes)
    with pytest.raises(error, match=message):
        RawImporter("atom").to_cimtbl(native)

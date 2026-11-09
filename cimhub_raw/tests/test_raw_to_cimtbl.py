"""R0-R2: the master, zone, area interchange, bus, branch, switch, multi-section line, load, fixed shunt and
switched shunt documents, and their bind under cim18v17 (BusBranchModel).

Goldens: ``tests/goldens/IEEE14/`` (``CIMHUB_UPDATE_GOLDENS=1`` rewrites them; review the diff).
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
    fixed_shunt,
    load,
    multi_section_line,
    owner,
    switch,
    switched_shunt,
    zone,
)
from cimhub_raw.importer.cimtbl.derived import (
    block_sections,
    ka_from_rating,
    kv_from_per_unit,
    load_p_q,
    per_unit_from_mva,
    volts_from_per_unit,
    zip_mix,
)
from cimhub_raw.importer.raw_to_cimtbl import RawImporter, raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader

TESTS = Path(__file__).parent
IEEE14 = TESTS / "cases" / "IEEE14" / "IEEE_14_bus.raw"
WECC240 = TESTS / "cases" / "WECC240" / "240busWECC_2018_PSS.raw"
NODE_BREAKER = TESTS / "atoms" / "substation" / "two_bus_node_breaker.raw"
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
                                    multi_section_line, load, fixed_shunt, switched_shunt],
                         ids=lambda module: module.__name__.rsplit(".", 1)[1])
def test_classification_is_complete(module):
    check_fields(module.FIELDS, module.NATIVE_CLASS)


def test_kv_from_per_unit():
    assert kv_from_per_unit(1.1, 138.0) == pytest.approx(151.8)
    assert kv_from_per_unit(0.0, 345.0) == 0.0


def test_ka_from_rating():
    """The spec's MVA = sqrt(3) x E x I: 100 MVA at 100 kV is 0.57735 kA."""
    assert ka_from_rating(100.0, 100.0) == pytest.approx(0.577350269)


# -- goldens -----------------------------------------------------------------------------------------


def test_master_matches_golden(ieee14_documents):
    assert_matches_golden(ieee14_documents.master, GOLDENS / "IEEE14.cimtbl")


@pytest.mark.parametrize("part", ["zone", "area_interchange", "bus", "branch", "load", "fixed_shunt"])
def test_part_matches_golden(ieee14_documents, part):
    document = next(doc for doc in ieee14_documents.parts if doc.name == part)
    assert_matches_golden(document, GOLDENS / f"{part}.cimtbl")


def test_import_order_is_the_mapping_order(ieee14_documents):
    assert [part.name for part in ieee14_documents.parts] == ["zone", "area_interchange", "bus", "branch", "load",
                                                              "fixed_shunt"]


# -- the bound networks ------------------------------------------------------------------------------


@pytest.mark.parametrize(("case", "name", "substations", "buses"),
                         [(IEEE14, "IEEE14", 11, 14), (WECC240, "WECC240", 134, 243),
                          (NODE_BREAKER, "node_breaker", 2, 2)],
                         ids=["IEEE14", "WECC240", "node_breaker"])
def test_binds(case, name, substations, buses):
    network = raw_to_cim(Raw34Reader(case).read_all(), name=name)
    assert len(_objects(network, "Substation")) == substations
    assert len(_objects(network, "TopologicalNode")) == buses
    assert len(_objects(network, "BusbarSection")) == buses
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
    assert "not mapped: GeneratorRecord 5, TransformerRecord 3" \
        in ieee14_documents.master.comment


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
    assert len(limits) == 281
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
    assert len(_objects(network, "RegulatingControl")) == 7


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
    ({"nreg": 2}, NotImplementedError, "NREG 2 names a node"),
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

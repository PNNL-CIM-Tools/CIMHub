"""R0 and R1: the master, zone, area interchange, bus, branch, switch and multi-section line documents, and their
bind under cim18v17 (BusBranchModel).

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
    multi_section_line,
    owner,
    switch,
    zone,
)
from cimhub_raw.importer.cimtbl.derived import ka_from_rating, kv_from_per_unit
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
                                    multi_section_line],
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


@pytest.mark.parametrize("part", ["zone", "area_interchange", "bus", "branch"])
def test_part_matches_golden(ieee14_documents, part):
    document = next(doc for doc in ieee14_documents.parts if doc.name == part)
    assert_matches_golden(document, GOLDENS / f"{part}.cimtbl")


def test_import_order_is_the_mapping_order(ieee14_documents):
    assert [part.name for part in ieee14_documents.parts] == ["zone", "area_interchange", "bus", "branch"]


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
    assert "not mapped: FixedShuntRecord 1, GeneratorRecord 5, LoadRecord 11, TransformerRecord 3" \
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

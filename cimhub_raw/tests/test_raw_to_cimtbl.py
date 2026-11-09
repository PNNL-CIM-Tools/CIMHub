"""R0: the master, zone, area interchange and bus documents, and their bind under cim18v17 (BusBranchModel).

Goldens: ``tests/goldens/IEEE14/`` (``CIMHUB_UPDATE_GOLDENS=1`` rewrites them; review the diff).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_raw.importer.cimtbl import area_interchange, bus, case_identification, owner, zone
from cimhub_raw.importer.cimtbl.derived import kv_from_per_unit
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


@pytest.mark.parametrize("module", [case_identification, zone, area_interchange, bus, owner],
                         ids=lambda module: module.__name__.rsplit(".", 1)[1])
def test_classification_is_complete(module):
    check_fields(module.FIELDS, module.NATIVE_CLASS)


def test_kv_from_per_unit():
    assert kv_from_per_unit(1.1, 138.0) == pytest.approx(151.8)
    assert kv_from_per_unit(0.0, 345.0) == 0.0


# -- goldens -----------------------------------------------------------------------------------------


def test_master_matches_golden(ieee14_documents):
    assert_matches_golden(ieee14_documents.master, GOLDENS / "IEEE14.cimtbl")


@pytest.mark.parametrize("part", ["zone", "area_interchange", "bus"])
def test_part_matches_golden(ieee14_documents, part):
    document = next(doc for doc in ieee14_documents.parts if doc.name == part)
    assert_matches_golden(document, GOLDENS / f"{part}.cimtbl")


def test_import_order_is_the_mapping_order(ieee14_documents):
    assert [part.name for part in ieee14_documents.parts] == ["zone", "area_interchange", "bus"]


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
    assert "not mapped: BranchRecord 17, FixedShuntRecord 1, GeneratorRecord 5, LoadRecord 11, TransformerRecord 3" \
        in ieee14_documents.master.comment


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

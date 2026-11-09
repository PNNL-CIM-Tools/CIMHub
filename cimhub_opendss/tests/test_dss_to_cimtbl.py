"""The orchestrator: master and bus documents, Import order, and the IEEE13_CDPSM artifacts binding."""

from __future__ import annotations

import pytest

from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_opendss import DssImporter, DssReader, dss_to_cim
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.dss_to_cimtbl import MAPPING_ORDER
from cimhub_opendss.schema import opendss_schema as schema

from conftest import DECKS


def assert_base_voltages_agree(network) -> None:
    """Every ConductingEquipment and TransformerEnd BaseVoltage equals that of each node it connects to. A
    transformer has none of its own (its ends carry them)."""
    cim = network.cim
    differ = []
    for cls in network.graph:
        if issubclass(cls, (cim.PowerTransformerEnd, cim.AutoTransformerEnd)):  # a phase end has no Terminal
            for end in network.graph[cls].values():
                if end.Terminal.ConnectivityNode.BaseVoltage is not end.BaseVoltage:
                    differ.append((end.mRID, end.Terminal.ConnectivityNode.mRID))
        if not issubclass(cls, cim.ConductingEquipment) or issubclass(cls, (cim.PowerTransformer, cim.AutoTransformer)):
            continue
        for equipment in network.graph[cls].values():
            for terminal in equipment.Terminals:
                if terminal.ConnectivityNode.BaseVoltage is not equipment.BaseVoltage:
                    differ.append((equipment.mRID, terminal.ConnectivityNode.mRID))
    assert not differ, f"BaseVoltage differs from the node's: {differ[:5]}"

IEEE13 = DECKS / "IEEE" / "IEEE13_CDPSM" / "IEEE13_CDPSM.dss"
GOLDENS = DECKS.parent / "goldens" / "IEEE13_CDPSM"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def ieee13():
    return DssReader(IEEE13).read_all()


@pytest.fixture(scope="module")
def documents(ieee13):
    return DssImporter("IEEE13_CDPSM").to_cimtbl(ieee13)


def test_master_matches_golden(documents):
    assert_matches_golden(documents.master, GOLDENS / "IEEE13_CDPSM.cimtbl")


def test_bus_matches_golden(documents):
    [bus] = [part for part in documents.parts if part.name == "bus"]
    assert_matches_golden(bus, GOLDENS / "bus.cimtbl")


def test_parts_follow_the_mapping_order(documents):
    assert [part.name for part in documents.parts] == ["bus", "zip_fractions", "linecode", "xfmrcode", "vsource",
                                                       "line", "transformer", "regcontrol", "load", "capacitor"]
    assert len(MAPPING_ORDER) == len({native_class for native_class, _ in MAPPING_ORDER})


def test_a_class_with_no_records_writes_no_part(tmp_path):
    deck = tmp_path / "bare.dss"
    deck.write_text("New Circuit.bare basekv=12.47\n")
    documents = DssImporter("bare").to_cimtbl(DssReader(deck).read_all())
    assert [part.name for part in documents.parts] == ["bus", "zip_fractions", "vsource"]


def test_a_deck_without_a_circuit_raises(tmp_path):
    deck = tmp_path / "bare.dss"
    deck.write_text("New Vsource.s basekv=12.47\n")
    with pytest.raises(ValueError, match="the deck has no New Circuit"):
        DssImporter("bare").to_cimtbl(DssReader(deck).read_all())


def test_base_frequency_comes_from_the_deck(tmp_path):
    deck = tmp_path / "bare.dss"
    deck.write_text("Set defaultbasefreq=50\nNew Circuit.bare basekv=11\n")
    master = DssImporter("bare").to_cimtbl(DssReader(deck).read_all()).master
    [frequency] = [s for s in master.statements if getattr(s, "cim_class", None) == "BaseFrequency"]
    assert [text for _, text in frequency.cells] == ["bf_50hz", "50.0"] and frequency.comment is None


def test_ieee13_binds_under_cim18v17(ieee13, tmp_path):
    network = dss_to_cim(ieee13, name="IEEE13_CDPSM", artifact_dir=tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "IEEE13_CDPSM.cimtbl", "bus.cimtbl", "capacitor.cimtbl", "line.cimtbl", "linecode.cimtbl", "load.cimtbl",
        "regcontrol.cimtbl", "transformer.cimtbl", "vsource.cimtbl", "xfmrcode.cimtbl", "zip_fractions.cimtbl"]
    assert_base_voltages_agree(network)
    cim = network.cim
    counts = {cls: len(network.graph.get(getattr(cim, cls), {})) for cls in (
        "ACLineSegment", "LoadBreakSwitch", "Fuse", "Recloser", "PowerTransformer", "VoltageRegulator",
        "TapChangerControl", "EnergyConsumer", "LinearShuntCompensator")}
    assert counts == {"ACLineSegment": 11, "LoadBreakSwitch": 3, "Fuse": 1, "Recloser": 1, "PowerTransformer": 3,
                      "VoltageRegulator": 3, "TapChangerControl": 3, "EnergyConsumer": 16,
                      "LinearShuntCompensator": 2}
    nodes = network.graph[network.cim.ConnectivityNode].values()
    assert len(nodes) == 22 and all(node.ConnectivityNodeContainer.mRID == "fdr_ieee13nodeckt" for node in nodes)
    [source] = network.graph[network.cim.EnergySource].values()
    assert source.EquipmentContainer.mRID == "sub_ieee13nodeckt"
    impedances = network.graph[network.cim.PerLengthPhaseImpedance]
    assert len(impedances) == 7
    [mtx601] = [z for z in impedances.values() if z.name == "mtx601"]
    data = {(d.row, d.column): d for d in mtx601.PhaseImpedanceData}
    assert float(data[(2, 1)].r.to("ohm/mi")) == pytest.approx(0.1535)  # verbatim from the deck
    assert float(data[(3, 3)].x.to("ohm/mi")) == pytest.approx(1.0348)


def test_tpoletop_is_by_its_center_tap_template(ieee13):
    # Tpoletop (XfmrCode CT5, a center tap) is a tank on the lug template, its phase ends on its terminals
    network = dss_to_cim(ieee13, name="IEEE13_CDPSM")
    cim = network.cim
    [tank] = [tank for tank in network.graph[cim.TransformerTank].values() if tank.PowerTransformer.name == "Tpoletop"]
    assert tank.TankConfiguration.mRID == "xc_ct5"
    lugs = {lug.designation: lug.sequenceNumber for lug in network.graph[cim.TransformerLug].values()}
    assert lugs == {"H1": 1, "H2": 2, "X1": 3, "X3": 4, "X2": 5}
    phase_ends = {end.sequenceNumber: (end.phase.value, end.Terminal.mRID)
                  for end in network.graph[cim.TransformerPhaseEnd].values() if end.mRID.startswith("xf_tpoletop")}
    assert phase_ends == {1: ("B", "xf_tpoletop_T1"), 2: ("N", "xf_tpoletop_T1"), 3: ("s1", "xf_tpoletop_T2"),
                          4: ("s2", "xf_tpoletop_T2"), 5: ("N", "xf_tpoletop_T2")}


def test_dss_defaults_are_typed_as_deck_text():
    defaults = dss_defaults(schema.Load)
    assert defaults["model"].text == "ConstantPQ"  # int(1) on an enum slot is DSS code 1
    assert (defaults["pf"], defaults["CVRwatts"], defaults["CVRvars"]) == (0.88, 1.0, 2.0)
    assert dss_defaults(schema.Options)["defaultbasefreq"] == 60.0


def test_ieee13_assets_catalogs_bind(tmp_path):
    native = DssReader(DECKS / "IEEE" / "IEEE13_assets" / "IEEE13_Assets.dss").read_all()
    network = dss_to_cim(native, name="IEEE13_Assets", artifact_dir=tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "IEEE13_Assets.cimtbl", "bus.cimtbl", "capacitor.cimtbl", "capcontrol.cimtbl", "cndata.cimtbl",
        "line.cimtbl", "linegeometry.cimtbl", "linespacing.cimtbl", "load.cimtbl", "regcontrol.cimtbl",
        "transformer.cimtbl", "tsdata.cimtbl", "vsource.cimtbl", "wiredata.cimtbl", "xfmrcode.cimtbl",
        "zip_fractions.cimtbl"]
    cim = network.cim
    # 7 geometries and the synthesized configuration of 684652 (spacing 510 + wires)
    assert len(network.graph[cim.WireConfiguration]) == 8 and len(network.graph[cim.XYSpacing]) == 5

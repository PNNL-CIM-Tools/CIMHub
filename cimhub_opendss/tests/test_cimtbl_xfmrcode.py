"""Atom tests: OpenDSS XfmrCode -> xfmrcode.cimtbl (TankEnd or lug templates) and its instances in transformer.cimtbl
-> cim18v17, with the engine as the oracle for each template's ratings and impedances."""

from __future__ import annotations

import math
from pathlib import Path

import opendssdirect as dss
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_opendss import dss_to_cim
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer import dss_to_cimtbl
from cimhub_opendss.importer.cimtbl import transformer, xfmrcode

from conftest import ENGINE_DECKS, compile_deck, deck

ATOMS = Path(__file__).parent / "atoms" / "xfmrcode"
CIRCUIT = "Clear\nNew Circuit.atom basekv=12.47 bus1=sourcebus pu=1.0 MVAsc3=20000 MVAsc1=21000\n"
CT25 = "New XfmrCode.ct25 phases=1 windings=3 kVs=[7.2 0.12 0.12] kVAs=[25 25 25]\n"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def codes():
    return DssReader(ATOMS / "codes.dss").read_all()


def test_classification_is_complete():
    check_fields(xfmrcode.FIELDS, xfmrcode.NATIVE_CLASS)


def test_matches_golden(codes):
    site = dss_to_cimtbl.site(codes)
    assert_matches_golden(xfmrcode.map_xfmrcode(codes, site.buses), ATOMS / "codes.cimtbl")
    assert_matches_golden(transformer.map_transformer(codes, site.buses, site.feeder),
                          ATOMS / "codes_transformer.cimtbl")


def test_codes_bind(codes):
    network = dss_to_cim(codes, name="atom")
    cim = network.cim
    tanks = {tank.PowerTransformer.name: tank.TankConfiguration.name for tank in network.graph[cim.TransformerTank].values()}
    assert tanks == {"sub": "sub", "t1": "ct25", "t2": "ct25", "yyda": "yyd", "yydb": "yyd", "yydc": "yyd"}
    [ct25] = [c for c in network.graph[cim.TransformerTankConfiguration].values() if c.name == "ct25"]
    lugs = {lug.mRID: lug for lug in network.graph[cim.TransformerLug].values()}
    windings = sorted(ct25.TransformerWinding, key=lambda w: w.mRID)
    assert [(w.FromTransformerLug.designation, w.ToTransformerLug.designation) for w in windings] == [
        ("H1", "H2"), ("X1", "X2"), ("X2", "X3")]
    assert {lug.designation: lug.sequenceNumber for lug in lugs.values() if lug.TankConfiguration is ct25} == {
        "H1": 1, "H2": 2, "X1": 3, "X3": 4, "X2": 5}
    # any other 1-phase code: two lugs per winding, numbered in each coil's node order (TankEnds are 3-phase only)
    [yyd] = [c for c in network.graph[cim.TransformerTankConfiguration].values() if c.name == "yyd"]
    assert not yyd.TransformerTankEnd
    assert sorted((w.FromTransformerLug.designation, w.FromTransformerLug.sequenceNumber,
                   w.ToTransformerLug.designation, w.ToTransformerLug.sequenceNumber)
                  for w in yyd.TransformerWinding) == [("H1", 1, "H2", 2), ("X1", 3, "X2", 4), ("Y1", 5, "Y2", 6)]
    t2 = {end.sequenceNumber: end.phase.value for end in network.graph[cim.TransformerPhaseEnd].values()
          if end.mRID.startswith("xf_t2_")}
    assert t2 == {1: "B", 2: "N", 3: "s1", 4: "s2", 5: "N"}
    assert "unused" not in {c.name for c in network.graph[cim.TransformerTankConfiguration].values()}


@pytest.mark.parametrize("text, message", [
    (CT25 + "New Transformer.t XfmrCode=ct25 buses=[sourcebus.1 h.1.0 h.0.2] kVAs=[50 50 50]\n",
     "sets kVAs, which its XfmrCode ct25 also sets"),
    (CT25 + "New Transformer.t XfmrCode=ct25 buses=[sourcebus.1 h.0.1 h.2.0]\n", "lugs are mapped for bus2.1.0"),
    # one instance line to neutral on the 12.47 kV system (12470Y nameplate), one line to line on 7.2 kV delta (7200)
    (CT25 + "New Transformer.t XfmrCode=ct25 buses=[sourcebus.1 h.1.0 h.0.2]\n"
            "New Transformer.d phases=3 buses=[sourcebus delta] conns=[wye delta] kVs=[12.47 7.2] kVAs=[500 500]\n"
            "New Transformer.u XfmrCode=ct25 buses=[delta.1.2 k.1.0 k.0.2]\n", "different templates"),
    ("New XfmrCode.c phases=1 windings=3 kVs=[7.2 2.4 2.4] kVAs=[100 50 50]\n"
     "New Transformer.t XfmrCode=c buses=[sourcebus.1 a.1 b.1]\n", "mesh's From winding \\(2\\) must carry it"),
    # TankEnds are for 3-phase templates only, and a 1-phase one is one can
    ("New XfmrCode.c phases=2 kVs=[12.47 0.48] kVAs=[50 50]\n"
     "New Transformer.t XfmrCode=c buses=[sourcebus.1.2 a.1.2]\n", "phases=2; a template is 3-phase"),
])
def test_unmapped_codes_fail_fast(tmp_path, text, message):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + text)
    native = DssReader(path).read_all()
    with pytest.raises(ValueError, match=message):
        xfmrcode.map_xfmrcode(native, dss_to_cimtbl.site(native).buses)


def _engine_template_differences(network) -> list[str]:
    """Every difference between each instance's template and the engine's transformer: winding kV, kVA, %R and
    the mesh x."""
    cim = network.cim
    differences = []

    def check(label: str, ours: float, theirs: float) -> None:
        if not math.isclose(ours, theirs, rel_tol=1e-9, abs_tol=1e-12):
            differences.append(f"{label}: {ours} vs {theirs}")

    for tank in network.graph.get(cim.TransformerTank, {}).values():
        configuration = tank.TankConfiguration
        if configuration is None:
            continue
        dss.Transformers.Name(tank.PowerTransformer.name)
        windings = sorted(configuration.TransformerWinding, key=lambda w: w.mRID)
        three_phase = dss.CktElement.NumPhases() == 3
        for number, winding in enumerate(windings, start=1):
            dss.Transformers.Wdg(number)
            label = f"{tank.PowerTransformer.name} winding {number}"
            kv = float((winding.ratedU if three_phase else winding.baseU).to("kV"))
            check(f"{label} kV", kv, dss.Transformers.kV())
            kva = float((winding.ratedS if three_phase else winding.baseS).to("kVA"))  # a coil's is its baseS
            check(f"{label} kVA", kva, dss.Transformers.kVA())
            z_base = float(winding.baseU.to("V")) ** 2 / float(winding.baseS.to("VA"))
            check(f"{label} %R", float(winding.r.to("ohm")) / z_base * 100, dss.Transformers.R())
        engine_x = {(1, 2): dss.Transformers.Xhl(), (1, 3): dss.Transformers.Xht(), (2, 3): dss.Transformers.Xlt()}
        for mesh in network.graph[cim.TransformerMeshImpedance].values():
            if mesh.FromWinding is None or mesh.FromWinding.TankConfiguration is not configuration:
                continue
            pair = (windings.index(mesh.FromWinding) + 1, windings.index(mesh.ToWinding) + 1)
            winding = mesh.FromWinding
            z_base = float(winding.baseU.to("V")) ** 2 / float(winding.baseS.to("VA"))
            check(f"{tank.PowerTransformer.name} x{pair}", float(mesh.x.to("ohm")) / z_base * 100, engine_x[pair])
    return differences


def test_atom_matches_the_engine(codes):
    network = dss_to_cim(codes, name="atom")
    compile_deck(ATOMS / "codes.dss")
    assert _engine_template_differences(network) == []


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_templates_match_the_engine(relative):
    path = deck(relative)
    try:
        network = dss_to_cim(DssReader(path).read_all(), name="deck")
    except ValueError as error:
        if "DSS-10" in str(error):
            pytest.skip(f"{relative}: stops before the transformers (DSS-10)")
        raise
    compile_deck(path)
    assert _engine_template_differences(network) == []


def test_rated_code_matches_golden_and_binds():
    """RdcOhms on the template windings and the seasonal Ratings on the template's own OperationalLimitSet
    (EquipmentConfiguration.OperationalLimitSet); the instance gets no set of its own."""
    native = DssReader(ATOMS / "rated.dss").read_all()
    site = dss_to_cimtbl.site(native)
    assert_matches_golden(xfmrcode.map_xfmrcode(native, site.buses), ATOMS / "rated.cimtbl")
    network = dss_to_cim(native, name="atom")
    cim = network.cim
    [code] = network.graph[cim.TransformerTankConfiguration].values()
    assert sorted((w.mRID, float(w.rDC.to("ohm"))) for w in code.TransformerWinding) == [
        ("xc_sub_wdg_1", pytest.approx(2.8103125)), ("xc_sub_wdg_2", pytest.approx(0.011014647))]
    limits = code.OperationalLimitSet.OperationalLimitValue
    assert sorted((limit.OperationalLimitType.name, float(limit.normalValue.to("kVA"))) for limit in limits) == [
        ("season 1", 22000.0), ("season 2", 25000.0)]
    [transformer] = network.graph[cim.PowerTransformer].values()
    assert not transformer.OperationalLimitSet

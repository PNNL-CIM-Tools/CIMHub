"""Atom tests: OpenDSS RegControl (+ the Transformer it names) -> transformer.cimtbl (VoltageRegulator or LTC) and
regcontrol.cimtbl -> cim18v17, with the engine as the oracle for the settings, the tap and the regulator nameplate."""

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
from cimhub_opendss.importer.cimtbl import regcontrol, transformer

from conftest import ENGINE_DECKS, compile_deck, deck

ATOMS = Path(__file__).parent / "atoms" / "regcontrol"
CIRCUIT = "Clear\nNew Circuit.atom basekv=12.47 bus1=sourcebus pu=1.0 MVAsc3=20000 MVAsc1=21000\n"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def regulators():
    return DssReader(ATOMS / "regulators.dss").read_all()


def test_classification_is_complete():
    check_fields(regcontrol.FIELDS, regcontrol.NATIVE_CLASS)


def test_matches_golden(regulators):
    site = dss_to_cimtbl.site(regulators)
    assert_matches_golden(transformer.map_transformer(regulators, site.buses, site.feeder),
                          ATOMS / "regulators_transformer.cimtbl")
    assert_matches_golden(regcontrol.map_regcontrol(regulators), ATOMS / "regulators.cimtbl")


def test_derived_settings():
    assert regcontrol.ct_ratio(700) == pytest.approx(3500)
    assert regcontrol.tap_range(1.0625, 1.1, 0.9, 32, name="t") == (-16, 16, 10, 0.625)
    with pytest.raises(ValueError, match="tap 0.625 is not a whole tap step"):
        regcontrol.tap_range(1.00390625, 1.1, 0.9, 32, name="t")


def test_regulators_bind(regulators):
    network = dss_to_cim(regulators, name="atom")
    cim = network.cim
    by_name = {regulator.name: regulator for regulator in network.graph[cim.VoltageRegulator].values()}
    assert sorted(by_name) == ["coded", "gang", "reg1", "vr_ll"]
    assert [terminal.phases.value for terminal in sorted(by_name["vr_ll"].Terminals, key=lambda t: t.sequenceNumber)] \
        == ["AB", "AB"]
    taps = {tap.name: tap for tap in network.graph[cim.RatioTapChanger].values()}
    assert taps["reg1"].TransformerEnd.mRID == "xf_reg1_2" and taps["reg1"].step == 10
    assert taps["ltc"].TransformerEnd.mRID == "xf_ltc_2" and type(taps["ltc"].TransformerEnd).__name__ == "PowerTransformerEnd"
    control = taps["reg1"].TapChangerControl
    assert control.Terminal.mRID == "xf_reg1_T2" and float(control.targetValue) == pytest.approx(7320)


@pytest.mark.parametrize("text, message", [
    ("New Transformer.t phases=1 buses=[sourcebus.1 b.1] kVs=[7.2 7.2] kVAs=[100 100]\n"
     "New RegControl.r transformer=t winding=2 bus=b\n", "bus not mapped"),
    ("New Transformer.t phases=1 buses=[sourcebus.1 b.1] kVs=[7.2 7.2] kVAs=[100 100]\n"
     "New RegControl.r transformer=t\nNew RegControl.s transformer=t\n", "named by RegControls r and s"),
    ("New Transformer.t phases=1 buses=[sourcebus.1 b.1] kVs=[7.2 7.2] kVAs=[100 200]\n"
     "New RegControl.r transformer=t winding=2\n", "regulator kVAs"),
    ("New Transformer.t phases=3 buses=[sourcebus b] kVs=[12.47 12.47] kVAs=[100 100] conns=[delta delta]\n"
     "New RegControl.r transformer=t winding=2\n", "3-phase regulator is mapped as wye"),
    ("New Transformer.t phases=1 buses=[sourcebus.1 b.1] kVs=[7.2 7.2] kVAs=[100 100] taps=[1 1.05]\n",
     "with no RegControl"),
])
def test_unmapped_regulators_fail_fast(tmp_path, text, message):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + text)
    native = DssReader(path).read_all()
    site = dss_to_cimtbl.site(native)
    with pytest.raises(ValueError, match=message):
        transformer.map_transformer(native, site.buses, site.feeder)
        regcontrol.map_regcontrol(native)


def _engine_regulator_differences(network, *, taps: bool) -> list[str]:
    """Every difference between the mapped tap changers (and regulator nameplates) and the engine's. ``taps``
    compares the tap position too: a deck that solves when compiled has moved it."""
    cim = network.cim
    differences = []

    def check(label: str, ours: float, theirs: float) -> None:
        if not math.isclose(ours, theirs, rel_tol=1e-9, abs_tol=1e-9):
            differences.append(f"{label}: {ours} vs {theirs}")

    for tap in network.graph.get(cim.RatioTapChanger, {}).values():
        control = tap.TapChangerControl
        dss.RegControls.Name(control.name)
        ptratio, ct_primary = float(control.ptRatio), float(tap.ctRating)
        name = control.name
        check(f"{name} vreg", float(control.targetValue) / ptratio, dss.RegControls.ForwardVreg())
        check(f"{name} band", float(control.targetDeadband) / ptratio, dss.RegControls.ForwardBand())
        check(f"{name} ptratio", ptratio, dss.RegControls.PTRatio())
        check(f"{name} CTprim", ct_primary, dss.RegControls.CTPrimary())
        check(f"{name} R", float(control.lineDropR.to("ohm")) * ct_primary / ptratio, dss.RegControls.ForwardR())
        check(f"{name} X", float(control.lineDropX.to("ohm")) * ct_primary / ptratio, dss.RegControls.ForwardX())
        check(f"{name} delay", float(tap.initialDelay.to("s")), dss.RegControls.Delay())
        check(f"{name} tapdelay", float(tap.subsequentDelay.to("s")), dss.RegControls.TapDelay())
        check(f"{name} reversible", bool(control.reversible), dss.RegControls.IsReversible())
        check(f"{name} revvreg", float(control.reverseTargetValue) / ptratio, dss.RegControls.ReverseVreg())
        check(f"{name} revband", float(control.reverseTargetDeadband) / ptratio, dss.RegControls.ReverseBand())
        winding = dss.RegControls.Winding()
        dss.Transformers.Name(dss.RegControls.Transformer())
        dss.Transformers.Wdg(winding)
        increment = float(tap.stepVoltageIncrement) / 100
        if taps:
            check(f"{name} tap", 1 + tap.step * increment, dss.Transformers.Tap())
        check(f"{name} MaxTap", 1 + tap.highStep * increment, dss.Transformers.MaxTap())
        check(f"{name} MinTap", 1 + tap.lowStep * increment, dss.Transformers.MinTap())
        check(f"{name} NumTaps", tap.highStep - tap.lowStep, dss.Transformers.NumTaps())
        check(f"{name} neutralU", float(tap.neutralU.to("kV")), dss.Transformers.kV())
        if tap.TransformerEnd.endNumber != winding:
            differences.append(f"{name}: end {tap.TransformerEnd.endNumber}, winding {winding}")
    for end in network.graph.get(cim.AutoTransformerEnd, {}).values():
        dss.Transformers.Name(end.AutoTransformer.name)
        dss.Transformers.Wdg(end.endNumber)
        check(f"{end.mRID} baseU", float(end.baseU.to("kV")), dss.Transformers.kV())
        check(f"{end.mRID} ratedS", float(end.ratedS.to("kVA")), dss.Transformers.kVA())
    for mesh in network.graph.get(cim.TransformerMeshImpedance, {}).values():
        end = mesh.FromTransformerEnd
        if not isinstance(end, cim.AutoTransformerEnd):
            continue
        z_base = float(end.baseU.to("V")) ** 2 / float(end.ratedS.to("VA"))
        percent = {name: float(getattr(mesh, name).to("ohm")) / z_base * 100 for name in ("r", "x")}
        dss.Transformers.Name(end.AutoTransformer.name)
        check(f"{mesh.mRID} x", percent["x"], dss.Transformers.Xhl())
        resistance = 0.0
        for winding in (1, 2):
            dss.Transformers.Wdg(winding)
            resistance += dss.Transformers.R()
        check(f"{mesh.mRID} r", percent["r"], resistance)
    return differences


def test_atom_matches_the_engine(regulators):
    network = dss_to_cim(regulators, name="atom")
    compile_deck(ATOMS / "regulators.dss")
    assert _engine_regulator_differences(network, taps=True) == []


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_regulators_match_the_engine(relative):
    path = deck(relative)
    try:
        network = dss_to_cim(DssReader(path).read_all(), name="deck")
    except ValueError as error:
        if "DSS-10" in str(error) or "unset while another winding" in str(error):
            pytest.skip(f"{relative}: stops before the regulators ({str(error)[:80]})")
        raise
    compile_deck(path)
    assert _engine_regulator_differences(network, taps=False) == []

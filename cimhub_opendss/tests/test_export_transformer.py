"""Export atoms: Transformer, XfmrCode, regulators and RegControl (EXPORT_MAPPING.md S6c), checked against the
original deck in the engine."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import opendssdirect as dss
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssImporter, DssReader
from cimhub_opendss.exporter.cim_to_dss import DssExporter
from cimhub_opendss.schema import opendss_schema as schema

from conftest import compile_deck
from engine_compare import assert_same_engine_state
from export_atoms import assert_matches_dss_golden, bus_names, export_atom, export_network

ATOMS = Path(__file__).parent / "atoms"
#: atom -> elements whose YPrim differs: ct_ab's phase-to-phase primary is written delta (a 1-phase coil's wye and
#: delta differ only in the engine's anti-float), and t2's ppm=0 is untranscribed
CASES = {
    "transformer/inline": {"transformer.ct_ab"},
    "xfmrcode/codes": {"transformer.t2"},
    "regcontrol/regulators": set(),
    "transformer/rated_inline": set(),
    "xfmrcode/rated": set(),
}
REGCONTROL_PROPERTIES = ("transformer", "winding", "vreg", "band", "ptratio", "CTprim", "R", "X", "delay",
                         "tapdelay", "reversible", "revvreg", "revband", "revR", "revX", "PTphase", "revThreshold",
                         "revDelay", "revNeutral", "enabled")
TAP_PROPERTIES = ("taps", "MaxTap", "MinTap", "NumTaps")


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _network(atom: str):
    path = ATOMS / f"{atom}.dss"
    return DssImporter(path.stem).to_cim(DssReader(path).read_all())


def _model(network):
    return DssExporter().to_model(network, name_source="name")


def _record(model, native_class, name):
    return next(record for record in model.list_by_class(native_class) if str(record.name).lower() == name)


def _object(network, cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)


@pytest.mark.parametrize("case", CASES)
def test_export_matches_the_original_in_the_engine(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    written = export_atom(atom, tmp_path, name_source="name")
    assert_same_engine_state(atom, written, yprim_differs=frozenset(CASES[case]))


@pytest.mark.parametrize("case", CASES)
def test_export_under_mrid_and_uri_solves_the_same(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    for name_source in ("mrid", "uri"):
        written, network = export_network(atom, tmp_path, name_source=name_source)
        assert_same_engine_state(atom, written, by_element=False, bus_names=bus_names(network, name_source))


@pytest.mark.parametrize("case", CASES)
def test_export_matches_golden(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    written = export_atom(atom, tmp_path, name_source="mrid")
    assert_matches_dss_golden(written, atom.parent / "export" / f"{atom.stem}.dss")


@pytest.mark.parametrize(("case", "element"), [("transformer/rated_inline", "Transformer.b13552-1a"),
                                               ("xfmrcode/rated", "XfmrCode.sub")])
def test_ratings_and_dc_resistance_match_the_engine(case, element, tmp_path):
    """The exported Seasons, Ratings and each winding's RdcOhms are what the engine read from the original."""
    atom = ATOMS / f"{case}.dss"
    written = export_atom(atom, tmp_path, name_source="name")
    assert _rating_properties(written, element) == _rating_properties(atom, element)


def _rating_properties(path, element: str) -> dict:
    compile_deck(path)
    values = {}
    for prop in ("Seasons", "Ratings"):
        dss.Text.Command(f"? {element}.{prop}")
        values[prop] = dss.Text.Result()
    for winding in (1, 2):
        dss.Text.Command(f"{element}.wdg={winding}")
        dss.Text.Command(f"? {element}.RdcOhms")
        values[f"RdcOhms {winding}"] = float(dss.Text.Result())
    return values


# regulators ----------------------------------------------------------------------------------------------------


def _properties(path: Path, element: str, properties) -> dict[str, object]:
    """The engine's ``properties`` of ``element``, as floats where they are numbers."""
    compile_deck(path)
    dss.Circuit.SetActiveElement(element)
    values = {}
    for name in properties:
        text = dss.Properties.Value(name).strip().lower()
        try:
            values[name] = float(text)
        except ValueError:
            values[name] = text
    return values


@pytest.mark.parametrize("name", ["reg1", "vr_ll", "gang", "coded", "ltc"])
def test_regulator_settings_match_the_engine(name, tmp_path):
    atom = ATOMS / "regcontrol" / "regulators.dss"
    written = export_atom(atom, tmp_path, name_source="name")
    for element, properties in ((f"RegControl.{name}", REGCONTROL_PROPERTIES), (f"Transformer.{name}", TAP_PROPERTIES)):
        expected, actual = _properties(atom, element, properties), _properties(written, element, properties)
        for slot, value in expected.items():
            assert actual[slot] == (value if isinstance(value, str) else pytest.approx(value, rel=1e-9)), \
                f"{element}.{slot}"


def test_regulator_resistance_is_the_mesh_r_halved():
    transformer = _record(_model(_network("regcontrol/regulators")), schema.Transformer, "reg1")
    # %LoadLoss=0.01 in the deck: r = %R1 + %R2 on the mesh (DSS-13)
    assert (transformer.pct_Rs, transformer.taps) == ([0.005, 0.005], [1.0, 1.0625])


def test_regcontrol_without_pt_ratio_raises():
    network = _network("regcontrol/regulators")
    control = _object(network, cim.TapChangerControl, "rc_reg1")
    tap = _object(network, cim.RatioTapChanger, "rc_reg1_tap")
    control.ptRatio = tap.ptRatio = None
    with pytest.raises(ValueError, match="ptRatio is unset"):
        _model(network)


def test_regcontrol_monitoring_another_terminal_raises():
    network = _network("regcontrol/regulators")
    control = _object(network, cim.TapChangerControl, "rc_reg1")
    control.Terminal = _object(network, cim.TapChangerControl, "rc_gang").Terminal
    with pytest.raises(ValueError, match="monitors another Terminal than its tap's end"):
        _model(network)


def test_line_drop_without_ct_rating_raises():
    network = _network("regcontrol/regulators")
    _object(network, cim.RatioTapChanger, "rc_reg1_tap").ctRating = None
    with pytest.raises(ValueError, match=r"a line drop \['R', 'X'\] needs the tap's ctRating"):
        _model(network)


def test_regcontrol_in_another_mode_raises():
    network = _network("regcontrol/regulators")
    _object(network, cim.TapChangerControl, "rc_ltc").mode = cim.RegulatingControlModeKind.currentFlow
    with pytest.raises(ValueError, match="mode currentFlow; a RegControl regulates voltage"):
        _model(network)


# transformers --------------------------------------------------------------------------------------------------


def test_neutral_through_an_impedance_is_on_node_4():
    transformer = _record(_model(_network("transformer/inline")), schema.Transformer, "sub3")
    assert transformer.buses[1].endswith(".1.2.3.4")
    assert (transformer.wdg, transformer.Rneut, transformer.Xneut) == (2, 0.0, pytest.approx(0.4))


def test_ungrounded_wye_is_on_node_4_without_rneut():
    transformer = _record(_model(_network("transformer/inline")), schema.Transformer, "ug")
    assert transformer.buses == ["634.1.2.3", "ug.1.2.3.4"] and transformer.Rneut is None


def test_two_neutral_impedances_raise():
    network = _network("transformer/inline")
    end = _object(network, cim.PowerTransformerEnd, "xf_sub3_3")
    end.rground = cim.Resistance(1.0)
    with pytest.raises(ValueError, match=r"a neutral impedance on windings \[2, 3\]"):
        _model(network)


def test_center_tap_half_is_written_at_the_can_kva():
    transformer = _record(_model(_network("transformer/inline")), schema.Transformer, "ct_bn")
    assert (transformer.kVAs, transformer.buses) == ([25.0] * 3, ["650.2.0", "house2.1.0", "house2.0.2"])


def test_mesh_resistance_raises():
    network = _network("transformer/inline")
    [mesh] = _object(network, cim.PowerTransformerEnd, "xf_xfm1_1").FromMeshImpedance
    mesh.r = cim.PerCent(0.1)
    with pytest.raises(ValueError, match=r"a mesh r between windings \[\(1, 2\)\]"):
        _model(network)


def test_several_tanks_are_one_transformer_each_named_by_the_tank():
    network = _network("transformer/inline")
    transformer = _object(network, cim.PowerTransformer, "xf_ct_bn")
    [tank] = transformer.TransformerTanks
    tank.name = "ct_bn_a"  # the importer names no tank: a one-tank transformer goes by its own name
    second = cim.TransformerTank(mRID="tank_b", name="ct_bn_b", PowerTransformer=transformer,
                                 TransformerWindings=list(tank.TransformerWindings))
    transformer.TransformerTanks.append(second)
    names = {str(record.name) for record in _model(network).list_by_class(schema.Transformer)}
    assert {"ct_bn_a", "ct_bn_b"} <= names and "ct_bn" not in names


# XfmrCode ------------------------------------------------------------------------------------------------------


def test_tank_end_coil_keeps_its_direction():
    """T3: yydc's delta tertiary runs C -> A (tert.3.1); the bank's voltages move 1.6 kV if it is reversed."""
    transformer = _record(_model(_network("xfmrcode/codes")), schema.Transformer, "yydc")
    assert (transformer.XfmrCode, transformer.buses) == ("yyd", ["feeder.3.0", "low.3.0", "tert.3.1"])


def test_instances_name_their_code_and_hold_only_buses():
    transformer = _record(_model(_network("xfmrcode/codes")), schema.Transformer, "t1")
    assert (transformer.XfmrCode, transformer.phases, transformer.kVs) == ("ct25", None, [])


def test_unused_configuration_is_skipped_and_logged(caplog):
    """A feeder package carries its utility's whole catalogue (T5): a template no unit uses gets no XfmrCode."""
    network = _network("xfmrcode/codes")
    network.add_to_graph(cim.TransformerTankConfiguration(mRID="xc_spare", name="spare"))
    with caplog.at_level("WARNING"):
        codes = {str(code.name) for code in _model(network).list_by_class(schema.Xfmrcode)}
    assert "spare" not in codes and "ct25" in codes
    assert "TransformerTankConfigurations ['xc_spare']: no unit uses them" in caplog.text

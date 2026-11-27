"""Regression tests for code-review fixes across reader, writer, importer, and exporter."""
from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl import cimtbl_to_cim
from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssExporter, DssImporter, DssModel, DssParseError, DssReader, DssWriter, dss_to_cim
from cimhub_opendss.dss_name_map import build_type_registry, get_class_map
from cimhub_opendss.dss_reader import _engine_name, _eval_rpn
from cimhub_opendss.exporter import loadshape as exp_loadshape, wire as exp_wire
from cimhub_opendss.exporter.linegeometry import geometry_name
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.importer import dss_to_cimtbl
from cimhub_opendss.importer.cimtbl import (buscoords, capcontrol, geometry, injection, line, linecode, load, loadshape,
                                            regcontrol, transformer, vsource)
from cimhub_opendss.schema import opendss_schema as schema


@pytest.fixture(autouse=True)
def _scope():
    with cim_scope():
        yield


def _read(tmp_path, text: str) -> DssModel:
    deck = tmp_path / "deck.dss"
    deck.write_text(text, encoding="utf-8")
    return DssReader(deck).read_all()


# ---------------------------------------------------------------------------
# Reader, writer, name map
# ---------------------------------------------------------------------------

def test_edit_transformer_with_wdg_raises(tmp_path):
    base = ("New Circuit.c basekv=12.47\n"
            "New Transformer.t phases=3 windings=2 buses=[sourcebus b2] kVs=[12.47 0.48] kVAs=[500 500]\n")
    with pytest.raises(DssParseError, match="wdg="):
        _read(tmp_path, base + "Edit Transformer.t wdg=2 tap=1.05\n")
    with pytest.raises(DssParseError, match="wdg="):
        _read(tmp_path, base + "Transformer.t.tap=1.05\n")
    with pytest.raises(DssParseError, match="wdg="):
        _read(tmp_path, base + "New Transformer.t wdg=2 tap=1.05\n")
    # Array edits remain allowed
    model = _read(tmp_path, base + "Edit Transformer.t taps=[1.0 1.05]\n")
    assert model.list_by_class(schema.Transformer)[0].taps == [1.0, 1.05]


def test_format_matrix_rejects_non_triangular():
    with pytest.raises(ValueError, match="not a lower triangle"):
        DssWriter._format_matrix([1.0, 2.0, 3.0, 4.0])
    with pytest.raises(ValueError, match="not a lower triangle"):
        DssWriter._format_matrix([1.0, 2.0])
    assert DssWriter._format_matrix([1.0, 2.0, 3.0]) == "[1 |2 3]"


def test_redirect_cycle_raises_parse_error(tmp_path):
    (tmp_path / "a.dss").write_text("Redirect b.dss\n", encoding="utf-8")
    (tmp_path / "b.dss").write_text("Redirect a.dss\n", encoding="utf-8")
    with pytest.raises(DssParseError, match="Redirect cycle detected"):
        DssReader(tmp_path / "a.dss").read_all()


def test_writer_empty_string_comments_and_linkml_bool(tmp_path):
    load_rec = schema.Load(name="L!1//x", bus1="b1", kW=10.0, yearly="", enabled=True)
    text = DssWriter().serialize(load_rec)
    assert "yearly=" not in text
    assert "!" not in text and "//" not in text
    assert "enabled=Yes" in text

    with pytest.raises(ValueError, match="non-finite"):
        DssWriter().serialize(schema.Load(name="bad", bus1="b1", kW=float("nan")))


def test_tcc_curve_registry_and_field_prefix_matching(tmp_path):
    registry = build_type_registry()
    assert registry.get("tcc_curve") is schema.TccCurve
    assert "options" not in registry and "buscoords" not in registry

    cm = get_class_map(schema.Loadshape)
    assert cm.field_for("n") == "npts"
    with pytest.raises(ValueError, match="unknown property"):
        cm.field_for("")
    assert _engine_name("", ("type", "mode")) is None

    model = _read(tmp_path, "New TCC_Curve.c npts=2 c_array=[1 2] t_array=[0.5 0.1]\n"
                            "New Loadshape.s n=2 mult=[1 0.5]\n")
    assert len(model.list_by_class(schema.TccCurve)) == 1
    assert model.list_by_class(schema.Loadshape)[0].npts == 2


def test_rpn_arrays_braces_strings_and_stack(tmp_path):
    model = _read(tmp_path, 'New Circuit.c basekv=12.47\n'
                            'New Capacitor.c1 bus1="pi" kvar=(600 3 /) kV=12.47\n'
                            'New Line.l1 bus1=sourcebus bus2=b2 length=10\n'
                            'Line.l1.length={100 2 *}\n')
    cap = model.list_by_class(schema.Capacitor)[0]
    assert cap.bus1 == "pi"
    assert cap.kvar == [200.0]
    assert model.list_by_class(schema.Line)[0].length == 200.0

    # Stack ops: stack [1, 2, 3] (X=3): rolldn -> [3, 1, 2] (top=2); rollup -> [2, 3, 1] (top=1)
    assert _eval_rpn("1 2 3 rolldn") == 2.0
    assert _eval_rpn("1 2 3 rollup") == 1.0
    with pytest.raises(ValueError):
        _eval_rpn("10 10000 ^")
    with pytest.raises(ValueError):
        _eval_rpn("-1 0.5 ^")


def test_like_deep_copy_and_history_order(tmp_path):
    model = _read(tmp_path, "New Circuit.c basekv=12.47\n"
                            "New Generator.g1 bus1=sourcebus kW=100 kvar=50 kW=200\n"
                            "New Generator.g2 like=g1\n"
                            "New Capacitor.c1 bus1=sourcebus kvar=[300]\n"
                            "New Capacitor.c2 like=c1\n")
    g1, g2 = model.list_by_class(schema.Generator)
    assert model.last_of(g1, "kW", "kvar") == "kW"
    assert model.last_of(g2, "kW", "kvar") == "kW"
    c1, c2 = model.list_by_class(schema.Capacitor)
    c2.kvar.append(100.0)
    assert c1.kvar == [300.0]


def test_linegeometry_cond_edge_cases(tmp_path):
    base = ("New Circuit.c basekv=12.47\n"
            "New Wiredata.w Rac=0.1 GMRac=0.01 radius=0.02 Runits=km GMRunits=m radunits=m\n"
            "New LineGeometry.g nconds=2 nphases=1 units=m cond=1 wire=w x=0 h=10 cond=1 x=0.5 cond=2 wire=w x=1 h=10\n")
    model = _read(tmp_path, base)
    g = model.list_by_class(schema.Linegeometry)[0]
    assert (g.units, g.xs, g.hs) == ("m", [0.5, 1.0], [10.0, 10.0])

    with pytest.raises(DssParseError, match="cond="):
        _read(tmp_path, base + "Edit LineGeometry.g cond=2 x=2\n")
    with pytest.raises(DssParseError, match="missing x"):
        _read(tmp_path, "New LineGeometry.g2 nconds=2 nphases=1 cond=1 wire=w x=0 h=10 cond=2 wire=w h=10\n")


# ---------------------------------------------------------------------------
# Importer regressions
# ---------------------------------------------------------------------------

def test_linespacing_detailed_flag(tmp_path):
    ok = _read(tmp_path, "New LineSpacing.s nconds=3 nphases=3 x=[-1 0 1] h=[10 10 10] units=m detailed=Yes\n")
    assert geometry.map_linespacing(ok).statements

    bad = _read(tmp_path, "New LineSpacing.s nconds=3 nphases=3 x=[-1 0 1] h=[10 10 10] units=m detailed=No\n")
    with pytest.raises(ValueError, match="detailed=No"):
        geometry.map_linespacing(bad)


def test_regcontrol_tapnum_zero_and_non_controlled_fixed_tap_raise(tmp_path):
    base = ("New Circuit.c basekv=12.47\n"
            "New Transformer.t phases=3 windings=2 buses=[sourcebus b2] kVs=[12.47 12.47] kVAs=[500 500]\n")
    with pytest.raises(ValueError, match="TapNum"):
        regcontrol.map_regcontrol(_read(tmp_path, base + "New RegControl.rc transformer=t winding=2 TapNum=0\n"))

    bad_tap = ("New Circuit.c basekv=12.47\n"
               "New Transformer.t phases=3 windings=2 buses=[sourcebus b2] kVs=[12.47 12.47] kVAs=[500 500] "
               "taps=[1.05 1.025]\n"
               "New RegControl.rc transformer=t winding=2\n")
    with pytest.raises(ValueError, match="fixed non-1 tap"):
        regcontrol.map_regcontrol(_read(tmp_path, bad_tap))


def test_reactive_power_and_load_kva_edge_cases(tmp_path):
    assert injection.reactive_power(-50.0, 0.9) == pytest.approx(-50.0 * math.tan(math.acos(0.9)))
    with pytest.raises(ValueError, match="power factor"):
        injection.reactive_power(50.0, 0.0)
    assert load.power_from_kva(100.0, 0.0) == pytest.approx((0.0, 100.0))

    bad_load = _read(tmp_path, "New Circuit.c basekv=12.47\nNew Load.l1 bus1=sourcebus kV=12.47 kVA=100 kvar=20\n")
    site = dss_to_cimtbl.site(bad_load)
    with pytest.raises(ValueError, match="kVA with kvar"):
        load.map_load(bad_load, site.buses, site.feeder)


def test_loadshape_normalize_then_save_keeps_normalization(tmp_path):
    model = _read(tmp_path, "New Circuit.c basekv=12.47\n"
                            "New LoadShape.ls npts=2 interval=1 mult=[2 4] action=normalize action=DblSave\n"
                            "New Load.l1 bus1=sourcebus kV=12.47 kW=10 yearly=ls\n")
    v1, _ = loadshape.shape_points(model)
    assert v1["ls_ls"] == pytest.approx([0.5, 1.0])


def test_linecode_default_nphases_and_line_phases_validation(tmp_path):
    model = _read(tmp_path, "New Circuit.c basekv=12.47\n"
                            "New LineCode.lc r1=0.1 x1=0.2 r0=0.3 x0=0.6 C1=3.4 C0=1.6 units=km\n"
                            "New Line.l1 bus1=sourcebus.1.2.3.0 bus2=b2.1.2.3.0 linecode=lc length=1 units=km\n")
    doc = linecode.map_linecode(model, base_frequency=60.0)
    assert doc.statements
    site = dss_to_cimtbl.site(model)
    assert line.map_line(model, site.buses, site.feeder, base_frequency=60.0).statements

    bad_extra = _read(tmp_path, "New Circuit.c basekv=12.47\n"
                                "New Line.l1 bus1=sourcebus.1.2 bus2=b2.1.2 phases=1 r1=0.1 x1=0.2 length=1 units=km\n")
    site2 = dss_to_cimtbl.site(bad_extra)
    with pytest.raises(ValueError, match="gives 2 nodes for 1 phase"):
        line.map_line(bad_extra, site2.buses, site2.feeder, base_frequency=60.0)

    bad_dup = _read(tmp_path, "New Circuit.c basekv=12.47\n"
                              "New Line.l1 bus1=sourcebus.2.2 bus2=b2.2.2 phases=2 r1=0.1 x1=0.2 length=1 units=km\n")
    site3 = dss_to_cimtbl.site(bad_dup)
    with pytest.raises(ValueError, match="repeats a phase node"):
        line.map_line(bad_dup, site3.buses, site3.feeder, base_frequency=60.0)


def test_vsource_partial_isc_zero_x1r1_and_node4(tmp_path):
    with pytest.raises(ValueError, match="only part of Isc3, Isc1"):
        vsource.impedance_group(schema.Vsource(name="s", Isc3=1000.0))
    z = vsource.thevenin_from_short_circuit(12.47, 1000.0, 1000.0, 0.0, 0.0)
    assert z.x1 == 0.0 and z.r1 > 0
    with pytest.raises(ValueError, match="only a 3-phase source"):
        vsource._phases(schema.Vsource(name="s", phases=1, bus1="src.4"))


def test_regulator_grounded_bus01_and_ungrounded_3ph(tmp_path):
    model = _read(tmp_path, "New Circuit.c basekv=7.2 phases=1 bus1=src.1.0\n"
                            "New Transformer.r1 phases=1 windings=2 buses=[src.0.1 b2.0.1] kVs=[7.2 7.2] kVAs=[100 100]\n"
                            "New RegControl.rc1 transformer=r1 winding=2\n")
    site = dss_to_cimtbl.site(model)
    doc = transformer.map_transformer(model, site.buses, site.feeder)
    auto_ends = [s for s in doc.statements if getattr(s, "cim_class", None) == "AutoTransformerEnd"][0]
    grounded_idx = [c.name for c in auto_ends.columns].index("grounded")
    assert all(row.cells[grounded_idx] == "true" for row in auto_ends.rows)

    model3 = _read(tmp_path, "New Circuit.c basekv=12.47 phases=3 bus1=src\n"
                             "New Transformer.r3 phases=3 windings=2 buses=[src.1.2.3.4 b2.1.2.3.4] "
                             "kVs=[12.47 12.47] kVAs=[500 500]\n"
                             "New RegControl.rc3 transformer=r3 winding=2\n")
    site3 = dss_to_cimtbl.site(model3)
    doc3 = transformer.map_transformer(model3, site3.buses, site3.feeder)
    auto_ends3 = [s for s in doc3.statements if getattr(s, "cim_class", None) == "AutoTransformerEnd"][0]
    grounded_idx3 = [c.name for c in auto_ends3.columns].index("grounded")
    assert all(row.cells[grounded_idx3] == "false" for row in auto_ends3.rows)


def test_capcontrol_spacing_line_and_terminal_validation(tmp_path):
    model = _read(tmp_path, "New Circuit.c basekv=12.47\n"
                            "New Wiredata.w Rac=0.1 GMRac=0.01 radius=0.02 Runits=km GMRunits=m radunits=m\n"
                            "New LineSpacing.sp nconds=1 nphases=1 x=[0] h=[10] units=m\n"
                            "New Line.l1 bus1=sourcebus.1 bus2=b2.1 spacing=sp wires=[w] length=100 units=m\n"
                            "New Capacitor.c1 bus1=b2.1 phases=1 kV=7.2 kvar=100\n"
                            "New CapControl.cc1 element=Capacitor.c1 terminal=2 capacitor=c1 type=voltage\n")
    site = dss_to_cimtbl.site(model)
    assert capcontrol._line_phase_count(model.list_by_class(schema.Line)[0], model) == 1
    with pytest.raises(ValueError, match="terminal=2 on shunt Capacitor"):
        capcontrol.map_capcontrol(model, site.buses)


def test_buscoords_case_insensitive_and_none_guard(tmp_path):
    model = _read(tmp_path, "New Circuit.c basekv=12.47 bus1=SourceBus\n")
    model.add_to_graph(schema.Buscoords(name="SourceBus", x=10.0, y=20.0, geographic=False))
    net = cimtbl_to_cim(DssImporter("c").to_cimtbl(model))
    doc = buscoords.map_buscoords(model, net)
    assert doc.statements

    bad = _read(tmp_path, "New Circuit.c basekv=12.47 bus1=SourceBus\n")
    bad.add_to_graph(schema.Buscoords(name="SourceBus", x=None, y=20.0, geographic=False))
    with pytest.raises(ValueError, match="x and y must both be set"):
        buscoords.map_buscoords(bad, net)


def test_pvsystem_hysteresis_fails_in_to_cimtbl(tmp_path):
    model = _read(tmp_path, "New Circuit.c basekv=12.47\n"
                            "New LoadShape.s npts=1 interval=1 mult=[0.15]\n"
                            "New PVSystem.pv bus1=sourcebus kV=12.47 kVA=100 Pmpp=100 %Cutout=10 %Cutin=20 yearly=s\n")
    with pytest.raises(ValueError, match="between %Cutout"):
        DssImporter("c").to_cimtbl(model)


# ---------------------------------------------------------------------------
# Exporter regressions
# ---------------------------------------------------------------------------

def test_exporter_wire_rac50_support():
    names = Names("name")
    w = cim.OverheadWireInfo(mRID="w1", name="w1", rAC50=cim.ResistancePerLength(0.2, "ohm/m"),
                             gmr=cim.Length(0.01, "m"), radius=cim.Length(0.02, "m"))
    rec = exp_wire._record(w, names)
    assert rec.Rac == pytest.approx(0.2)

    w_both = cim.OverheadWireInfo(mRID="w2", name="w2", rAC25=cim.ResistancePerLength(0.18, "ohm/m"),
                                  rAC50=cim.ResistancePerLength(0.2, "ohm/m"),
                                  gmr=cim.Length(0.01, "m"), radius=cim.Length(0.02, "m"))
    with pytest.raises(ValueError, match="both rAC25 and rAC50"):
        exp_wire._record(w_both, names)


def test_exporter_shape_registry_sanitization_and_collision():
    names = Names("name")
    reg = exp_loadshape.ShapeRegistry()
    g1 = cim.ConformLoadGroup(mRID="g1", name="curve 1")
    g2 = cim.ConformLoadGroup(mRID="g2", name="curve_1")
    g3 = cim.ConformLoadGroup(mRID="g3", name="curve_1_2")
    n1, _ = reg.claim(names, g1, 3600.0, [1.0])
    n2, _ = reg.claim(names, g2, 3600.0, [0.5])
    n3, _ = reg.claim(names, g3, 3600.0, [0.25])
    assert len({n1.lower(), n2.lower(), n3.lower()}) == 3


def test_exporter_linegeometry_sub_mm_offset_name():
    cfg = cim.WireConfiguration(mRID="wc_g", name="g")
    assert geometry_name(cfg, 0.0001, Names("name")) == "g"
    assert geometry_name(cfg, -0.0001, Names("name")) == "g"


def test_exporter_waiting_storage_positive_p_raises(tmp_path):
    model = _read(tmp_path, "New Circuit.c basekv=12.47\n"
                            "New Storage.s1 bus1=sourcebus kV=12.47 kWrated=50 kWhrated=100 State=idling\n")
    net = dss_to_cim(model, name="c")
    pec = next(iter(net.graph[cim.PowerElectronicsConnection].values()))
    # Generation sign p > 0 means load sign p < 0: set CIM p = -10 kW while state is waiting
    pec.p = cim.ActivePower(-10.0, "kW")
    with pytest.raises(ValueError, match="waiting with p"):
        DssExporter().to_model(net)


def test_exporter_ungrounded_transformer_rground_raises(tmp_path):
    model = _read(tmp_path, "New Circuit.c basekv=12.47\n"
                            "New Transformer.t phases=3 windings=2 buses=[sourcebus b2] kVs=[12.47 0.48] kVAs=[500 500]\n")
    net = dss_to_cim(model, name="c")
    end = next(iter(net.graph[cim.PowerTransformerEnd].values()))
    end.grounded = False
    end.rground = cim.Resistance(5.0, "ohm")
    with pytest.raises(ValueError, match="not a grounded wye"):
        DssExporter().to_model(net)

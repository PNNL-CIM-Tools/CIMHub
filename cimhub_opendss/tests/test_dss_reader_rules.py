"""The reader's command semantics and fail-fast rules (DSS_REWRITE_PLAN.md section 3.4)."""

from __future__ import annotations

import logging

import opendssdirect as dss
import pytest

from cimhub_opendss.dss_reader import (DSS_COMMANDS, DSS_OPTIONS, DssParseError, DssReader, dss_command, dss_defaults,
                                       dss_option)
from cimhub_opendss import dss_name_map
from cimhub_opendss.schema import opendss_schema as schema

from conftest import ENGINE_UNIT, clear_engine, compile_deck


def read(tmp_path, text: str, name: str = "deck.dss"):
    deck = tmp_path / name
    deck.write_text(text)
    return DssReader(deck).read_all()


def only(model, cls):
    [obj] = model.list_by_class(cls)
    return obj


def test_second_new_is_applied_as_an_edit(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        model = read(tmp_path, "New Load.a bus1=b kW=10 kvar=2\nNew Load.A kW=20\nNew Load.a kW=30\n")
    load = only(model, schema.Load)
    assert (load.name, load.kW, load.kvar) == ("a", 30.0, 2.0)
    assert len([r for r in caplog.records if "applied as an edit" in r.message]) == 1


def test_edit_changes_the_object_case_insensitively(tmp_path):
    model = read(tmp_path, "New Load.a bus1=b kW=10\nEdit Load.A kW=20\nLoad.a.kvar=3\n")
    assert (only(model, schema.Load).kW, only(model, schema.Load).kvar) == (20.0, 3.0)


def test_edit_of_an_undefined_object_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"Load.x: Edit of an object no New defines in .* at line 1"):
        read(tmp_path, "Edit Load.x kW=20\n")


def test_like_copies_the_unset_slots(tmp_path):
    model = read(tmp_path, "New Linecode.a nphases=1 r1=0.1 x1=0.2\nNew Linecode.b like=a x1=0.3\n")
    [b] = [code for code in model.list_by_class(schema.Linecode) if code.name == "b"]
    assert (b.nphases, b.r1, b.x1) == (1, 0.1, 0.3)


def test_like_of_an_undefined_object_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"like='a': no object of that name is defined before it"):
        read(tmp_path, "New Linecode.b like=a x1=0.3\nNew Linecode.a r1=0.1\n")


def test_unknown_class_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"unknown DSS class 'Widget'"):
        read(tmp_path, "New Widget.w size=1\n")


def test_unknown_property_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"unknown property 'colour' on Load"):
        read(tmp_path, "New Load.a bus1=b colour=red\n")


@pytest.mark.parametrize("text, cls, slot, expected", [
    ("New Load.a bus1=b Vmin=0.9", schema.Load, "Vminpu", 0.9),  # first match in DSS order, not Vminnorm
    ("New Wiredata.w GMR=0.01", schema.Wiredata, "GMRac", 0.01),
    ("New Transformer.t phases=1 ppm=5", schema.Transformer, "ppm_antifloat", 5.0),
])
def test_abbreviated_property_takes_the_first_in_dss_order(tmp_path, text, cls, slot, expected):
    assert getattr(only(read(tmp_path, text + "\n"), cls), slot) == expected


def test_unknown_enum_value_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"conn='zag': 'zag' is not one of"):
        read(tmp_path, "New Load.a bus1=b conn=zag\n")


def test_set_keeps_the_circuit_options_only(tmp_path):
    model = read(tmp_path, "Set voltagebases=[115 4.16 0.48]\nSet defaultbasefreq=50 maxiterations=80\n"
                           "Set mode=snapshot\nSet voltagebases=[115 4.16]\n")
    options = only(model, schema.Options)
    assert (options.voltagebases, options.defaultbasefreq) == ([115.0, 4.16], 50.0)


def test_dss_options_match_the_engine():
    engine = [dss.Executive.Option(i).lower() for i in range(1, dss.Executive.NumOptions() + 1)]
    assert list(DSS_OPTIONS) == engine


@pytest.mark.parametrize("word, option", [
    ("voltagebase", "voltagebases"), ("DefaultBaseFreq", "defaultbasefrequency"), ("earth", "earthmodel"),
    ("e", "element"), ("basefrequency", "basefrequency"), ("colour", None),
])
def test_a_set_option_is_the_first_option_it_abbreviates(word, option):
    assert dss_option(word) == option


def test_abbreviated_set_options_are_kept(tmp_path):
    options = only(read(tmp_path, "Set voltagebase=[12.47 0.48] defaultbase=50 earth=deri\n"), schema.Options)
    assert (options.voltagebases, options.defaultbasefreq, str(options.earthmodel).lower()) == \
        ([12.47, 0.48], 50.0, "deri")


def test_an_unknown_set_option_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"Set colour: no DSS option has that name"):
        read(tmp_path, "Set colour=red\n")


@pytest.mark.parametrize("word", ["basefrequency", "basefreq", "base"])
def test_set_basefrequency_raises(tmp_path, word):
    # the engine gives the new frequency only to objects defined after it, so the deck may hold two base frequencies
    with pytest.raises(DssParseError, match=rf"Set {word}: not read.*set defaultbasefreq before New Circuit"):
        read(tmp_path, f"Set {word}=50\n")


def test_batchedit_changes_every_matching_object(tmp_path):
    model = read(tmp_path, "New Load.a1 bus1=b kW=1\nNew Load.a2 bus1=b kW=2\nNew Load.c bus1=b kW=3\n"
                           "BatchEdit Load.a.* model=5\n")
    models = {load.name: load.model and load.model.text for load in model.list_by_class(schema.Load)}
    assert models == {"a1": "ConstantI", "a2": "ConstantI", "c": None}


def test_batchedit_matching_nothing_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"BatchEdit pattern 'z.\*' matches no object"):
        read(tmp_path, "New Load.a bus1=b kW=1\nBatchEdit Load.z.* model=5\n")


def test_missing_redirect_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"Redirect target not found: .*gone.dss in .* at line 1"):
        read(tmp_path, "Redirect gone.dss\n")


def test_parenthesized_number_and_trailing_comma(tmp_path):
    model = read(tmp_path, "New Regcontrol.r transformer=t vreg=(122)\nNew Loadshape.s npts='1,' mult=[1]\n")
    assert only(model, schema.Regcontrol).vreg == 122.0
    assert only(model, schema.Loadshape).npts == 1


def test_file_array_is_read_from_the_deck_directory(tmp_path):
    (tmp_path / "shape.csv").write_text("0.5\n0.75, 9\n\n1.0\n")
    model = read(tmp_path, "New Loadshape.s npts=3 mult=(file=shape.csv)\n")
    assert only(model, schema.Loadshape).mult == [0.5, 0.75, 1.0]


def test_out_of_range_values_are_kept(tmp_path):
    assert only(read(tmp_path, "New Linecode.lc nphases=4 r1=0.1\n"), schema.Linecode).nphases == 4


def test_new_circuit_is_vsource_source_and_keeps_its_name(tmp_path):
    model = read(tmp_path, "New Circuit.IEEE13Nodeckt basekv=115\nEdit Vsource.source pu=1.05\n")
    source = only(model, schema.Vsource)
    assert (source.name, source.pu, source.bus1) == ("source", 1.05, None)  # bus1 is the mapper's default
    assert only(model, schema.Options).circuit == "IEEE13Nodeckt"


def test_a_second_new_circuit_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"a second New Circuit \(the first is 'a'\)"):
        read(tmp_path, "New Circuit.a\nNew Circuit.b\n")


def test_edit_circuit_raises(tmp_path):
    with pytest.raises(DssParseError, match="only New Circuit is read"):
        read(tmp_path, "New Circuit.a\nEdit Circuit.a basekv=12.47\n")


def test_clear_discards_everything_before_it(tmp_path):
    model = read(tmp_path, "New Circuit.a basekv=69\nNew Load.x bus1=b kW=1\nSet voltagebases=[69]\nClear\n"
                           "New Circuit.b basekv=12.47\n")
    assert only(model, schema.Vsource).basekv == 12.47 and model.list_by_class(schema.Load) == []
    options = only(model, schema.Options)
    assert (options.circuit, options.voltagebases) == ("b", [])


def test_dss_commands_match_the_engine():
    engine = [dss.Executive.Command(i).lower() for i in range(1, dss.Executive.NumCommands() + 1)]
    assert list(DSS_COMMANDS) == engine


@pytest.mark.parametrize("word, command", [
    ("CalcV", "calcvoltagebases"), ("o", "open"), ("M", "m"), ("mo", "more"), ("se", "select"), ("Set", "set"),
    ("Reditect", None),
])
def test_a_command_word_is_the_first_command_it_abbreviates(word, command):
    assert dss_command(word) == command


@pytest.mark.parametrize("line, message", [
    ("Reditect Switches.dss", "unknown DSS command 'Reditect'"),
    ("Disable Load.x", "the disable command changes the model and is not read"),
    ("Select Load.x", "the select command changes the model and is not read"),
    ("   /* an indented block comment is a command, as in the engine", r"unknown DSS command '/\*'"),
])
def test_an_unread_command_raises(tmp_path, line, message):
    with pytest.raises(DssParseError, match=message):
        read(tmp_path, f"New Circuit.c\nNew Load.x bus1=b kW=1\n{line}\n")


def test_skipped_commands_leave_the_model_alone(tmp_path):
    model = read(tmp_path, "New Circuit.c\nCalcV\nsetkvbase b kVLL=0.48\nSolve mode=snap\nPlot daisy\n"
                           "Show Voltage LN Nodes\nExport voltages\n")
    assert only(model, schema.Vsource).name == "source"


def test_more_and_m_continue_the_last_element(tmp_path):
    model = read(tmp_path, "New Load.a bus1=b\nMore kW=10\nM kvar=2\n~ pf=0.9\n")
    assert (only(model, schema.Load).kW, only(model, schema.Load).kvar, only(model, schema.Load).pf) == (10, 2, 0.9)


def test_a_continuation_with_nothing_to_continue_raises(tmp_path):
    with pytest.raises(DssParseError, match="a continuation with no New or Edit before it"):
        read(tmp_path, "Set voltagebases=[12.47]\n~ pu=1.05\n")


BLOCKS_AND_OPENS = """New Circuit.c basekv=12.47
/* a block comment
New Load.inblock bus1=sourcebus kW=1
the end */ New Load.on_the_closing_line bus1=sourcebus kW=1
/* one line */ New Load.on_a_one_line_block bus1=sourcebus kW=1
New Load.after bus1=sourcebus kW=1
New Line.sw1 bus1=sourcebus bus2=b2 switch=y
New Line.sw2 bus1=sourcebus bus2=b3 switch=y
New Line.sw3 bus1=sourcebus bus2=b4 switch=y
Open Line.sw1
Open Line.SW2 terminal=2
o Line.sw3 2
Close Line.sw3 2
"""


def test_block_comments_and_open_match_the_engine(tmp_path):
    deck = tmp_path / "deck.dss"
    deck.write_text(BLOCKS_AND_OPENS)
    model = DssReader(deck).read_all()
    clear_engine()
    dss.Text.Command(f"Redirect [{deck}]")
    assert [load.name for load in model.list_by_class(schema.Load)] == dss.Loads.AllNames()
    engine = []
    for name in dss.Lines.AllNames():
        dss.Circuit.SetActiveElement(f"Line.{name}")
        engine += [f"line.{name} {terminal}" for terminal in (1, 2) if dss.CktElement.IsOpen(terminal, 0)]
    assert [entry.lower() for entry in only(model, schema.Options).open_terminals] == engine


def test_open_of_an_undefined_object_raises(tmp_path):
    with pytest.raises(DssParseError, match="Open of an object no New defines"):
        read(tmp_path, "New Circuit.c\nOpen Line.nope\n")


def test_open_of_one_conductor_raises(tmp_path):
    with pytest.raises(DssParseError, match="open of conductor 3 only is not read"):
        read(tmp_path, "New Circuit.c\nNew Line.l bus1=sourcebus bus2=b\nOpen Line.l 2 3\n")


@pytest.mark.parametrize("units", ["units=ft ~ cond=2 x=1 h=10 units=m", "~ cond=2 x=1 h=10 units=m"])
def test_geometry_positions_in_different_units_raise(tmp_path, units):
    with pytest.raises(DssParseError, match="the cond= blocks give positions in different units"):
        read(tmp_path, f"New LineGeometry.g nconds=2 nphases=1 cond=1 x=0 h=10 {units}\n".replace(" ~ ", "\n~ "))


def test_geometry_units_carry_to_the_next_cond_block(tmp_path):
    model = read(tmp_path, "New LineGeometry.g nconds=2 nphases=1\n~ cond=1 x=0 h=10 units=m\n~ cond=2 x=1 h=9\n")
    geometry = only(model, schema.Linegeometry)
    assert (geometry.units, geometry.xs, geometry.hs) == ("m", [0.0, 1.0], [10.0, 9.0])


POSITIONAL = """New Circuit.c
New Linecode.a nphases=3 r1=0.1 x1=0.2 units=km Normamps=156 {156 1.25 *}
New Linecode.b 3 0.3 0.4
New Linecode.c nphases=3 r1=0.1 x1=0.2 units=km emergamps={2 3 ^ 10 *}
"""


def test_positional_values_match_the_engine(tmp_path):
    # a value with no name goes to the property after the last one named; {...} is RPN
    deck = tmp_path / "deck.dss"
    deck.write_text(POSITIONAL)
    codes = {code.name: code for code in DssReader(deck).read_all().list_by_class(schema.Linecode)}
    clear_engine()
    dss.Text.Command(f"Redirect [{deck}]")
    for name, code in codes.items():
        dss.LineCodes.Name(name)
        assert (code.nphases, code.r1, code.x1) == (dss.LineCodes.Phases(), dss.LineCodes.R1(), dss.LineCodes.X1())
        if code.emergamps is not None:
            assert code.emergamps == dss.LineCodes.EmergAmps()
    assert codes["a"].emergamps == 195 and codes["c"].emergamps == 80


@pytest.mark.parametrize("text, message", [
    ("New Transformer.t phases=1 windings=2 2.4\n", "positional value '2.4' is not read"),
    ("New Linecode.a nphases=3 r1={1 x +}\n", "could not convert"),
    ("New Linecode.a nphases=3 r1={1 +}\n", "stack underflow"),
    ("New Linecode.a like=b 1\n", "past the last property"),
])
def test_unreadable_positional_values_raise(tmp_path, text, message):
    with pytest.raises(DssParseError, match=message):
        read(tmp_path, "New Circuit.c\nNew Linecode.b nphases=3 r1=0.1 x1=0.2\n" + text)


WINDING_SCALARS = [
    "phases=3 windings=2 kVA=750 buses=[src b] kVs=[12.47 0.48]",
    "phases=3 windings=2 wdg=1 bus=src kv=12.47 kva=500 wdg=2 bus=b kv=0.48 kva=300",
    "phases=3 windings=2 buses=[src b] kVs=[12.47 0.48] kVA=750 kVAs=[400 300]",
    "phases=3 windings=3 buses=[src b c] kVs=[12.47 0.48 0.48] kVAs=[900 800 700] wdg=2 kVA=50",
]


@pytest.mark.parametrize("text", WINDING_SCALARS)
def test_winding_scalars_match_the_engine(tmp_path, text):
    # a bare kV/kVA/conn/%R goes to the active winding (the last wdg=, else the last an array set, else 1);
    # on a 2-winding transformer kVA sets both
    xf = only(read(tmp_path, f"New Circuit.c bus1=src\nNew Transformer.t {text}\n"), schema.Transformer)
    clear_engine()
    dss.Text.Command("New Circuit.c bus1=src")
    dss.Text.Command(f"New Transformer.t {text}")
    dss.Transformers.Name("t")
    engine = []
    for winding in range(1, dss.Transformers.NumWindings() + 1):
        dss.Transformers.Wdg(winding)
        engine.append((dss.Transformers.kVA(), dss.Transformers.R(), dss.Transformers.IsDelta()))
    ours = [(float(kva), float(r) if r is not None else 0.2, str(conn).lower() == "delta")
            for kva, r, conn in zip(xf.kVAs or [1000.0] * len(engine), xf.pct_Rs or [None] * len(engine),
                                    [c.text if hasattr(c, "text") else c for c in xf.conns] or ["wye"] * len(engine))]
    assert ours == engine


@pytest.mark.parametrize("text", [
    "phases=3 windings=2 buses=[src b] kVs=[12.47 0.48] kVA=750 %R=0.1 conn=delta",
    "phases=3 windings=3 buses=[src b c] kVs=[12.47 0.48 0.48] wdg=2 %R=0.4",
])
def test_a_winding_left_unset_takes_the_engine_default(tmp_path, text, caplog):
    # an array cannot hold an unset winding; it takes the DSS per-winding default, as the engine does
    with caplog.at_level(logging.WARNING):
        test_winding_scalars_match_the_engine(tmp_path, text)
    assert "unset while another winding's is set" in caplog.text


def test_a_bus_left_unset_raises(tmp_path):
    with pytest.raises(DssParseError, match="buses: winding \\[1\\] unset .* bus has no default"):
        read(tmp_path, "New Circuit.c bus1=src\nNew Transformer.t phases=1 windings=2 wdg=2 bus=b\n")


def test_rdcohms_goes_to_the_active_winding(tmp_path):
    """RdcOhms has no array form in DSS: each value belongs to the winding the last wdg= names."""
    model = read(tmp_path, "New Transformer.t phases=1 windings=2 buses=[a.1 b.1] kVs=[7.2 0.24] kVAs=[25 25]\n"
                           "~ wdg=2 RdcOhms=0.004 wdg=1 RdcOhms=2.1\n")
    [transformer] = model.list_by_class(schema.Transformer)
    assert transformer.RdcOhms == [2.1, 0.004]


def test_rneut_on_a_second_winding_raises(tmp_path):
    """The schema holds one winding's Rneut/Xneut; a second winding's would be lost."""
    with pytest.raises(DssParseError, match=r"Transformer.t: Rneut on winding 2 after winding 1's neutral"):
        read(tmp_path, "New Transformer.t phases=3 windings=2 buses=[a b] kVs=[12.47 4.16] kVAs=[500 500] "
                       "wdg=1 conn=wye Rneut=0 wdg=2 conn=wye Rneut=5\n")


def test_a_malformed_schema_yaml_raises(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("classes: [unclosed\n")
    with pytest.raises(ValueError, match=r"broken.yaml: malformed schema YAML"):
        dss_name_map._load_yaml(path)


def test_invcontrol_modes_are_names(tmp_path):
    control = only(read(tmp_path, "New InvControl.ic Mode=VOLTVAR CombiMode=VV_VW\n"), schema.Invcontrol)
    assert (control.Mode, control.CombiMode) == ("VOLTVAR", "VV_VW")


def test_rdcohms_on_some_windings_only_raises(tmp_path):
    with pytest.raises(DssParseError, match=r"RdcOhms: winding \[1\] unset while another winding's is set"):
        read(tmp_path, "New Transformer.t phases=1 windings=2 buses=[a.1 b.1] kVs=[7.2 0.24] kVAs=[25 25] "
                       "wdg=2 RdcOhms=0.004\n")


# ---------------------------------------------------------------------------
# Engine behaviours the reader follows (ported from the PR #14 audit; each checked against opendssdirect)
# ---------------------------------------------------------------------------

CIRCUIT = "New Circuit.c bus1=src\n"


def coordinates(model) -> dict[str, tuple[float, float]]:
    return {str(row.name): (row.x, row.y) for row in model.list_by_class(schema.Buscoords)}


def test_a_set_with_no_option_name_raises(tmp_path):
    # the engine reads "Set =5" as an unknown parameter; an empty name abbreviates no option
    with pytest.raises(DssParseError, match="no DSS option has that name"):
        read(tmp_path, CIRCUIT + "Set =5\n")


@pytest.mark.parametrize("target", [r"Sub\Lower.dss", "sub/lower.dss", "(Sub/Lower.dss)", "[Sub/Lower.dss]"])
def test_redirect_paths_resolve_as_on_windows(tmp_path, target):
    # backslashes and the () or [] the engine strips; case-insensitive, as the deck's Windows author saw it
    (tmp_path / "Sub").mkdir()
    (tmp_path / "Sub" / "Lower.dss").write_text("New Load.l bus1=src kW=1\n")
    assert [load.name for load in read(tmp_path, CIRCUIT + f"Redirect {target}\n").list_by_class(schema.Load)] == ["l"]


def test_a_relative_master_path_resolves_case_insensitively(tmp_path, monkeypatch):
    (tmp_path / "Sub").mkdir()
    (tmp_path / "Sub" / "Lower.dss").write_text("New Load.l bus1=src kW=1\n")
    (tmp_path / "deck.dss").write_text(CIRCUIT + "Redirect sub/lower.dss\n")
    monkeypatch.chdir(tmp_path)
    assert [load.name for load in DssReader("deck.dss").read_all().list_by_class(schema.Load)] == ["l"]


def test_a_nested_redirect_resolves_against_its_own_folder(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "inner.dss").write_text("Redirect leaf.dss\nMakeBusList\nBusCoords xy.csv\n")
    (tmp_path / "sub" / "leaf.dss").write_text("New Line.leaf bus1=src bus2=b\n")
    (tmp_path / "sub" / "xy.csv").write_text("b, 7, 8\n")
    (tmp_path / "leaf.dss").write_text("New Line.wrong bus1=src bus2=b\n")
    (tmp_path / "xy.csv").write_text("b, 1, 2\n")
    deck = tmp_path / "deck.dss"
    deck.write_text(CIRCUIT + "Redirect sub/inner.dss\n")
    model = DssReader(deck).read_all()
    compile_deck(deck)
    dss.Circuit.SetActiveBus("b")
    assert [line.name for line in model.list_by_class(schema.Line)] == dss.Lines.AllNames() == ["leaf"]
    assert coordinates(model)["b"] == (dss.Bus.X(), dss.Bus.Y()) == (7.0, 8.0)


def test_a_redirect_cycle_raises_and_a_diamond_does_not(tmp_path):
    for name, text in {"b.dss": "Redirect d.dss\n", "c.dss": "Redirect d.dss\n", "d.dss": "! shared\n"}.items():
        (tmp_path / name).write_text(text)
    read(tmp_path, CIRCUIT + "Redirect b.dss\nRedirect c.dss\n")
    (tmp_path / "d.dss").write_text("Redirect b.dss\n")
    with pytest.raises(DssParseError, match="Redirect cycle"):
        read(tmp_path, CIRCUIT + "Redirect b.dss\n")


@pytest.mark.parametrize("line", ["Redirect", "Compile", "BusCoords", "LatLongCoords"])
def test_a_file_command_with_no_path_raises(tmp_path, line):
    with pytest.raises(DssParseError, match="needs a file path"):
        read(tmp_path, CIRCUIT + line + "\n")


def test_a_byte_order_mark_is_skipped(tmp_path):
    (tmp_path / "xy.csv").write_bytes("﻿b, 1, 2\n".encode())
    deck = tmp_path / "deck.dss"
    deck.write_bytes(("﻿" + CIRCUIT + "New Line.l bus1=src bus2=b\nBusCoords xy.csv\n").encode())
    model = DssReader(deck).read_all()
    assert ([line.name for line in model.list_by_class(schema.Line)], coordinates(model)) == (["l"], {"b": (1, 2)})


def test_coordinate_files_apply_in_deck_order_and_clear_drops_them(tmp_path):
    for name, text in {"a.csv": "b, 1, 2\n", "ll.csv": "b, 5, 6\n", "c.csv": "b, 3, 4\n"}.items():
        (tmp_path / name).write_text(text)
    deck = tmp_path / "deck.dss"
    deck.write_text(CIRCUIT + "New Line.l bus1=src bus2=b\nMakeBusList\nBusCoords a.csv\nLatLongCoords ll.csv\n"
                    "BusCoords c.csv\n")
    model = DssReader(deck).read_all()
    compile_deck(deck)
    dss.Circuit.SetActiveBus("b")
    assert coordinates(model)["b"] == (dss.Bus.X(), dss.Bus.Y()) == (3.0, 4.0)
    assert coordinates(read(tmp_path, CIRCUIT + "BusCoords a.csv\nClear\n" + CIRCUIT)) == {}


def test_a_continuation_after_clear_raises(tmp_path):
    # the engine has no circuit after Clear (#301); the reader must not extend the discarded load
    with pytest.raises(DssParseError, match="a continuation with no New or Edit before it"):
        read(tmp_path, CIRCUIT + "New Load.a bus1=src kW=1\nClear\n~ kW=5\n")


def test_a_continuation_extends_a_dotted_edit(tmp_path):
    text = CIRCUIT + "New Line.l1 bus1=src bus2=b\nNew Line.l2 bus1=src bus2=c\nLine.l1.length=5\n~ phases=1\n"
    lines = {line.name: line for line in read(tmp_path, text).list_by_class(schema.Line)}
    clear_engine()
    for command in text.splitlines():
        dss.Text.Command(command)
    for name, line in lines.items():
        dss.Lines.Name(name)
        assert (line.phases or 3) == dss.Lines.Phases()
    assert (lines["l1"].phases, lines["l1"].length) == (1, 5.0)


def test_open_takes_a_quoted_element(tmp_path):
    model = read(tmp_path, CIRCUIT + 'New Line.sw1 bus1=src bus2=b switch=y\nOpen "Line.sw1" 2\n')
    assert only(model, schema.Options).open_terminals == ["Line.sw1 2"]


def test_open_of_terminal_zero_raises(tmp_path):
    # the engine opens terminal 1 instead, silently
    with pytest.raises(DssParseError, match="terminal 0 must be 1 or more"):
        read(tmp_path, CIRCUIT + "New Line.sw1 bus1=src bus2=b switch=y\nOpen Line.sw1 0\n")


@pytest.mark.parametrize("line", ["New", "Edit", "BatchEdit"])
def test_a_bare_element_command_raises(tmp_path, line):
    # the engine raises #263 / #267: Object Type "" not found
    with pytest.raises(DssParseError, match="needs Class.name"):
        read(tmp_path, CIRCUIT + line + "\n")


@pytest.mark.parametrize("text, like", [
    ("New Generator.g bus1=src kW=100 kvar=50 kW=200\n", ""),
    ("New Generator.g3 bus1=src kW=100 kvar=50 kW=200\nNew Generator.g like=g3 kW=300\n", "g3"),
    ("New Generator.g3 bus1=src kW=100 kvar=50\nNew Generator.g like=g3 kW=200\n", "g3"),
])
def test_the_history_replays_to_the_engine_kvar(tmp_path, text, like):
    # every assignment in deck order, like= first with its source's whole history: the engine keeps kvar as a
    # power factor at the kW of the moment
    from cimhub_opendss.importer.cimtbl.generator import dispatched_kvar
    model = read(tmp_path, CIRCUIT + text)
    [generator] = [g for g in model.list_by_class(schema.Generator) if g.name == "g"]
    clear_engine()
    for command in (CIRCUIT + text).splitlines():
        dss.Text.Command(command)
    dss.Text.Command("? Generator.g.kvar")
    assert dispatched_kvar("g", model.assignments(generator)) == pytest.approx(float(dss.Text.Result()))


def test_an_edit_of_linegeometry_conductors_raises(tmp_path):
    # an Edit's cond= block would replace every conductor's position with this one's
    with pytest.raises(DssParseError, match=r"per-conductor properties \(cond=\) on an Edit are not read"):
        read(tmp_path, "New LineGeometry.g nconds=2 nphases=2 cond=1 x=0 h=10 cond=2 x=1 h=10\n"
                       "Edit LineGeometry.g cond=2 x=2\n")


def test_a_missing_array_file_raises_with_its_line(tmp_path):
    with pytest.raises(DssParseError, match=r"no-such\.csv.* at line 2"):
        read(tmp_path, CIRCUIT + "New Loadshape.s npts=2 mult=(file=no-such.csv)\n")


@pytest.mark.parametrize("text, expected", [
    ("windings=3.0 buses=[src b c] kVs=[1 1 1]", 3),
    ("windings={1 2 +} buses=[src b c] kVs=[1 1 1]", 3),
])
def test_a_winding_count_takes_any_number(tmp_path, text, expected):
    assert only(read(tmp_path, CIRCUIT + f"New Transformer.t phases=1 {text}\n"), schema.Transformer).windings == expected


@pytest.mark.parametrize("text", [
    "phases=1 windings=2 buses=[src b] wdg=(2 1 -) bus=b2 kv=2",
    "phases=1 windings=2 buses=[src b] wdg={2 1 -} bus=b2 kv=2",
    "phases=1 windings=2 buses=[src b] wdg=1.0 bus=b2 kv=2",
    "phases=3 windings=2 buses={src b} kvs={12.47 4.16} kvas={500 500}",
    "phases=3 windings=2 buses=[src b] kvs=[{12 2 *} 4.16]",
    "phases=3 windings=2 buses=[src b] kVs=[12.47 4.16] wdg=2 kv={2 2 *}",
])
def test_winding_arrays_match_the_engine(tmp_path, text):
    xf = only(read(tmp_path, CIRCUIT + f"New Transformer.t {text}\n"), schema.Transformer)
    clear_engine()
    dss.Text.Command(CIRCUIT.strip())
    dss.Text.Command(f"New Transformer.t {text}")
    dss.Transformers.Name("t")
    engine_kvs = []
    for winding in range(1, dss.Transformers.NumWindings() + 1):
        dss.Transformers.Wdg(winding)
        engine_kvs.append(dss.Transformers.kV())
    assert [float(kv) for kv in xf.kVs] == pytest.approx(engine_kvs)
    assert [bus.split(".")[0] for bus in xf.buses][1:] == [bus.split(".")[0] for bus in dss.CktElement.BusNames()][1:]


def test_winding_zero_raises(tmp_path):
    with pytest.raises(DssParseError, match="wdg=0"):
        read(tmp_path, CIRCUIT + "New Transformer.t phases=1 windings=2 wdg=0 bus=b2\n")


@pytest.mark.parametrize("text, slot, expected", [
    ('New Load.a bus1="pi" kW=1', "bus1", "pi"),
    ("New Load.a bus1=(1 2 +) kW=1", "bus1", "1 2 +"),
    ("New Load.a bus1=src kW=1\nLoad.a.kW={2 3 *}", "kW", 6.0),
    ("New Load.a bus1=src kW=1\nLoad.a.kW=(2 3 *)", "kW", 6.0),
])
def test_rpn_is_evaluated_on_numbers_only(tmp_path, text, slot, expected):
    load = only(read(tmp_path, CIRCUIT + text + "\n"), schema.Load)
    clear_engine()
    for command in (CIRCUIT + text).splitlines():
        dss.Text.Command(command)
    dss.Text.Command(f"? Load.a.{slot}")
    engine = dss.Text.Result()
    assert getattr(load, slot) == expected == (float(engine) if isinstance(expected, float) else engine)


def test_rpn_elements_of_an_array_match_the_engine(tmp_path):
    text = "New Loadshape.s npts=3 mult=[1 {2 3 *} (2 2 +)]"
    shape = only(read(tmp_path, CIRCUIT + text + "\n"), schema.Loadshape)
    clear_engine()
    dss.Text.Command(CIRCUIT.strip())
    dss.Text.Command(text)
    dss.LoadShape.Name("s")
    assert shape.mult == list(dss.LoadShape.PMult()) == [1.0, 6.0, 4.0]


def test_a_bad_batchedit_pattern_raises_with_its_line(tmp_path):
    with pytest.raises(DssParseError, match=r"BatchEdit pattern '\(' is not a regular expression.* at line 3"):
        read(tmp_path, CIRCUIT + "New Load.a bus1=src kW=1\nBatchEdit Load.( kW=3\n")


@pytest.mark.parametrize("text", [
    "nconds=2 nphases=2 units=m cond=1 x=0 h=10 cond=2 x=1 h=10",
    "nconds=2 nphases=2 cond=1 x=0 h=10 units=m cond=2 x=1 h=10",
    "nconds=2 nphases=2 cond=1 x=0 cond=2 x=1 h=9 cond=1 h=10",
    "nconds=2 nphases=2 cond=1 x=-1 h=10 cond=2 h=10",
    "nconds=2 nphases=2 cond=1 h=10 cond=2 x=1 h=10",
    "nconds=1 nphases=1 cond=1 h=10",
])
def test_geometry_conductors_match_the_engine(tmp_path, text):
    """A units= before cond=1 is the first conductor's; a repeated cond= block adds to that conductor. A conductor
    with no x is at x=0: ``nconds=`` puts every conductor at (0, 0) (LineGeometry.pas:1075-1076), and the engine gave
    Xcoords ``[-1, 0]``, ``[0, 1]`` and ``[0]`` for the last three."""
    geometry = only(read(tmp_path, CIRCUIT + f"New LineGeometry.g {text}\n"), schema.Linegeometry)
    clear_engine()
    dss.Text.Command(CIRCUIT.strip())
    dss.Text.Command(f"New LineGeometry.g {text}")
    dss.LineGeometries.Name("g")
    assert (geometry.xs, geometry.hs) == (dss.LineGeometries.Xcoords(), dss.LineGeometries.Ycoords())
    assert {ENGINE_UNIT[unit] for unit in dss.LineGeometries.Units()} == {str(geometry.units or "ft").lower()}


def test_a_geometry_conductor_with_no_height_raises(tmp_path):
    """The engine puts it at h=0 (LineGeometry.pas:1076; Ycoords ``[0, 10]`` for this deck), on the ground; the
    reader raises rather than guess that the deck meant it."""
    with pytest.raises(DssParseError, match=r"LineGeometry.g: cond=1 has no h .* at line 1"):
        read(tmp_path, "New LineGeometry.g nconds=2 nphases=2 cond=1 x=1 cond=2 x=2 h=10\n")


def test_geometry_units_before_cond_count_for_the_mixed_check(tmp_path):
    with pytest.raises(DssParseError, match="the cond= blocks give positions in different units"):
        read(tmp_path, "New LineGeometry.g nconds=2 nphases=2 units=m cond=1 x=0 h=10 cond=2 x=1 h=10 units=ft\n")


@pytest.mark.parametrize("function", ["rollup", "rolldn"])
def test_rpn_rollup_and_rolldn_raise(tmp_path, function):
    with pytest.raises(DssParseError, match=f"RPN {function} is not supported"):
        read(tmp_path, CIRCUIT + f"New Load.a bus1=src kW=(1 2 3 {function})\n")


# ---------------------------------------------------------------------------
# Decisions 2, 3, 4 and 6 of the PR #14 port (each probed in opendssdirect 0.9.4)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("line", [
    "New Load.l bus1=a kW= kvar=5",
    "Edit Load.base kW= kvar=5",
    "New Transformer.t phases=3 windings=2 buses=[a b] kvs= kvas=[100 100]",
])
def test_a_blank_after_equals_takes_the_next_word_and_raises_as_the_engine_does(tmp_path, line):
    """A blank after ``=`` is no empty value: the parser skips it and reads the next word as the value
    (Parser/ParserDel.pas:434-439). Each of these raises ``(#303) ... Invalid inline math entry`` in the engine
    (``kW`` is given the text ``kvar``)."""
    with pytest.raises(DssParseError, match=r"in .*deck\.dss at line 3"):
        read(tmp_path, CIRCUIT + "New Load.base bus1=a kW=10 kvar=3\n" + line + "\n")


TWO_WINDINGS = "New Transformer.t phases=3 windings=2 buses=[a b] kVs=[12.47 4.16] kVAs=[500 400] %Rs=[1 2]\n"
THREE_WINDINGS = ("New Transformer.t phases=3 windings=3 buses=[a b c] kVs=[12.47 4.16 0.48] kVAs=[500 400 300] "
                  "%Rs=[1 2 3]\n")


def _windings(record) -> list[tuple[float, float, float, float, bool]]:
    """``(kV, kVA, tap, %R, delta)`` per winding of a read Transformer or XfmrCode; an unset array is the DSS
    default."""
    defaults = dss_defaults(type(record))
    count = record.windings or defaults["windings"]

    def column(values, scalar):
        return list(values) if values else [defaults[scalar]] * count

    return [(float(kv), float(kva), float(tap), float(r), str(getattr(conn, "text", conn)).lower() == "delta")
            for kv, kva, tap, r, conn in zip(column(record.kVs, "kV"), column(record.kVAs, "kVA"),
                                             column(record.taps, "tap"), column(record.pct_Rs, "pct_R"),
                                             column(record.conns, "conn"))]


def _engine_windings(name: str) -> list[tuple[float, float, float, float, bool]]:
    dss.Transformers.Name(name)
    windings = []
    for number in range(1, dss.Transformers.NumWindings() + 1):
        dss.Transformers.Wdg(number)
        windings.append((dss.Transformers.kV(), dss.Transformers.kVA(), dss.Transformers.Tap(), dss.Transformers.R(),
                         dss.Transformers.IsDelta()))
    return windings


TAPPED = ("New Transformer.t phases=3 windings=2 buses=[a b] conns=[delta wye] kVs=[12.47 4.16] kVAs=[500 400] "
          "%Rs=[1 2] taps=[1.05 1.02]")
#: the per-winding values the engine resets ``windings=`` to (kV, kVA, tap, %R, delta)
FRESH = (12.47, 1000, 1, 0.2, False)


@pytest.mark.parametrize("text, expected", [
    # kVA on winding 1 sets every winding, and on a 2-winding transformer either winding's sets both
    # (Transformer.pas:571-578)
    (TWO_WINDINGS + "Edit Transformer.t kva=600\n",
     [(12.47, 600, 1, 1, False), (4.16, 600, 1, 2, False)]),
    (TWO_WINDINGS + "Edit Transformer.t wdg=1\nEdit Transformer.t kva=600\n",
     [(12.47, 600, 1, 1, False), (4.16, 600, 1, 2, False)]),
    (THREE_WINDINGS + "Edit Transformer.t wdg=1 kVA=50\n",
     [(12.47, 50, 1, 1, False), (4.16, 50, 1, 2, False), (0.48, 50, 1, 3, False)]),
    # IEEE34's regulator tap: winding 2 only, winding 1 keeps the default tap
    ("New Transformer.t phases=1 windings=2 buses=[a.1 b.1] kVs=[14.376 14.376] kVAs=[1666 1666]\n"
     "Transformer.t.wdg=2 Tap=(0.00625 12 * 1 +)\n",
     [(14.376, 1666, 1, 0.2, False), (14.376, 1666, 1.075, 0.2, False)]),
    # an array, however short, leaves the last winding active (Transformer.pas:731-737)
    (THREE_WINDINGS + "Edit Transformer.t kv=5\n",
     [(12.47, 500, 1, 1, False), (4.16, 400, 1, 2, False), (5, 300, 1, 3, False)]),
    (THREE_WINDINGS + "Edit Transformer.t wdg=1\nEdit Transformer.t kVs=[5]\nEdit Transformer.t kv=7\n",
     [(5, 500, 1, 1, False), (4.16, 400, 1, 2, False), (7, 300, 1, 3, False)]),
    # a short array keeps the windings it leaves out ("Ignore omitted values", Transformer.pas:796-801)
    (TAPPED + "\nEdit Transformer.t taps=[0.9]\n",
     [(12.47, 500, 0.9, 1, True), (4.16, 400, 1.02, 2, False)]),
    # wdg= stays active across Edit, ~ and dotted edits of the same object
    (THREE_WINDINGS + "Edit Transformer.t wdg=2\nEdit Transformer.t kv=5\n",
     [(12.47, 500, 1, 1, False), (5, 400, 1, 2, False), (0.48, 300, 1, 3, False)]),
    (THREE_WINDINGS + "Edit Transformer.t wdg=2\n~ kv=5 %R=0.7\n",
     [(12.47, 500, 1, 1, False), (5, 400, 1, 0.7, False), (0.48, 300, 1, 3, False)]),
    (THREE_WINDINGS + "Transformer.t.wdg=1\nTransformer.t.kv=5\n",
     [(5, 500, 1, 1, False), (4.16, 400, 1, 2, False), (0.48, 300, 1, 3, False)]),
    # another transformer's wdg= does not move this one's
    (THREE_WINDINGS + "Edit Transformer.t wdg=1\nNew Transformer.u phases=3 windings=2 buses=[x y] wdg=2 kv=1\n"
     "Edit Transformer.t kv=5\n",
     [(5, 500, 1, 1, False), (4.16, 400, 1, 2, False), (0.48, 300, 1, 3, False)]),
    # a New's last wdg= stays active
    ("New Transformer.t phases=3 windings=2 wdg=1 bus=a kv=12.47 wdg=2 bus=b kv=4.16\nEdit Transformer.t tap=1.05\n",
     [(12.47, 1000, 1, 0.2, False), (4.16, 1000, 1.05, 0.2, False)]),
    # windings= makes every winding anew, even at the same count (Transformer.pas:985-994, SetNumWindings)
    (TAPPED + "\nEdit Transformer.t windings=2\n", [FRESH, FRESH]),
    (TAPPED.replace("windings=2 ", "") + " windings=2\n", [FRESH, FRESH]),
])
def test_per_winding_edits_go_to_the_active_winding(tmp_path, text, expected):
    """The engine keeps each transformer's active winding across commands (``ActiveWinding`` is a field of the
    object, set to 1 when it is created, Transformer.pas:924), and an edit's kV, kVA, tap or %R goes to it.
    ``expected`` is what opendssdirect 0.9.4 gave for each deck: ``(kV, kVA, tap, %R, delta)`` per winding."""
    model = read(tmp_path, CIRCUIT + text)
    [transformer] = [record for record in model.list_by_class(schema.Transformer) if record.name == "t"]
    compile_deck(tmp_path / "deck.dss")
    assert _engine_windings("t") == [pytest.approx(winding) for winding in expected]
    assert _windings(transformer) == [pytest.approx(winding) for winding in expected]


def test_per_winding_edits_of_an_xfmrcode_go_to_its_active_winding(tmp_path):
    """The engine gave ``[(12.47, 500, 1.05, 1), (5, 400, 1, 2), (0.48, 300, 1, 3)]`` (kV, kVA, tap, %R) for the
    transformer that uses the code (XfmrCode.pas:273, 319)."""
    model = read(tmp_path, CIRCUIT + "New XfmrCode.x phases=3 windings=3 kVs=[12.47 4.16 0.48] kVAs=[500 400 300] "
                                     "%Rs=[1 2 3]\nEdit XfmrCode.x wdg=2\nEdit XfmrCode.x kv=5\nXfmrCode.x.wdg=1\n"
                                     "XfmrCode.x.tap=1.05\nNew Transformer.t XfmrCode=x buses=[a b c]\n")
    compile_deck(tmp_path / "deck.dss")
    expected = [(12.47, 500, 1.05, 1, False), (5, 400, 1, 2, False), (0.48, 300, 1, 3, False)]
    assert _engine_windings("t") == [pytest.approx(winding) for winding in expected]
    assert _windings(only(model, schema.Xfmrcode)) == [pytest.approx(winding) for winding in expected]


def test_a_neutral_edit_keeps_the_winding_of_the_first(tmp_path):
    """The engine resets Rneut to -1 (its default) on ``windings=``; the reader leaves it unset, which is that
    default."""
    model = read(tmp_path, TWO_WINDINGS + "Edit Transformer.t wdg=1 Rneut=0\nEdit Transformer.t Xneut=0.4\n")
    transformer = only(model, schema.Transformer)
    assert (transformer.wdg, transformer.Rneut, transformer.Xneut) == (1, 0.0, 0.4)
    with pytest.raises(DssParseError, match=r"Rneut on winding 2 after winding 1's neutral.* at line 3"):
        read(tmp_path, TWO_WINDINGS + "Edit Transformer.t wdg=1 Rneut=0\nEdit Transformer.t wdg=2 Rneut=5\n")
    model = read(tmp_path, TWO_WINDINGS + "Edit Transformer.t wdg=2 Rneut=5\nEdit Transformer.t windings=2\n")
    transformer = only(model, schema.Transformer)
    assert (transformer.wdg, transformer.Rneut) == (None, None)


def test_a_winding_past_the_last_raises(tmp_path):
    """The engine raises ``(#2020031) Transformer.t.Wdg: Invalid value (4).`` (Transformer.pas:624)."""
    with pytest.raises(DssParseError, match=r"wdg=4: the windings are 1 to 3 .* at line 3"):
        read(tmp_path, CIRCUIT + THREE_WINDINGS + "Edit Transformer.t wdg=4 kv=9\n")


def test_a_per_winding_batchedit_raises(tmp_path):
    """The engine sets each matched transformer's own active winding; the reader does not follow that."""
    with pytest.raises(DssParseError, match=r"BatchEdit of per-winding properties .* at line 2"):
        read(tmp_path, TWO_WINDINGS + "BatchEdit Transformer..* kv=5\n")


# ---------------------------------------------------------------------------
# W17 matrices in rows, W16 empty values, M4 command boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("matrix", [
    "[1 2 3 | 2 4 5 | 3 5 6]",  # full
    "[1 | 2 4 | 3 5 6]",  # lower triangle
    "[1 | 2 4 5 | 3 5 6]",  # mixed
    "[1 2 9 | 2 4 9 | 3 5 6]",  # a later row overwrites the upper values an earlier one wrote
])
def test_a_matrix_in_rows_is_its_lower_triangle_as_the_engine_reads_it(tmp_path, matrix):
    """``ParseAsSymMatrix`` (Parser/ParserDel.pas:817-829) writes M[i,j] and M[j,i] for each value j of row i, later
    rows over earlier ones; the engine gave Rmatrix ``[1 2 3 | 2 4 5 | 3 5 6]`` for each of these."""
    code = only(read(tmp_path, CIRCUIT + f"New Linecode.lc nphases=3 rmatrix={matrix} xmatrix=[1 |0 1 |0 0 1]\n"),
                schema.Linecode)
    compile_deck(tmp_path / "deck.dss")
    dss.LineCodes.Name("lc")
    full = dss.LineCodes.Rmatrix()
    assert code.rmatrix == [full[row * 3 + column] for row in range(3) for column in range(row + 1)]


def test_a_matrix_row_shorter_than_its_number_raises(tmp_path):
    """The engine reads ``[1 | 2 | 3 5 6]`` with M[2,2]=0: a row that stops short leaves an earlier row's value or 0
    (Parser/ParserDel.pas:822-826)."""
    with pytest.raises(DssParseError, match=r"rmatrix=.*matrix row 2 has 1 value; it needs 2 or more .* at line 2"):
        read(tmp_path, CIRCUIT + "New Linecode.lc nphases=3 rmatrix=[1 | 2 | 3 5 6]\n")


@pytest.mark.parametrize("line", [
    "New Load.l bus1=a kW=",
    'New Load.l bus1=a kW=""',
    "New Load.l bus1=a kW=''",
    "New Load.l bus1=a kW=()",
    "New Load.l bus1=a kW=[]",
    "New Load.l bus1=a kW={}",
    'New Load.l bus1=a kW="" kvar=5',
    "New Load.l kW=10 bus1=",
    "New Load.l bus1=a yearly=",
    "New Load.l bus1=a model=",
    'New Line.ln bus1=a bus2=b linecode=""',
    "New Transformer.t phases=3 windings=2 buses=[a b] kvs=[]",
    "Edit Load.base kW=",
    "Load.base.kW=",
    "BatchEdit Load..* kW=",
    "~ kW=",
])
def test_an_empty_value_raises(tmp_path, line):
    """The engine reads an empty value as the end of the command: it drops that property and every later one on the
    line without a word (``WHILE Length(Param)>0``, Load.pas:566, Transformer.pas:491), so ``New Load.l bus1=a
    kW="" kvar=5`` keeps the default kvar. The reader raises instead."""
    with pytest.raises(DssParseError, match=r"=.* is empty; the engine silently drops it and every later property on "
                                            r"the line.* at line 3"):
        read(tmp_path, CIRCUIT + "New Load.base bus1=a kW=10 kvar=3\n" + line + "\n")


def test_a_blank_after_equals_is_no_empty_value(tmp_path):
    """The engine gives ``Edit Load.base kW= 5`` kW=5: the parser skips the blank (Parser/ParserDel.pas:434-439)."""
    model = read(tmp_path, CIRCUIT + "New Load.base bus1=a kW=10\nEdit Load.base kW= 5\n")
    assert only(model, schema.Load).kW == 5.0


def test_each_command_is_its_own_group_in_the_history(tmp_path):
    """The engine recalculates a Load's kW/kvar/kVA/pf once at the end of each command (Load.pas:681), and a ``~`` line
    is a command of its own (``DoMoreCmd``, Executive/ExecHelper.pas:887): ``New Load.l bus1=a kvar=50 kW=100`` gives
    kvar 53.97 (kW and the default pf), while ``New Load.l bus1=a kvar=50`` then ``~ kW=100`` gives kvar 500."""
    model = read(tmp_path, CIRCUIT + "New Load.l bus1=a kvar=50\n~ kW=100\nLoad.l.pf=0.9\nBatchEdit Load..* kvar=1\n")
    load = only(model, schema.Load)
    assert model.commands(load) == [[("bus1", "a"), ("kvar", 50.0)], [("kW", 100.0)], [("pf", 0.9)], [("kvar", 1.0)]]
    assert model.assignments(load) == [("bus1", "a"), ("kvar", 50.0), ("kW", 100.0), ("pf", 0.9), ("kvar", 1.0)]
    compile_deck(tmp_path / "deck.dss")
    dss.Text.Command("? Load.l.kW")
    assert dss.Text.Result() == "100"


def test_a_like_copy_gives_the_source_commands_first(tmp_path):
    """``like=`` copies the source's state as it stands (``MakeLike`` copies kWBase, kvarBase, LoadSpecType and
    PFNominal, Load.pas:716-721), which is what replaying the source's commands gives; the rest of the ``New`` is one
    command after them. The engine gave ``New Load.l like=base kvar=10`` kvar 10 and pf 0.995 for a base of kW=100
    pf=0.5."""
    model = read(tmp_path, CIRCUIT + "New Load.base bus1=a kW=100\n~ pf=0.5\nNew Load.l like=base bus1=b kvar=10\n")
    [load] = [record for record in model.list_by_class(schema.Load) if record.name == "l"]
    assert model.commands(load) == [[("bus1", "a"), ("kW", 100.0)], [("pf", 0.5)],
                                    [("like", "base"), ("bus1", "b"), ("kvar", 10.0)]]

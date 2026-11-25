"""The reader's command semantics and fail-fast rules (DSS_REWRITE_PLAN.md section 3.4)."""

from __future__ import annotations

import logging

import opendssdirect as dss
import pytest

from cimhub_opendss.dss_reader import DSS_COMMANDS, DSS_OPTIONS, DssParseError, DssReader, dss_command, dss_option
from cimhub_opendss import dss_name_map
from cimhub_opendss.schema import opendss_schema as schema


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
    dss.Text.Command("Clear")
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
    dss.Text.Command("Clear")
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
    dss.Text.Command("Clear")
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

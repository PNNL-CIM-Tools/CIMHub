"""The reader's command semantics and fail-fast rules (DSS_REWRITE_PLAN.md section 3.4)."""

from __future__ import annotations

import logging

import pytest

from cimhub_opendss.dss_reader import DssParseError, DssReader
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

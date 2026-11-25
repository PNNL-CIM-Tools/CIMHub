"""GlmWriter (EXPORT_MAPPING.md X0): value formats, one object's text, the deck order, and a read-back round trip."""
from __future__ import annotations

import pytest

from cimhub_gridlabd.glm_reader import GlmModel, GlmReader
from cimhub_gridlabd.glm_writer import GlmWriter, format_complex, format_value
from cimhub_gridlabd.schema import gridlabd as schema


@pytest.mark.parametrize(("real", "imag", "text"), [(0.4576, 1.078, "0.4576+1.078j"), (0.4576, -1.078, "0.4576-1.078j"),
                                                    (-0.5, 0.0, "-0.5+0j"), (1e-06, 0.0775, "1e-06+0.0775j")])
def test_complex_is_rectangular_with_its_sign(real, imag, text):
    assert format_complex(schema.Complex(real=real, imag=imag)) == text


@pytest.mark.parametrize(("value", "text"), [(True, "TRUE"), (False, "FALSE"), (16, "16"), (2401.7771198288433,
                                                                                            "2401.77711982884"),
                                             ("ABCN", '"ABCN"'), ("632", '"632"')])
def test_values(value, text):
    assert format_value(value) == text


def test_a_double_quote_raises():
    with pytest.raises(ValueError, match="holds a double quote"):
        format_value('a"b')


def test_serialize_writes_name_first_and_set_slots_only():
    node = schema.Node(name="632", phases="ABCN", nominal_voltage=2401.78)
    assert GlmWriter().serialize(node) == 'object node {\n  name "632";\n  phases "ABCN";\n  nominal_voltage 2401.78;\n}'


def test_the_property_name_is_glm_s():
    line = schema.OverheadLine(name="l1", from_node="a", to="b")
    assert '  from "a";' in GlmWriter().serialize(line)


def test_deck_order_and_header():
    model = GlmModel()
    model.add_to_graph(schema.OverheadLine(name="l1", phases="ABC", from_node="a", to="b", configuration="c",
                                           length=100.0))
    model.add_to_graph(schema.Node(name="b", phases="ABCN", nominal_voltage=2401.78))
    model.add_to_graph(schema.LineConfiguration(name="c", z11=schema.Complex(real=0.3, imag=1.0)))
    model.clock.update(timezone="UTC0")
    model.globals["relax_naming_rules"] = "1"
    model.modules["powerflow"] = {"solver_method": "NR"}
    deck = GlmWriter().deck(model)
    assert deck.startswith("clock {\n  timezone UTC0;\n}\n#set relax_naming_rules=1\nmodule powerflow {\n"
                           "  solver_method NR;\n}\n")
    assert deck.index("line_configuration") < deck.index("object node") < deck.index("overhead_line")


def test_a_class_with_no_write_order_raises():
    model = GlmModel()
    model.add_to_graph(schema.Motor(name="m"))
    with pytest.raises(ValueError, match=r"no write order for \['Motor'\]"):
        GlmWriter().deck(model)


def test_round_trip_through_the_reader(tmp_path):
    model = GlmModel()
    model.add_to_graph(schema.Node(name="n 1", phases="ABCN", nominal_voltage=277.13))
    model.add_to_graph(schema.TransformerConfiguration(name="xc", connect_type="WYE_WYE", power_rating=500.0,
                                                       primary_voltage=4160.0, secondary_voltage=480.0,
                                                       impedance=schema.Complex(real=0.011, imag=-0.02)))
    path = tmp_path / "deck.glm"
    GlmWriter().write(model, path)
    back = GlmReader(path).read_all()
    assert back.by_name("n 1").nominal_voltage == 277.13
    assert (back.by_name("xc").impedance.real, back.by_name("xc").impedance.imag) == (0.011, -0.02)
    assert str(back.by_name("xc").connect_type) == "WYE_WYE"


def test_a_written_unit_is_written_back(tmp_path):
    """``distance_AB 30 in`` stays 30 inches: GridLAB-D reads a bare 30 in the schema's feet."""
    source = tmp_path / "source.glm"
    source.write_text("object line_spacing { name s; distance_AB 30 in; distance_AN 5.0; }\n")
    model = GlmReader(source).read_all()
    assert '  distance_AB 30 in;' in GlmWriter().serialize(model.by_name("s"), written_units=model.written_units)
    path = tmp_path / "deck.glm"
    GlmWriter().write(model, path)
    back = GlmReader(path).read_all()
    assert (back.by_name("s").distance_AB, back.unit(back.by_name("s"), "distance_AB")) == (30.0, "in")
    assert (back.by_name("s").distance_AN, back.unit(back.by_name("s"), "distance_AN")) == (5.0, "ft")


def _player_model(file: str | None) -> GlmModel:
    model = GlmModel()
    model.add_to_graph(schema.Player(name="p", file=file))
    model.tapes["p"] = [("2000-01-01 00:00:00", "1.0")]
    return model


def test_a_tape_in_a_subdirectory_is_written(tmp_path):
    GlmWriter().write(_player_model("tapes/a.player"), tmp_path / "deck.glm")
    assert (tmp_path / "tapes" / "a.player").read_text() == "2000-01-01 00:00:00,1.0\n"


def test_a_player_with_no_file_raises_before_writing(tmp_path):
    with pytest.raises(ValueError, match=r"GlmWriter: players \['p'\] have no file to write their tape to"):
        GlmWriter().write(_player_model(None), tmp_path / "deck.glm")
    assert not (tmp_path / "deck.glm").exists()

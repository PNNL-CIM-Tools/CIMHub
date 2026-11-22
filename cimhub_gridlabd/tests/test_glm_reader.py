"""GlmReader: one test per rule of the reader (GLM_REWRITE_PLAN.md section 3.4), and every deck reads."""
from __future__ import annotations

import logging
import math

import pytest

from conftest import deck, deck_params, defines
from cimhub_gridlabd.glm_reader import GlmParseError, GlmReader
from cimhub_gridlabd.schema import gridlabd as schema


def read(tmp_path, text: str, **kwargs):
    path = tmp_path / "model.glm"
    path.write_text(text)
    return GlmReader(path, **kwargs).read_all()


def test_value_keeps_its_written_unit(tmp_path):
    model = read(tmp_path, """
object line_spacing { name ls1; distance_AN 30 in; distance_AB 2.5; }
object substation { name sub; phases ABCN; nominal_voltage 7200; base_power 12MVA; }
""")
    spacing = model.by_name("ls1")
    assert spacing.distance_AN == 30.0 and model.unit(spacing, "distance_AN") == "in"
    assert spacing.distance_AB == 2.5 and model.unit(spacing, "distance_AB") == "ft"  # the schema's unit
    substation = model.by_name("sub")
    assert substation.base_power == 12.0 and model.written_units[("sub", "base_power")] == "MVA"


def test_complex_rectangular_and_polar(tmp_path):
    model = read(tmp_path, """
object node { name n1; phases ABCN; nominal_voltage 7200; voltage_A 7200+0.5j; voltage_B 7200-120d; }
""")
    node = model.by_name("n1")
    assert (node.voltage_A.real, node.voltage_A.imag) == (7200.0, 0.5)
    assert node.voltage_B.real == pytest.approx(7200 * math.cos(math.radians(-120)))
    assert node.voltage_B.imag == pytest.approx(7200 * math.sin(math.radians(-120)))
    assert model.polar == {("n1", "voltage_B"): (7200.0, -120.0)}  # as written


def test_macro_from_define_set_or_caller(tmp_path):
    model = read(tmp_path, """
#define V1=7200
object node { name n1; phases AN; nominal_voltage ${V1}; }
object substation { name s; phases ABCN; nominal_voltage 7200; positive_sequence_voltage ${VSOURCE}; }
""", defines={"VSOURCE": "66395.28"})
    assert model.by_name("n1").nominal_voltage == 7200.0
    assert model.by_name("s").positive_sequence_voltage.real == 66395.28


def test_unknown_macro_raises(tmp_path):
    with pytest.raises(GlmParseError, match=r"model.glm:2: macro \$\{VSOURCE\} is not defined"):
        read(tmp_path, "\nobject substation { name s; positive_sequence_voltage ${VSOURCE}; }\n")


def test_expression_is_kept_and_leaves_the_slot_unset(tmp_path):
    model = read(tmp_path, """
schedule LIGHTS { * * * * * 1.0; }
object load { name l1; phases AN; nominal_voltage 7200; base_power_A LIGHTS*1.2; }
""")
    assert model.by_name("l1").base_power_A is None
    assert model.expressions == {("l1", "base_power_A"): "LIGHTS*1.2"}
    assert model.schedules["LIGHTS"] == ["* * * * * 1.0"]


def test_bad_boolean_raises(tmp_path):
    with pytest.raises(GlmParseError, match="model.glm:1: .*is not a boolean"):
        read(tmp_path, "object ZIPload { name z; is_240 maybe; }\n")


def test_unknown_object_type_is_counted(tmp_path):
    model = read(tmp_path, "object recorder { name r; property voltage_A; }\nobject node { name n; }\n")
    assert dict(model.not_read) == {"recorder": 1}
    assert model.count(schema.Node) == 1


def test_unknown_property_raises(tmp_path):
    with pytest.raises(GlmParseError, match="model.glm:3: node has no property 'colour'"):
        read(tmp_path, "object node {\n  name n;\n  colour red;\n}\n")


def test_keywords_are_case_sensitive(tmp_path):
    with pytest.raises(GlmParseError, match="unknown block 'Object battery'"):
        read(tmp_path, "Object battery { name b; }\n")


def test_include_is_followed(tmp_path):
    (tmp_path / "part.glm").write_text("object node { name n2; }\n")
    model = read(tmp_path, '#include "part.glm"\nobject node { name n1; }\n')
    assert {str(node.name) for node in model.list_by_class(schema.Node)} == {"n1", "n2"}


def test_missing_include_raises(tmp_path):
    with pytest.raises(GlmParseError, match="#include file .*missing.glm does not exist"):
        read(tmp_path, '#include "missing.glm"\n')


def test_unread_directive_raises(tmp_path):
    with pytest.raises(GlmParseError, match="directive '#ifdef' is not read"):
        read(tmp_path, "#ifdef X\n#endif\n")


def test_settings_are_kept(tmp_path):
    model = read(tmp_path, """
#set relax_naming_rules=1
clock { timezone EST+5EDT; timestamp '2000-01-01 0:00:00'; }
module tape;
module powerflow { solver_method NR; nominal_frequency 50; }
""")
    assert model.globals == {"relax_naming_rules": "1"}
    assert model.clock["timezone"] == "EST+5EDT"
    assert model.modules == {"tape": {}, "powerflow": {"solver_method": "NR", "nominal_frequency": "50"}}


def test_nested_object_gets_its_parent(tmp_path):
    model = read(tmp_path, """
object inverter { name inv; phases AN; object solar { name pv; rated_power 5000; }; }
""")
    assert model.by_name("pv").parent == "inv"


def test_nested_object_with_its_own_parent_raises(tmp_path):
    with pytest.raises(GlmParseError, match="a nested object sets its own parent"):
        read(tmp_path, "object inverter { name inv; object solar { name pv; parent x; }; }\n")


def test_unnamed_objects_and_references(tmp_path):
    model = read(tmp_path, """
object node:632 { phases ABCN; nominal_voltage 2401.78; }
object node:633 { phases ABCN; nominal_voltage 2401.78; }
object overhead_line { name l1; phases ABC; from node:632; to node:633; length 500; }
object triplex_line_conductor: { resistance 0.97; }
""")
    line = model.by_name("l1")
    assert (line.from_node, line.to) == ("node:632", "node:633")
    assert model.by_name("triplex_line_conductor:3").resistance == 0.97  # no header id: its position


def test_named_object_is_found_by_its_header_alias(tmp_path):
    model = read(tmp_path, """
object node:1 { name n1; }
object node:2 { name n2; }
object overhead_line { name l1; from node:1; to n2; }
""")
    assert model.by_name("l1").from_node == "n1"


def test_object_range_makes_copies(tmp_path):
    model = read(tmp_path, "object house:..2 { floor_area 1500; object ZIPload { base_power 1.0; }; }\n")
    houses = model.list_by_class(schema.House)
    assert [str(house.name) for house in houses] == ["house:0", "house:2"]
    assert [str(z.parent) for z in model.list_by_class(schema.ZIPload)] == ["house:0", "house:2"]


def test_duplicate_name_raises(tmp_path):
    with pytest.raises(GlmParseError, match="model.glm:2: name 'n' is already used by the object at .*model.glm:1"):
        read(tmp_path, "object node { name n; }\nobject meter { name n; }\n")


def test_property_set_twice_keeps_the_last_value(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        model = read(tmp_path, "object fuse { name f; mean_replacement_time 2; mean_replacement_time 3600; }\n")
    assert model.by_name("f").mean_replacement_time == 3600.0
    assert "fuse.mean_replacement_time is set twice on 1 object(s)" in caplog.text


def test_statement_without_semicolon_raises(tmp_path):
    with pytest.raises(GlmParseError, match="statement 'module tape' has no closing ';'"):
        read(tmp_path, "module tape\n")


def test_comments_and_quotes(tmp_path):
    model = read(tmp_path, 'object node { name "a;b"; // a comment { ;\n phases ABCN; }\n')
    assert model.by_name("a;b").phases == "ABCN"


#: Decks that stop, with the reason. Each is a defect in the deck, not a reader gap.
READ_STOPS = {
    "IEEE/IEEE123_transactive.glm": "IEEE123_transactive.glm:26728: unknown block 'Object battery'",
}


@pytest.mark.parametrize("relative, stop", deck_params(READ_STOPS))
def test_every_deck_reads(relative, stop):
    reader = GlmReader(deck(relative), defines=defines(relative))
    if stop is None:
        model = reader.read_all()
        assert len(model) > 0
    else:
        with pytest.raises(GlmParseError, match=stop):
            reader.read_all()

"""The orchestrator: master document, base frequency and the expression guard (the IEEE13_cdpsm directory is
test_cimtbl_sweep.py's)."""
from __future__ import annotations

import pytest

from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer import glm_to_cimtbl
from cimhub_gridlabd.importer.cimtbl import bus, load
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, base_frequency, check_expressions
from cimhub_gridlabd.schema import gridlabd as schema


def read(tmp_path, text: str):
    path = tmp_path / "model.glm"
    path.write_text(text)
    return GlmReader(path).read_all()


def test_base_frequency(tmp_path):
    assert base_frequency(read(tmp_path, "module powerflow { nominal_frequency 50; }\n")) == (50.0, False)
    assert base_frequency(read(tmp_path, "#set powerflow::nominal_frequency=50\n")) == (50.0, False)
    assert base_frequency(read(tmp_path, "module powerflow;\n")) == (60.0, True)


def test_expression_only_raises_in_a_slot_a_mapper_reads(tmp_path):
    model = read(tmp_path, """
schedule S { * * * * * 1; }
object load { name l1; phases AN; base_power_A S*2; }
object node { name n1; phases ABCN; voltage_B S*7200; voltage_A S*7200; }
""")
    fields = {schema.Node: bus.FIELDS[schema.Node], schema.Load: load.FIELDS[schema.Load]}
    with pytest.raises(ValueError, match=r"load l1 \(.*model.glm:3\): base_power_A is the expression 'S\*2'"):
        check_expressions(model, fields, {})
    # the load mapper reads its base's expression itself (S4a-2); voltage_A is read on a swing bus
    with pytest.raises(ValueError, match=r"node n1 \(.*model.glm:4\): voltage_A is the expression 'S\*7200'"):
        check_expressions(model, fields, load.EXPRESSION_SLOTS)
    del model.expressions[("n1", "voltage_A")]
    check_expressions(model, fields, load.EXPRESSION_SLOTS)  # voltage_B is untranscribed: nothing raises


def test_master_lists_every_class_no_mapper_reads(tmp_path, scope, monkeypatch):
    monkeypatch.setattr(glm_to_cimtbl, "MAPPING_ORDER", ())
    model = read(tmp_path, """
object substation { name src; bustype SWING; phases ABCN; nominal_voltage 7200; }
object diesel_dg { name g; parent src; }
object recorder { name r; }
""")
    master = GlmImporter("m").to_cimtbl(model).master
    assert "not mapped: diesel_dg 1, recorder 1" in master.comment  # substation is mapped (S1); diesel_dg is not


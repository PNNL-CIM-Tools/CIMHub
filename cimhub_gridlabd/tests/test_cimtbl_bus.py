"""S1: buses (``bus.cimtbl``) and the swing source (``source.cimtbl``): classification, atoms, fail fast, decks."""
from __future__ import annotations

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from conftest import BIND_STOPS, deck, deck_params, defines
from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_gridlabd.glm_reader import GlmParseError, GlmReader
from cimhub_gridlabd.importer.cimtbl.bus import (DEFAULT_SHORT_CIRCUIT_MVA, DEFAULT_X_OVER_R, FIELDS, NATIVE_CLASSES,
                                                 default_source_impedance)
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim

ATOMS = Path(__file__).parent / "atoms"
GOLDENS = Path(__file__).parent / "goldens"


def read(path: Path, **kwargs):
    return GlmReader(path, **kwargs).read_all()


def parts(model, name: str) -> dict:
    return {part.name: part for part in GlmImporter(name).to_cimtbl(model).parts}


def text_model(tmp_path, text: str):
    path = tmp_path / "model.glm"
    path.write_text(text)
    return read(path)


@pytest.mark.parametrize("native_cls", NATIVE_CLASSES, ids=lambda cls: cls.__name__)
def test_every_slot_is_classified(native_cls):
    check_fields(FIELDS[native_cls], native_cls)


def test_default_source_impedance():
    r, x = default_source_impedance(12.47)
    z = 12.47 ** 2 / 10_000  # |Z| = kV^2 / MVAsc
    assert math.hypot(r, x) == pytest.approx(z)
    assert x / r == pytest.approx(10.0)
    assert (DEFAULT_SHORT_CIRCUIT_MVA, DEFAULT_X_OVER_R) == (10_000.0, 10.0)


# -- tier 1 / 1b: atoms ------------------------------------------------------------------------------------------

def test_feeder_atom_goldens():
    documents = parts(read(ATOMS / "bus" / "feeder.glm"), "feeder")
    assert_matches_golden(documents["bus"], ATOMS / "bus" / "feeder.bus.cimtbl")
    assert_matches_golden(documents["source"], ATOMS / "bus" / "feeder.source.cimtbl")


def test_feeder_atom_binds(scope):
    network = glm_to_cim(read(ATOMS / "bus" / "feeder.glm"), name="feeder")
    voltages = {str(node.mRID): float(node.BaseVoltage.nominalVoltage.to("kV"))
                for node in network.list_by_class(cim.ConnectivityNode)}
    # the children (ld_1, tn_1) are their root's node; meter_1's nominal_voltage 480 does not set its 0.48 kV
    assert voltages == {"sourcebus": 12.47, "n1": 12.47, "meter_1": 0.48, "tm_1": 0.24}
    [source] = network.list_by_class(cim.EnergySource)
    assert float(source.nominalVoltage.to("V")) == pytest.approx(7200 * math.sqrt(3))
    assert float(source.voltageMagnitude.to("V")) == pytest.approx(7200 * math.sqrt(3))
    r, x = default_source_impedance(7.2 * math.sqrt(3))
    assert float(source.r.to("ohm")) == pytest.approx(r) and float(source.x0.to("ohm")) == pytest.approx(x)
    [base] = network.list_by_class(cim.BasePower)
    assert float(base.basePower.to("MVA")) == 12.0


def test_swing_node_atom(scope):
    model = read(ATOMS / "source" / "swing_node.glm")
    assert_matches_golden(parts(model, "swing_node")["source"], ATOMS / "source" / "swing_node.cimtbl")
    [source] = glm_to_cim(model, name="swing_node").list_by_class(cim.EnergySource)
    assert float(source.voltageMagnitude.to("V")) == pytest.approx(7416 * math.sqrt(3))
    assert float(source.voltageAngle.to("deg")) == pytest.approx(-30.0)


# -- fail fast -------------------------------------------------------------------------------------------------------

SOURCE = """
object substation { name src; bustype SWING; phases ABCN; nominal_voltage 7200; %s }
object node { name n1; phases ABCN; nominal_voltage 7200; }
object overhead_line { name l1; phases ABCN; from src; to n1; length 100; }
"""


def test_child_on_a_phase_its_root_lacks_raises(tmp_path):
    model = text_model(tmp_path, SOURCE % "" + """
object meter { name m; phases AN; nominal_voltage 7200; }
object load { name ld; parent m; phases CN; nominal_voltage 7200; }
""")
    with pytest.raises(ValueError, match=r"load ld: phases CN are not all on its root bus meter m \(AN\)"):
        GlmImporter("m").to_cimtbl(model)


def test_source_voltage_far_from_nominal_raises(tmp_path):
    model = text_model(tmp_path, SOURCE % "positive_sequence_voltage 66395.28;")
    with pytest.raises(ValueError, match=r"substation src: source voltage 66395.3 V \(positive_sequence_voltage\) "
                                         r"is more than 10% from nominal_voltage 7200 V"):
        GlmImporter("m").to_cimtbl(model)


def test_reference_phase_other_than_a_raises(tmp_path):
    model = text_model(tmp_path, SOURCE % "reference_phase PHASE_B;")
    with pytest.raises(ValueError, match="substation src: reference_phase PHASE_B; only PHASE_A is mapped"):
        GlmImporter("m").to_cimtbl(model)


def test_expression_in_a_read_slot_raises(tmp_path):
    model = text_model(tmp_path, "schedule S { * * * * * 1; }\n" + SOURCE % "positive_sequence_voltage S*7200;")
    with pytest.raises(ValueError, match=r"positive_sequence_voltage is the expression 'S\*7200'"):
        GlmImporter("m").to_cimtbl(model)


def test_swing_bus_with_a_parent_raises(tmp_path):
    model = text_model(tmp_path, SOURCE % "" + "object node { name s2; parent n1; bustype SWING; phases ABCN; }\n")
    with pytest.raises(ValueError, match="node s2: a swing bus with a parent"):
        GlmImporter("m").to_cimtbl(model)


def test_two_phase_source_raises(tmp_path):
    model = text_model(tmp_path, (SOURCE % "").replace("phases ABCN; nominal_voltage 7200;  }",
                                                        "phases ABN; nominal_voltage 7200;  }"))
    with pytest.raises(ValueError, match="substation src: phases ABN; only 1- and 3-phase swing buses"):
        GlmImporter("m").to_cimtbl(model)


# -- decks -------------------------------------------------------------------------------------------------------

def test_ieee13_cdpsm_goldens():
    model = read(deck("IEEE/IEEE13_cdpsm.glm"), defines=defines("IEEE/IEEE13_cdpsm.glm"))
    documents = parts(model, "IEEE13_cdpsm")
    for name in ("bus", "source"):
        assert_matches_golden(documents[name], GOLDENS / "IEEE13_cdpsm" / f"{name}.cimtbl")


@pytest.mark.parametrize("relative, stop", deck_params(BIND_STOPS))
def test_every_deck_binds(relative, stop, scope):
    def run():
        model = read(deck(relative), defines=defines(relative))
        return glm_to_cim(model, name=Path(relative).stem)

    if stop is not None:
        with pytest.raises((GlmParseError, ValueError), match=stop):
            run()
        return
    network = run()
    nodes = network.list_by_class(cim.ConnectivityNode)
    assert nodes and all(node.BaseVoltage is not None for node in nodes)
    assert len(network.list_by_class(cim.EnergySource)) >= 1

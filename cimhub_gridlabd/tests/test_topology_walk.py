"""The GLM model as a ``cimtopology.core.Network``, and the walk on every deck."""
from __future__ import annotations

import math

import pytest
from cimtopology.core import Connection, System, walk

from conftest import deck, deck_params, defines
from cimhub_gridlabd.glm_reader import GlmParseError, GlmReader
from cimhub_gridlabd.importer.topology import bus_roots, glm_network, line_voltage


def read(tmp_path, text: str):
    path = tmp_path / "model.glm"
    path.write_text(text)
    return GlmReader(path).read_all()


def test_line_voltage():
    assert line_voltage(7.2, System.THREE_PHASE) == pytest.approx(7.2 * math.sqrt(3))
    assert line_voltage(0.12, System.SPLIT_PHASE) == pytest.approx(0.24)
    assert line_voltage(0.277, System.SINGLE_PHASE) == 0.277


def test_child_buses_are_their_root(tmp_path):
    model = read(tmp_path, """
object meter { name tm; phases ABCN; nominal_voltage 7200; }
object load { name ld; parent tm; phases AN; nominal_voltage 7200; }
object capacitor { name cap; parent ld; phases ABCN; nominal_voltage 7200; }
object inverter { name inv; parent tm; }
""")
    assert bus_roots(model) == {"tm": "tm", "ld": "tm", "cap": "tm"}


def test_parent_that_is_not_a_bus_raises(tmp_path):
    model = read(tmp_path, "object inverter { name inv; }\nobject meter { name m; parent inv; }\n")
    with pytest.raises(ValueError, match="meter m: parent inv is not a bus object"):
        bus_roots(model)


FEEDER = """
object substation { name src; bustype SWING; phases ABCN; nominal_voltage 7200; }
object node { name n1; phases ABCN; nominal_voltage 7200; }
object meter { name m1; phases ABCN; nominal_voltage 277; }
object triplex_meter { name t1; phases AS; nominal_voltage 120; }
object overhead_line { name l1; phases ABCN; from src; to n1; length 100; }
object transformer_configuration { name wye; connect_type WYE_WYE; primary_voltage 12470; secondary_voltage 480; }
object transformer_configuration { name ct; connect_type SINGLE_PHASE_CENTER_TAPPED; primary_voltage 7200;
                                   secondary_voltage 120; }
object transformer { name x3; phases ABCN; from n1; to m1; configuration wye; }
object transformer { name x1; phases AS; from n1; to t1; configuration ct; }
"""


def test_network_coils(tmp_path):
    network = glm_network(read(tmp_path, FEEDER))
    coils = {xf.name: [(c.bus, c.kv, c.connection) for c in xf.coils] for xf in network.transformers}
    assert coils["x3"] == [("n1", 12.47, Connection.POLYPHASE), ("m1", 0.48, Connection.POLYPHASE)]
    assert coils["x1"] == [("n1", 7.2, Connection.PHASE_NEUTRAL), ("t1", 0.12, Connection.HALF),
                           ("t1", 0.12, Connection.HALF)]
    assert network.sources[0].kv == pytest.approx(7.2 * math.sqrt(3))


def test_walk_systems(tmp_path):
    buses = walk(glm_network(read(tmp_path, FEEDER)))
    assert {bus: (system.kv, system.system) for bus, system in buses.items()} == {
        "src": (12.47, System.THREE_PHASE), "n1": (12.47, System.THREE_PHASE),
        "m1": (0.48, System.THREE_PHASE), "t1": (0.24, System.SPLIT_PHASE)}


def test_single_phase_wye_wye_is_line_to_line(tmp_path):
    """A 1-phase ``WYE_WYE`` unit's ratings are line to line, as GridLAB-D's 3-phase ones are."""
    model = read(tmp_path, FEEDER.replace("object transformer { name x3; phases ABCN;",
                                          "object transformer { name x3; phases CN;"))
    assert walk(glm_network(model))["m1"].kv == 0.48


def test_coil_rated_single_phase_is_phase_to_neutral(tmp_path):
    """A SINGLE_PHASE unit rated at its buses' nominal_voltage: one phase-to-neutral coil per side, so its service
    is a single-phase system (S6)."""
    model = read(tmp_path, FEEDER + "object node { name s1; phases AN; nominal_voltage 120; }\n"
                 "object transformer_configuration { name sp; connect_type SINGLE_PHASE; primary_voltage 7200; "
                 "secondary_voltage 120; }\nobject transformer { name xs; phases AN; from n1; to s1; "
                 "configuration sp; }\n")
    coils = {xf.name: [(c.bus, c.kv, c.connection) for c in xf.coils] for xf in glm_network(model).transformers}
    assert coils["xs"] == [("n1", 7.2, Connection.PHASE_NEUTRAL), ("s1", 0.12, Connection.PHASE_NEUTRAL)]
    assert walk(glm_network(model))["s1"] == (0.12, System.SINGLE_PHASE)


def test_link_on_a_phase_its_end_lacks_raises(tmp_path):
    model = read(tmp_path, FEEDER + "object node { name n2; phases BN; nominal_voltage 7200; }\n"
                 "object switch { name sw; phases AN; from n1; to n2; status CLOSED; }\n")
    with pytest.raises(ValueError, match=r"switch sw: phases AN are not all on its to node n2 \(BN\); GridLAB-D "
                                         r"throws \(link.cpp:664\)"):
        glm_network(model)


def test_open_status_on_a_line_raises(tmp_path):
    model = read(tmp_path, FEEDER.replace("length 100;", "length 100; status OPEN;"))
    with pytest.raises(ValueError, match="overhead_line l1: status OPEN on a device that is not a switch"):
        glm_network(model)


def test_center_tap_on_three_phases_raises(tmp_path):
    model = read(tmp_path, FEEDER.replace("phases AS; from n1", "phases ABCN; from n1"))
    with pytest.raises(ValueError, match="transformer x1: SINGLE_PHASE_CENTER_TAPPED needs one phase and S"):
        glm_network(model)


def test_ieee13_cdpsm_systems():
    buses = walk(glm_network(GlmReader(deck("IEEE/IEEE13_cdpsm.glm"), defines=defines("IEEE/IEEE13_cdpsm.glm")).read_all()))
    assert buses["sourcebus"].kv == 115.0
    assert buses["650"].kv == 4.16 and buses["650"].system is System.THREE_PHASE
    assert buses["634"].kv == 0.48
    assert {bus.system for bus in buses.values()} == {System.THREE_PHASE, System.SPLIT_PHASE}


#: Decks that stop, with the reason. Each is a defect in the deck (README in tests/decks).
WALK_STOPS = {
    "IEEE/IEEE123_transactive.glm": "unknown block 'Object battery'",
    "IEEE/IEEE13_houses.glm": "Transformer 633-634: its coil on bus 634 gives 0.48 kV, but the island .* is 4.16 kV",
}


@pytest.mark.parametrize("relative, stop", deck_params(WALK_STOPS))
def test_every_deck_walks(relative, stop):
    def run():
        model = GlmReader(deck(relative), defines=defines(relative)).read_all()
        return model, walk(glm_network(model))

    if stop is not None:
        with pytest.raises((GlmParseError, ValueError), match=stop):
            run()
        return
    model, buses = run()
    assert set(buses) == set(bus_roots(model).values())  # every bus is reached

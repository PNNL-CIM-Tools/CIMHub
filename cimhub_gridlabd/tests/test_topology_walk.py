"""The GLM model as a ``cimtopology.core.Network``, and the walk on every deck."""
from __future__ import annotations

import math

import pytest
from cimtopology.core import Connection, System, walk

from conftest import deck, deck_params, defines
from cimhub_gridlabd.glm_reader import GlmParseError, GlmReader
from cimhub_gridlabd.importer.topology import bus_roots, glm_network, line_voltage, service_buses


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


def test_coil_rated_one_phase_service_is_split_phase(tmp_path):
    """A SINGLE_PHASE unit rated at its buses' nominal_voltage is a service (S6, the user's rule): a 120 V secondary
    is one split-phase leg (s1 to N), a 240 V one a center tap (two 120 V halves); both are a 240 V split-phase
    system."""
    model = read(tmp_path, FEEDER + "object node { name s1; phases AN; nominal_voltage 120; }\n"
                 "object node { name s2; phases AN; nominal_voltage 240; }\n"
                 "object transformer_configuration { name sp; connect_type SINGLE_PHASE; primary_voltage 7200; "
                 "secondary_voltage 120; }\nobject transformer { name xs; phases AN; from n1; to s1; "
                 "configuration sp; }\n"
                 "object transformer_configuration { name sp2; connect_type SINGLE_PHASE; primary_voltage 7200; "
                 "secondary_voltage 240; }\nobject transformer { name xs2; phases AN; from n1; to s2; "
                 "configuration sp2; }\n"
                 "object node { name s3; phases AN; nominal_voltage 110; }\n"
                 "object transformer_configuration { name sp3; connect_type SINGLE_PHASE; primary_voltage 7200; "
                 "secondary_voltage 110; }\nobject transformer { name xs3; phases AN; from n1; to s3; "
                 "configuration sp3; }\n")
    coils = {xf.name: [(c.bus, c.kv, c.connection) for c in xf.coils] for xf in glm_network(model).transformers}
    assert coils["xs"] == [("n1", 7.2, Connection.PHASE_NEUTRAL), ("s1", 0.12, Connection.HALF)]
    assert coils["xs2"] == [("n1", 7.2, Connection.PHASE_NEUTRAL), ("s2", 0.12, Connection.HALF),
                            ("s2", 0.12, Connection.HALF)]
    walked = walk(glm_network(model))
    assert walked["s1"] == walked["s2"] == (0.24, System.SPLIT_PHASE)
    # within the walk's nameplate tolerance, as coil_rated: a 110 V can is a 120 V service's leg
    assert service_buses(model, bus_roots(model)) == {"s1": "s1N", "s2": "s1s2N", "s3": "s1N"}


def test_link_on_a_service_bus_raises(tmp_path):
    model = read(tmp_path, FEEDER + "object node { name s1; phases AN; nominal_voltage 120; }\n"
                 "object node { name s9; phases AN; nominal_voltage 120; }\n"
                 "object transformer_configuration { name sp; connect_type SINGLE_PHASE; primary_voltage 7200; "
                 "secondary_voltage 120; }\nobject transformer { name xs; phases AN; from n1; to s1; "
                 "configuration sp; }\nobject switch { name sw9; phases AN; from s1; to s9; status CLOSED; }\n")
    with pytest.raises(ValueError, match="switch sw9: on the s1N service bus s1; only loads are mapped"):
        service_buses(model, bus_roots(model))


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

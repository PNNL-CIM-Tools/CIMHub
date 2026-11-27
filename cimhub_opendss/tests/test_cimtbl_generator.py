"""Atom tests: OpenDSS Generator -> generator.cimtbl -> cim18v17, with the engine as the oracle for the dispatch,
the ratings and a PV bus's voltage and kvar limits."""

from __future__ import annotations

import math
from pathlib import Path

import opendssdirect as dss
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_core.getters.control import get_regulating_control
from cimhub_opendss import dss_to_cim
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer import dss_to_cimtbl
from cimhub_opendss.importer.cimtbl import generator

from conftest import ENGINE_DECKS, compile_deck, deck
from test_dss_to_cimtbl import assert_base_voltages_agree

ATOMS = Path(__file__).parent / "atoms" / "generator"
CIRCUIT = ("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus pu=1.0 MVAsc3=20000 MVAsc1=21000\n"
           "New Line.l1 bus1=sourcebus bus2=b1 phases=3 r1=0.1 x1=0.2 r0=0.3 x0=0.6 length=1 units=kft\n")
#: The engine's Model code of a machine with and without a PV-bus control (model 7 maps as model 1).
PV_BUS_MODEL = 3


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def gens():
    return DssReader(ATOMS / "gens.dss").read_all()


def test_classification_is_complete():
    check_fields(generator.FIELDS, generator.NATIVE_CLASS)


def test_matches_golden(gens):
    site = dss_to_cimtbl.site(gens)
    assert_matches_golden(generator.map_generator(gens, site.buses, site.feeder), ATOMS / "gens.cimtbl")


def test_kvar_replays_the_deck_order():
    assert generator.dispatched_kvar("g", [("kW", 620.0), ("kvar", 30.0), ("kW", 0.0)]) == 0
    assert generator.dispatched_kvar("g", [("kvar", 30.0), ("kW", 100.0)]) == pytest.approx(3.0, rel=1e-3)
    assert generator.dispatched_kvar("g", [("kW", 0.0), ("kvar", 30.0), ("kW", 50.0)]) == 30
    assert generator.dispatched_kvar("g", [("kW", 100.0)]) == pytest.approx(53.974282)
    assert generator.dispatched_kvar("g", []) == 60


def test_kvar_limits_follow_the_engine_reset():
    """Each kW, pf or kvar assignment resets Maxkvar and Minkvar to +-2 x kvar (engine-checked)."""
    assert generator.reactive_limits([("kW", 1000.0)], 50.0) == (100.0, -100.0)
    assert generator.reactive_limits([("kW", 1000.0), ("maxkvar", 500.0)], 50.0) == (500.0, -100.0)
    assert generator.reactive_limits([("maxkvar", 500.0), ("minkvar", -50.0), ("kW", 800.0)], 50.0) == (100.0, -100.0)


def test_machines_bind(gens):
    network = dss_to_cim(gens, name="atom")
    assert_base_voltages_agree(network)
    machines = {machine.name: machine for machine in network.graph[network.cim.SynchronousMachine].values()}
    assert len(machines) == 14
    assert float(machines["pq"].p.to("kW")) == -100 and machines["pq"].type.value == "generator"
    assert machines["delta"].earthing is False and machines["pq"].earthing is True
    steam = machines["steam"]
    control = steam.RegulatingControl
    assert control.Terminal is steam.Terminals[0] and control.RegulatingCondEq == [steam] and steam.controlEnabled
    assert get_regulating_control(control, "V").target == pytest.approx(1.02 * 4160)
    capped = machines["capped"]
    assert (float(capped.maxQ.to("kVAr")), float(capped.minQ.to("kVAr"))) == pytest.approx((500, -1079.48564427617))
    single = machines["single"]
    assert [phase.phase.value for phase in single.RotatingMachinePhase] == ["A"]
    assert float(single.ratedU.to("kV")) == pytest.approx(0.277 * math.sqrt(3))
    assert machines["limited"].RegulatingControl is None


@pytest.mark.parametrize("text, message", [
    ("New Generator.x bus1=b1 kv=4.16 kW=100 model=2\n", "model ConstantZ is not mapped"),
    ("New Generator.x bus1=b1 kv=4.16 kW=100 maxkvar=50\n", "Maxkvar/Minkvar on model ConstantPQ"),
    ("New Generator.x bus1=b1 kv=4.16 kW=100 MVA=1\n", "MVA not mapped"),
    ("New Generator.x bus1=b1.1.2 phases=1 kv=2.4 kW=100\n", "wye neutral on node 2"),
])
def test_unmapped_machines_fail_fast(tmp_path, text, message):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + text)
    native = DssReader(path).read_all()
    site = dss_to_cimtbl.site(native)
    with pytest.raises(ValueError, match=message):
        generator.map_generator(native, site.buses, site.feeder)


def _ask(query: str) -> str:
    dss.Text.Command(f"? {query}")
    return dss.Text.Result()


def _engine_differences(network) -> list[str]:
    """Every difference between the machines and the engine's dispatch, ratings and PV-bus settings. kW and kvar
    are the properties (the dispatch), not ``Generators.kvar()``, which a solved PV bus changes."""
    differences = []

    def check(label: str, ours: float, theirs: float) -> None:
        if not math.isclose(ours, theirs, rel_tol=1e-9, abs_tol=1e-9):
            differences.append(f"{label}: {ours} vs {theirs}")

    for machine in network.graph.get(network.cim.SynchronousMachine, {}).values():
        name = machine.name
        dss.Generators.Name(name)
        rated_kv = float(machine.ratedU.to("kV"))
        one_phase_wye = len(machine.RotatingMachinePhase) == 1 and machine.earthing
        check(f"{name} kW", -float(machine.p.to("kW")), float(_ask(f"generator.{name}.kW")))
        check(f"{name} kvar", -float(machine.q.to("kVAr")), float(_ask(f"generator.{name}.kvar")))
        check(f"{name} kVA", float(machine.ratedS.to("kVA")), dss.Generators.kVARated())
        check(f"{name} kV", rated_kv / math.sqrt(3) if one_phase_wye else rated_kv, dss.Generators.kV())
        check(f"{name} delta", not machine.earthing, dss.Generators.IsDelta())
        control = machine.RegulatingControl
        if control is None:
            if dss.Generators.Model() == PV_BUS_MODEL:
                differences.append(f"{name}: a model 3 machine has no control")
            continue
        check(f"{name} model", PV_BUS_MODEL, dss.Generators.Model())
        target = get_regulating_control(control, "V").target
        check(f"{name} Vpu", target / float(machine.ratedU.to("V")), float(_ask(f"generator.{name}.Vpu")))
        check(f"{name} Maxkvar", float(machine.maxQ.to("kVAr")), float(_ask(f"generator.{name}.Maxkvar")))
        check(f"{name} Minkvar", float(machine.minQ.to("kVAr")), float(_ask(f"generator.{name}.Minkvar")))
    return differences


def test_atom_matches_the_engine(gens):
    network = dss_to_cim(gens, name="atom")
    compile_deck(ATOMS / "gens.dss")
    assert _engine_differences(network) == []


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_machines_match_the_engine(relative):
    path = deck(relative)
    try:
        network = dss_to_cim(DssReader(path).read_all(), name="deck")
    except ValueError as error:
        if "DSS-10" in str(error):
            pytest.skip(f"{relative}: stops before the machines ({str(error)[:80]})")
        raise
    compile_deck(path)
    assert _engine_differences(network) == []

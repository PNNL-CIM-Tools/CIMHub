"""GLM player -> CIM -> DSS LoadShape, solved in the engine (GLM S8, DSS S8): a synthetic deck (no utility data)
whose two loads read the GLM player atom's four 1-minute rows (``zipload.player``) behind a matrix line. The player
is one ConformLoadSchedule, exported as a LoadShape both loads name as ``yearly``. In yearly mode at 60 s steps,
step k (sample k, wrapping after the fourth) must solve as the same deck with every load's kW and kvar fixed at the
player's value k times the base: the exported sinterval, multipliers and Q rule are the player's.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import opendssdirect as dss
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim
from cimhub_opendss.dss_writer import DssWriter
from cimhub_opendss.exporter.cim_to_dss import DssExporter
from cimhub_opendss.schema import opendss_schema as schema

ROOT = Path(__file__).parents[2]
PLAYER = ROOT / "cimhub_gridlabd" / "tests" / "atoms" / "player" / "zipload.player"
DECK = """
module tape;
class player { double value; }
object player { name zipload; file zipload.player; loop 0; }
object substation { name src; bustype SWING; phases ABCN; nominal_voltage 7200; }
object node { name p; phases ABCN; nominal_voltage 7200; }
object line_configuration { name lc; z11 0.3465+1.0179j; z12 0.1560+0.5017j; z13 0.1580+0.4236j;
    z21 0.1560+0.5017j; z22 0.3375+1.0478j; z23 0.1535+0.3849j; z31 0.1580+0.4236j; z32 0.1535+0.3849j;
    z33 0.3414+1.0348j; }
object overhead_line { name ln; phases ABC; from src; to p; length 5000; configuration lc; }
object load { name l3; parent p; phases ABCN; nominal_voltage 7200; base_power_A zipload.value*400000;
    power_fraction_A 1.0; power_pf_A 0.9; base_power_B zipload.value*400000; power_fraction_B 1.0; power_pf_B 0.9;
    base_power_C zipload.value*400000; power_fraction_C 1.0; power_pf_C 0.9; }
object load { name l1; parent p; phases BN; nominal_voltage 7200; base_power_B zipload.value*200000;
    power_fraction_B 1.0; power_pf_B 0.85; }
"""
#: zipload.player's four values
VALUES = [0.425364, 0.421530, 0.418488, 0.399880]


@pytest.fixture
def exported(tmp_path):
    """The deck's DSS model, its loads naming the player's LoadShape."""
    (tmp_path / "glm").mkdir()
    shutil.copy(PLAYER, tmp_path / "glm" / "zipload.player")
    (tmp_path / "glm" / "atom.glm").write_text(DECK)
    with cim_scope():
        time_points = {}
        network = glm_to_cim(GlmReader(tmp_path / "glm" / "atom.glm").read_all(), name="atom",
                             time_points=time_points)
        return DssExporter(time_points).to_model(network, name_source="name")


def solve(path: Path, *, mode: str = "snapshot", steps: int = 1) -> list[np.ndarray]:
    """The node voltages after each of ``steps`` solves, controls off and a tight tolerance."""
    dss.Text.Command("Clear")
    dss.Text.Command(f"Compile [{path.resolve()}]")
    dss.Text.Command(f"Set mode={mode} stepsize=60s number=1 controlmode=off tolerance=1e-10 maxiterations=500")
    voltages = []
    for _ in range(steps):
        dss.Solution.Solve()
        assert dss.Solution.Converged()
        voltages.append(np.array(dss.Circuit.AllBusVolts()))
    return voltages


def test_the_player_is_one_loadshape_both_loads_name(exported):
    [shape] = exported.list_by_class(schema.Loadshape)
    assert (shape.name, shape.npts, shape.sinterval) == ("zipload", 4, "60")
    assert shape.mult == VALUES and not shape.qmult  # a GLM base scales p and q together
    assert {str(load.yearly) for load in exported.list_by_class(schema.Load)} == {"zipload"}


def test_each_step_solves_as_the_deck_fixed_at_its_value(exported, tmp_path):
    played = tmp_path / "played" / "atom.dss"
    DssWriter().write(exported, played)
    steps = solve(played, mode="yearly", steps=len(VALUES) + 1)
    assert np.max(np.abs(steps[0] - steps[1])) > 1e-6 * np.max(np.abs(steps[0]))  # the steps are told apart
    bases = {str(load.name): (load.kW, load.kvar) for load in exported.list_by_class(schema.Load)}
    for number, voltages in enumerate(steps):
        value = VALUES[number % len(VALUES)]  # sample k at k x 60 s; the fifth step wraps to the first
        for load in exported.list_by_class(schema.Load):
            kw, kvar = bases[str(load.name)]
            load.kW, load.kvar, load.yearly = kw * value, kvar * value, None
        fixed = tmp_path / f"fixed{number}" / "atom.dss"
        DssWriter().write(exported, fixed)
        [expected] = solve(fixed)
        assert np.max(np.abs(voltages - expected)) / np.max(np.abs(expected)) < 1e-9, f"step {number + 1}"
        for load in exported.list_by_class(schema.Load):
            load.kW, load.kvar, load.yearly = *bases[str(load.name)], "zipload"

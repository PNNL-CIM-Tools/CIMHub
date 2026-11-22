"""A GLM schedule (GLM S9) in the other spokes: its days by season and day type have no OpenDSS or GDM form (DSS has
no calendar, a GDM series needs absolute times), so both write its loads static at their base and name the group in
one warning; a player's group on the same deck still becomes a time series. A synthetic deck (no utility data)."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_gdm.exporter.cim_to_gdm import GdmExporter
from gdm.systems.distribution.components import DistributionLoad
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim
from cimhub_opendss.exporter.cim_to_dss import DssExporter
from cimhub_opendss.schema import opendss_schema as schema

ROOT = Path(__file__).parents[2]
PLAYER = ROOT / "cimhub_gridlabd" / "tests" / "atoms" / "player" / "zipload.player"
DECK = """
module tape;
class player { double value; }
object player { name zipload; file zipload.player; loop 0; }
schedule daily { * 0-5 * * * 0.5; * 6-23 * * 1-5 1.0; * 6-23 * * 0,6 0.8; }
object substation { name src; bustype SWING; phases ABCN; nominal_voltage 7200; }
object node { name p; phases ABCN; nominal_voltage 7200; }
object line_configuration { name lc; z11 0.3465+1.0179j; z12 0.1560+0.5017j; z13 0.1580+0.4236j;
    z21 0.1560+0.5017j; z22 0.3375+1.0478j; z23 0.1535+0.3849j; z31 0.1580+0.4236j; z32 0.1535+0.3849j;
    z33 0.3414+1.0348j; }
object overhead_line { name ln; phases ABC; from src; to p; length 5000; configuration lc;
    continuous_rating_A 400; continuous_rating_B 400; continuous_rating_C 400; }
object load { name sched; parent p; phases AN; nominal_voltage 7200; base_power_A daily*100000;
    power_fraction_A 1.0; power_pf_A 1.0; }
object load { name played; parent p; phases BN; nominal_voltage 7200; base_power_B zipload.value*200000;
    power_fraction_B 1.0; power_pf_B 1.0; }
"""


@pytest.fixture
def imported(tmp_path):
    """(network, time points) of the deck."""
    (tmp_path / "glm").mkdir()
    shutil.copy(PLAYER, tmp_path / "glm" / "zipload.player")
    (tmp_path / "glm" / "atom.glm").write_text(DECK)
    with cim_scope():
        time_points = {}
        network = glm_to_cim(GlmReader(tmp_path / "glm" / "atom.glm").read_all(), name="atom",
                             time_points=time_points)
        yield network, time_points


def test_dss_writes_the_scheduled_load_static(imported, caplog):
    network, time_points = imported
    with caplog.at_level(logging.WARNING, logger="cimhub_opendss.exporter.load"):
        model = DssExporter(time_points).to_model(network, name_source="name")
    loads = {str(load.name): load for load in model.list_by_class(schema.Load)}
    assert (loads["sched"].yearly, loads["sched"].kW) == (None, pytest.approx(100))  # its base, static
    assert loads["played"].yearly == "zipload"
    assert "1 load group(s) are written static" in caplog.text and "['daily']" in caplog.text


def test_gdm_writes_the_scheduled_load_static(imported, caplog):
    network, time_points = imported
    with caplog.at_level(logging.WARNING, logger="cimhub_gdm.exporter.time_series"):
        system = GdmExporter(time_points).to_model(network, name_source="name")
    assert "1 load group(s) are written static" in caplog.text and "['daily']" in caplog.text
    assert sorted(load.name for load in system.get_components(DistributionLoad)) == ["played", "sched"]

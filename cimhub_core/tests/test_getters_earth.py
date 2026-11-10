"""cimhub_core.getters.earth: a WireConfiguration's earth model and resistivity."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.earth import EarthData, get_earth_resistivity

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _configuration():
    network = load_model(SHAPES / "line_by_wire_configuration.cimtbl")
    [configuration] = network.graph[cim.WireConfiguration].values()
    return configuration


def test_model_and_resistivity():
    assert get_earth_resistivity(_configuration()) == EarthData(cim.EarthModelKind.carson, 100.0, None)


def test_no_earth_is_none():
    configuration = _configuration()
    configuration.EarthResistivity = None
    assert get_earth_resistivity(configuration) is None

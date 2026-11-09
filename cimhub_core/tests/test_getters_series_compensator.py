"""cimhub_core.getters.series_compensator: a series compensator's impedance in a declared unit."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.series_compensator import SeriesCompensatorData, get_series_compensator

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _compensator(mrid):
    network = load_model(SHAPES / "series_compensator.cimtbl")
    return next(obj for obj in network.graph[cim.SeriesCompensator].values() if obj.mRID == mrid)


def test_impedance_in_ohm():
    assert get_series_compensator(_compensator("rx_r1")) == SeriesCompensatorData(
        0.5, 2.0, 0.5, 2.0, None, None, None, None)


def test_unset_x_raises():
    compensator = _compensator("rx_r1")
    compensator.x = None
    with pytest.raises(ValueError, match="SeriesCompensator 'rx_r1': x is unset"):
        get_series_compensator(compensator)


def test_other_equipment_raises():
    with pytest.raises(ValueError, match="is not a SeriesCompensator"):
        get_series_compensator(cim.ACLineSegment(mRID="ln_x"))

"""cimhub_core.getters.switch_state.get_reclose_delays: a protected switch's reclose sequence."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.switch_state import get_reclose_delays

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _switch(mrid):
    network = load_model(SHAPES / "switch.cimtbl")
    return next(obj for objects in network.graph.values() for obj in objects.values()
                if isinstance(obj, cim.Switch) and obj.mRID == mrid)


def test_delays_in_step_order():
    assert get_reclose_delays(_switch("sw_r1")) == (0.5, 2.0)
    assert get_reclose_delays(_switch("sw_r1"), "ms") == (500.0, 2000.0)


def test_no_sequence_is_no_reclosure():
    assert get_reclose_delays(_switch("sw_brkr")) == ()


def test_a_missing_step_raises():
    recloser = _switch("sw_r1")
    recloser.RecloseSequences[0].recloseStep = 3
    with pytest.raises(ValueError, match=r"reclose steps \[2, 3\] of 2 sequences"):
        get_reclose_delays(recloser)


def test_unset_delay_raises():
    recloser = _switch("sw_r1")
    recloser.RecloseSequences[1].recloseDelay = None
    with pytest.raises(ValueError, match="recloseDelay is unset"):
        get_reclose_delays(recloser)

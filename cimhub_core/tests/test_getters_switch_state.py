"""cimhub_core.getters.switch_state on the switch shape."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.switch_state import get_switch_state

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture
def switches():
    with cim_scope():
        network = load_model(SHAPES / "switch.cimtbl")
        yield {switch.mRID: switch for cls in (cim.Breaker, cim.LoadBreakSwitch)
               for switch in network.graph[cls].values()}


def test_open_and_closed(switches):
    assert get_switch_state(switches["sw_s1"], which="actual") is True
    assert get_switch_state(switches["sw_brkr"], which="normal") is False


def test_actual_and_normal_are_read_separately(switches):
    switch = switches["sw_s1"]
    switch.open = False
    assert get_switch_state(switch, which="actual") is False
    assert get_switch_state(switch, which="normal") is True


def test_unset_state_raises(switches):
    switch = switches["sw_brkr"]
    switch.open = None
    with pytest.raises(ValueError, match="Breaker 'sw_brkr': open is unset"):
        get_switch_state(switch, which="actual")


def test_unknown_which_raises(switches):
    with pytest.raises(ValueError, match="which must be one of"):
        get_switch_state(switches["sw_brkr"], which="as_built")

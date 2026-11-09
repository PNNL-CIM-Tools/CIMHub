import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.getters.in_service import get_in_service


def test_in_service_reads_the_state_asked_for():
    source = cim.EnergySource(mRID="src", inService=False, normallyInService=True)
    assert get_in_service(source, which="normal") is True
    assert get_in_service(source, which="actual") is False


def test_unset_is_none():
    assert get_in_service(cim.EnergySource(mRID="src"), which="normal") is None


def test_which_has_no_default():
    with pytest.raises(ValueError, match="which must be one of"):
        get_in_service(cim.EnergySource(mRID="src"), which="nominal")

"""cimhub_core.getters.impedance_table: an impedance tap changer table's points, as stored."""

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.impedance_table import ImpedanceTablePoint, get_impedance_table


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _table(*points):
    table = cim.ImpedanceTapChangerTable(mRID="ict_1")
    for point in points:
        point.ImpedanceTapChangerTable = table
        table.ImpedanceTapChangerTablePoint.append(point)
    return table


def test_points_as_stored():
    table = _table(
        cim.ImpedanceTapChangerTablePoint(angle=cim.AngleDegrees(30.0), rEnd1=cim.PerCent(20.0), xEnd1=cim.PerCent(20.0)),
        cim.ImpedanceTapChangerTablePoint(ratio=0.95, step=3, xEnd2=cim.PerCent(-5.0)))
    assert get_impedance_table(table) == (
        ImpedanceTablePoint(None, None, pytest.approx(30.0), (pytest.approx(20.0), None, None),
                            (pytest.approx(20.0), None, None)),
        ImpedanceTablePoint(3, 0.95, None, (None, None, None), (None, pytest.approx(-5.0), None)))


def test_table_without_points_raises():
    with pytest.raises(ValueError, match="ImpedanceTapChangerTable 'ict_1': has no ImpedanceTapChangerTablePoint"):
        get_impedance_table(_table())

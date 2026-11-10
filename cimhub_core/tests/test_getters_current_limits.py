"""cimhub_core.getters.current_limits on the line shape and inline atoms."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.current_limits import CurrentLimits, get_current_limits

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"

# one line with a limit set on each terminal (the old CIMHub writer's convention), limit types as common.cimtbl's
ATOM = """Profile = cim18v17
Object Feeder: mRID=fdr, name=fdr
Object BaseVoltage: mRID=bv_4p16kv, nominalVoltage (kV)=4.16
Table OperationalLimitType: mRID, name, durationKind, season, isInfiniteDuration, direction
    olt_normal,        normal,        normal,    ,       true,  absoluteValue
    olt_short,         short,         shortTerm, ,       false, absoluteValue
    olt_emergency,     emergency,     emergency, ,       false, absoluteValue
    olt_untyped,       untyped,       ,          ,       false, absoluteValue
    olt_summer_normal, summer normal, normal,    summer, true,  absoluteValue
    olt_winter_normal, winter normal, normal,    winter, true,  absoluteValue
Object ACLineSegment: mRID=ln_x, name=x, node1=n1, node2=n2, length (m)=100, r (ohm)=1, x (ohm)=2, BaseVoltage=bv_4p16kv, EquipmentContainer=fdr
Table OperationalLimitSet: mRID, Terminal
    ln_x_limits_1, ln_x_T1
    ln_x_limits_2, ln_x_T2
Table CurrentLimit: mRID, normalValue (A), OperationalLimitType, OperationalLimitSet
"""


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _atom_line(tmp_path, rows):
    path = tmp_path / "atom.cimtbl"
    path.write_text(ATOM + "".join(f"    {row}\n" for row in rows))
    network = load_model(path)
    return next(iter(network.graph[cim.ACLineSegment].values()))


def _shape_line(mrid):
    network = load_model(SHAPES / "line_by_impedance.cimtbl")
    return next(line for line in network.graph[cim.ACLineSegment].values() if line.mRID == mrid)


def test_limits_on_the_equipment():
    assert get_current_limits(_shape_line("ln_l1")) == CurrentLimits(normal=340, short_term=None, emergency=600)


def test_limits_in_the_callers_unit():
    assert get_current_limits(_shape_line("ln_l1"), "kA").normal == pytest.approx(0.34)


def test_no_limits_is_all_none():
    assert get_current_limits(_shape_line("ln_l2")) == CurrentLimits(None, None, None)


def test_limits_on_each_terminal_agree(tmp_path):
    line = _atom_line(tmp_path, ["n_1, 400, olt_normal, ln_x_limits_1", "n_2, 400, olt_normal, ln_x_limits_2",
                                 "s_1, 500, olt_short, ln_x_limits_1"])
    assert get_current_limits(line) == CurrentLimits(normal=400, short_term=500, emergency=None)


def test_limits_that_disagree_raise(tmp_path):
    line = _atom_line(tmp_path, ["n_1, 400, olt_normal, ln_x_limits_1", "n_2, 450, olt_normal, ln_x_limits_2"])
    with pytest.raises(ValueError, match="ACLineSegment 'ln_x': normal current limits disagree"):
        get_current_limits(line)


def test_limit_type_without_duration_kind_raises(tmp_path):
    line = _atom_line(tmp_path, ["u_1, 400, olt_untyped, ln_x_limits_1"])
    with pytest.raises(ValueError, match="OperationalLimitType 'olt_untyped': durationKind None is not one of"):
        get_current_limits(line)


def test_limit_without_a_value_raises(tmp_path):
    line = _atom_line(tmp_path, ["n_1, , olt_normal, ln_x_limits_1"])
    with pytest.raises(ValueError, match="CurrentLimit 'n_1': normalValue is unset"):
        get_current_limits(line)


def test_limit_without_a_type_raises(tmp_path):
    line = _atom_line(tmp_path, ["n_1, 400, , ln_x_limits_1"])
    with pytest.raises(ValueError, match="CurrentLimit 'n_1': has no OperationalLimitType"):
        get_current_limits(line)


# seasons (OperationalLimitType.season) -------------------------------------------------------------------------

SEASONAL = ["n_1, 400, olt_normal, ln_x_limits_1", "e_1, 600, olt_emergency, ln_x_limits_1",
            "su_1, 350, olt_summer_normal, ln_x_limits_1", "wi_1, 450, olt_winter_normal, ln_x_limits_1"]


def test_no_season_reads_the_all_year_limits(tmp_path):
    assert get_current_limits(_atom_line(tmp_path, SEASONAL)) == CurrentLimits(normal=400, short_term=None,
                                                                              emergency=600)


def test_a_season_overrides_the_all_year_limit_of_its_kind(tmp_path):
    line = _atom_line(tmp_path, SEASONAL)
    assert get_current_limits(line, season=cim.CalendarSeasonKind.summer) == CurrentLimits(350, None, 600)
    assert get_current_limits(line, season=cim.CalendarSeasonKind.winter) == CurrentLimits(450, None, 600)


def test_a_season_without_limits_of_its_own_reads_all_year(tmp_path):
    line = _atom_line(tmp_path, SEASONAL)
    assert get_current_limits(line, season=cim.CalendarSeasonKind.spring) == CurrentLimits(400, None, 600)

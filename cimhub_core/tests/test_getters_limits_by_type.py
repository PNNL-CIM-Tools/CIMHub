"""``get_configuration_limits_by_type``: a template's limits, on ``EquipmentConfiguration.OperationalLimitSet``."""

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.limits_by_type import get_configuration_limits_by_type
from cimtables import load_model

#: one template with two seasonal ratings, on its own set (the set is written alone; the template names it)
TEMPLATE = """Profile = cim18v17

Table OperationalLimitType: mRID, name, durationKind, isInfiniteDuration, direction
    olt_season1, season 1, normal, true, absoluteValue
    olt_season2, season 2, normal, true, absoluteValue

Table OperationalLimitSet: mRID
    xc_ratings

Table ApparentPowerLimit: mRID, normalValue (kVA), OperationalLimitType, OperationalLimitSet
    xc_ratings_1, 22000, olt_season1, xc_ratings
    xc_ratings_2, 25000, olt_season2, xc_ratings

Table TransformerTankConfiguration: mRID, name, OperationalLimitSet
    xc, xc, xc_ratings
    bare, bare,
"""


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture
def network(tmp_path):
    path = tmp_path / "template.cimtbl"
    path.write_text(TEMPLATE)
    return load_model(path)


def _configuration(network, mrid):
    return next(obj for obj in network.graph[cim.TransformerTankConfiguration].values() if obj.mRID == mrid)


def test_a_templates_limits_by_type_in_the_callers_unit(network):
    limits = get_configuration_limits_by_type(_configuration(network, "xc"), cim.ApparentPowerLimit, "MVA")
    assert {limit_type.mRID: value for limit_type, value in limits.items()} == {
        "olt_season1": pytest.approx(22.0), "olt_season2": pytest.approx(25.0)}


def test_a_template_without_a_set_has_none(network):
    assert get_configuration_limits_by_type(_configuration(network, "bare"), cim.ApparentPowerLimit, "kVA") == {}


def test_another_limit_class_is_not_read(network):
    assert get_configuration_limits_by_type(_configuration(network, "xc"), cim.CurrentLimit, "A") == {}

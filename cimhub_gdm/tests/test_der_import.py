"""DistributionSolar / DistributionBattery → PowerElectronicsConnection + unit + InverterInfo (tests/atoms/der)."""

from uuid import uuid4

import gdm_atoms
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import der
from gdm.distribution.components import DistributionBattery, DistributionSolar
from gdm.distribution.controllers import InverterController
from gdm.distribution.enums import Phase
from gdm.distribution.equipment import BatteryEquipment, InverterEquipment, SolarEquipment
from gdm.quantities import ActivePower, ReactivePower

from cimhub_gdm import gdm_to_cim


def der_system():
    system = gdm_atoms.shell_system()
    gdm_atoms.add_der(system)
    return system


def test_der_matches_golden():
    gdm_atoms.assert_import_matches(der_system(), gdm_atoms.ATOMS / "der" / "der.cimtbl")


@pytest.mark.parametrize("fields, cls", [
    (der.FIELDS_DistributionSolar, DistributionSolar),
    (der.FIELDS_DistributionBattery, DistributionBattery),
    (der.FIELDS_SolarEquipment, SolarEquipment),
    (der.FIELDS_BatteryEquipment, BatteryEquipment),
    (der.FIELDS_InverterEquipment, InverterEquipment),
])
def test_fields_are_classified(fields, cls):
    check_fields(fields, cls)


def test_injection_is_the_load_sign():
    assert der.injection(ActivePower(25, "kilowatt"), "active", "pv").value == -25
    assert der.injection(ReactivePower(-10, "kilovar"), "reactive", "pv").value == 10
    assert str(der.injection(ReactivePower(0, "kilovar"), "reactive", "pv").value) == "0.0"


def test_injection_checks_the_power_unit():
    with pytest.raises(ValueError, match="is not an active power unit"):
        der.injection(ReactivePower(25, "kilovar"), "active", "pv")


@pytest.mark.parametrize("kw, state", [(150, "discharging"), (-3, "charging"), (0, "waiting")])
def test_battery_state_follows_the_output(kw, state):
    assert der.battery_state(ActivePower(kw, "kilowatt")) == state


def test_der_on_the_neutral_raises():
    system = der_system()
    system.get_component(DistributionSolar, "primary").phases = [Phase.C, Phase.N]
    with pytest.raises(ValueError, match="a DER on the neutral has no PowerElectronicsConnectionPhase"):
        gdm_to_cim(system)


def test_inverter_shared_by_pv_and_battery_raises():
    system = der_system()
    ess = system.get_component(DistributionBattery, "ess")
    system.add_component(ess.model_copy(update={"name": "shared", "uuid": uuid4(),
                                                "inverter": system.get_component(DistributionSolar, "roof").inverter}))
    with pytest.raises(ValueError, match="'inv33': shared by a PV and a battery"):
        gdm_to_cim(system)


def test_panel_rated_in_kva_is_taken_as_kw_with_a_warning(caplog):
    # ditto's PVSystem reader writes the panel's Pmpp as an ActivePower in kVA (GDM_MAPPING.md §14)
    power = der.panel_power(ActivePower(30, "kilova"), "pv")
    assert (power.value, power.unit) == (30.0, "kW")
    assert "in an apparent power unit (ditto's PVSystem reader); taken as 30.0 kW" in caplog.text


def test_panel_rated_in_kvar_raises():
    with pytest.raises(ValueError, match="is not an active power unit"):
        der.panel_power(ReactivePower(30, "kilovar"), "pv")


def test_inverter_controller_is_pending():
    system = der_system()
    controller = InverterController.example()
    system.add_component(controller)
    system.get_component(DistributionSolar, "roof").controller = controller
    with pytest.raises(ValueError, match="InverterController x1: pending, inverter controls"):
        gdm_to_cim(system)

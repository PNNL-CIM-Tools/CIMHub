"""The exporter's framework: slot coverage, naming, the system name, fail-fast rules (EXPORT_MAPPING.md)."""

from uuid import UUID, uuid5

import cimtables
import gdm_atoms
import pytest

from cimhub_gdm import GdmExporter, gdm_to_cim
from cimhub_gdm.exporter import EXPORT_ORDER
from cimhub_gdm.exporter.slots import check_slots
from cimhub_gdm.exporter.source import phase_angle

SOURCE_GOLDEN = gdm_atoms.ATOMS / "source" / "balanced_3ph.cimtbl"


def _source_network():
    return cimtables.load_model(SOURCE_GOLDEN)


def _node(network, name):
    [node] = [node for node in network.graph[network.cim.ConnectivityNode].values() if node.name == name]
    return node


@pytest.mark.parametrize("module", EXPORT_ORDER, ids=lambda module: module.__name__.rsplit(".", 1)[-1])
def test_every_gdm_field_has_a_slot(module):
    for gdm_class, slots in module.SLOTS.items():
        check_slots(slots, gdm_class)


def test_names_follow_the_shared_switch():
    system = GdmExporter().to_model(_source_network(), name_source="mrid", system_name="atom")
    feeder_names = sorted(feeder.name for feeder in system.get_components(gdm_atoms.DistributionFeeder))
    assert feeder_names == ["fdr_atom", "fdr_atom2"]
    assert system.get_component(gdm_atoms.DistributionVoltageSource, "src_src").equipment.sources[2].name == \
        "src_src_C"


def test_two_buses_may_share_a_name():
    """Names are free text; the uuid tells them apart."""
    network = _source_network()
    _node(network, "b2").name = "b1"
    system = GdmExporter().to_model(network, name_source="name", system_name="atom")
    assert len(system.list_components_by_name(gdm_atoms.DistributionBus, "b1")) == 2


def test_a_component_is_identified_by_its_cim_uri():
    """A component takes its CIM object's uri(); a part, a uuid5 of its owner's on its class and suffix."""
    network = _source_network()
    [source] = network.graph[network.cim.EnergySource].values()
    system = GdmExporter().to_model(network, name_source="name", system_name="atom")
    exported = system.get_component(gdm_atoms.DistributionVoltageSource, source.name)
    assert exported.uuid == UUID(source.uri())
    assert exported.equipment.sources[0].uuid == uuid5(UUID(source.uri()), "PhaseVoltageSourceEquipment_A")
    assert {bus.uuid for bus in system.get_components(gdm_atoms.DistributionBus)} == \
        {UUID(node.uri()) for node in network.graph[network.cim.ConnectivityNode].values()}


def test_several_feeders_need_a_system_name():
    with pytest.raises(ValueError, match="2 Feeders .* pass system_name="):
        GdmExporter().to_model(_source_network())


def test_one_feeder_names_the_system():
    system = gdm_atoms.DistributionSystem(name="solo", auto_add_composed_components=True)
    feeder = gdm_atoms.DistributionFeeder(name="f1")
    system.add_component(gdm_atoms.DistributionBus(name="b1", rated_voltage=gdm_atoms.Voltage(4.16, "kilovolt"),
                                                   voltage_type=gdm_atoms.LL, phases=gdm_atoms.ABC, feeder=feeder))
    assert GdmExporter().to_model(gdm_to_cim(system), name_source="name").name == "f1"


def test_unset_source_impedance_raises():
    network = _source_network()
    [source] = network.graph[network.cim.EnergySource].values()
    source.r0 = None
    with pytest.raises(ValueError, match="r0 unset"):
        GdmExporter().to_model(network, system_name="atom")


@pytest.mark.parametrize(("angle", "position", "expected"),
                         [(0.0, 1, -120.0), (0.0, 2, 120.0), (30.0, 1, -90.0), (-150.0, 1, 90.0), (180.0, 0, -180.0)])
def test_phase_angle_steps_minus_120_and_wraps(angle, position, expected):
    assert phase_angle(angle, position) == pytest.approx(expected)


# --- X2: fills and fail-fast rules ----------------------------------------------------------------------------------

def _golden(family, name):
    return cimtables.load_model(gdm_atoms.ATOMS / family / f"{name}.cimtbl")


def _named(network, cim_class, name):
    [obj] = [obj for obj in network.graph[cim_class].values() if obj.name == name]
    return obj


def test_fills_are_counted_in_one_warning(caplog):
    with caplog.at_level("WARNING", logger="cimhub_gdm.exporter.fills"):
        GdmExporter().to_model(_golden("switch", "switches"), name_source="name", system_name="atom")
    [record] = caplog.records
    assert "placeholder protection" in record.message
    assert "MatrixImpedanceSwitch.length x5" in record.message
    assert "MatrixImpedanceRecloser.controller x1" in record.message


def test_placeholder_protection_is_named_after_its_device():
    system = GdmExporter().to_model(_golden("switch", "switches"), name_source="name", system_name="atom")
    fuse = system.get_component(gdm_atoms.MatrixImpedanceFuse, "fus")
    recloser = system.get_component(gdm_atoms.MatrixImpedanceRecloser, "rcl")
    assert fuse.equipment.tcc_curve.name == "fus_tcc_placeholder"
    assert (recloser.controller.name, recloser.controller.equipment.name) == ("rcl_ctrl_placeholder",) * 2


def test_a_normal_state_differing_from_the_actual_one_is_a_controller():
    system = GdmExporter().to_model(_golden("switch", "switches"), name_source="name", system_name="atom")
    switches = {switch.name: switch for switch in system.get_components(gdm_atoms.MatrixImpedanceSwitch)}
    assert switches["lbs"].equipment.controller.normal_state == "open"
    assert switches["tie"].equipment.controller is None  # normally open and open
    assert switches["mix"].is_closed == [True, False, True]


def test_a_fuse_whose_normal_state_differs_raises():
    network = _golden("switch", "switches")
    _named(network, network.cim.Fuse, "fus").normalOpen = True
    with pytest.raises(ValueError, match="MatrixImpedanceFuseEquipment holds no switch controller"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


def test_a_sectionaliser_has_no_export():
    network = _golden("switch", "switches")
    network.add_to_graph(network.cim.Sectionaliser(mRID="sec", name="sec"))
    with pytest.raises(ValueError, match="no GDM export yet for {'Sectionaliser': 1}"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


def test_a_geometry_line_rates_its_first_conductor():
    """geo's own emergency limit goes on its first conductor, which splits acsr_556; the others keep their wire's
    rating, 1.5 x normal where the wire has no emergency limit (acsr_4/0: 340 A, 510 A)."""
    network = gdm_atoms.type_limit_durations(_golden("line", "lines"))
    geo = _named(network, network.cim.ACLineSegment, "geo")
    [emergency] = [value for limit_set in geo.OperationalLimitSet for value in limit_set.OperationalLimitValue
                   if value.OperationalLimitType.name == "emergency"]
    emergency.normalValue = network.cim.CurrentFlow(900, "A")
    exported = GdmExporter().to_model(network, name_source="name", system_name="atom")
    conductors = exported.get_component(gdm_atoms.GeometryBranch, "geo").equipment.conductors
    assert [(conductor.name, float(conductor.emergency_ampacity.to("ampere").magnitude)) for conductor in conductors] \
        == [("acsr_556", 900.0), ("acsr_556_2", 1095.0), ("acsr_556_2", 1095.0), ("acsr_4/0", 510.0)]


def test_an_unnamed_inverter_is_shared():
    """roof and roof2 on one InverterInfo with no name: one GDM equipment, named '' (infrasys keys it by uuid)."""
    network = _golden("der", "der")
    _named(network, network.cim.GenerationInverterInfo, "inv33").name = None
    exported = GdmExporter().to_model(network, name_source="name", system_name="atom")
    roof, roof2 = (exported.get_component(gdm_atoms.DistributionSolar, name) for name in ("roof", "roof2"))
    assert roof.inverter is roof2.inverter and roof.inverter.name == ""


def test_a_hybrid_inverter_is_one_der_per_unit():
    """pv_house with home's battery behind its inverter: each unit takes its maxP share (5 of 10 kW) of the 4 kW, the
    q and the 6 kVA rating, and is named and identified by its unit; the two halves share one inverter."""
    network = _golden("der", "der")
    cim = network.cim
    house, home = _named(network, cim.PowerElectronicsConnection, "house"), _named(network, cim.BatteryUnit, "home")
    connections = network.graph[cim.PowerElectronicsConnection]
    network.graph[cim.PowerElectronicsConnection] = {key: connection for key, connection in connections.items()
                                                     if connection is not home.PowerElectronicsConnection}
    home.PowerElectronicsConnection = house
    house.PowerElectronicsUnit.append(home)
    house.PowerElectronicsUnit[0].irradiance = None  # the rule: the unit's output share of its panel
    exported = GdmExporter().to_model(network, name_source="name", system_name="atom")
    pv = exported.get_component(gdm_atoms.DistributionSolar, "house")
    battery = exported.get_component(gdm_atoms.DistributionBattery, "home")
    pv_unit = house.PowerElectronicsUnit[0]
    assert (pv.uuid, battery.uuid) == (UUID(pv_unit.uri()), UUID(home.uri()))
    assert [der.active_power.to("kilowatt").magnitude for der in (pv, battery)] == pytest.approx([2, 2])
    assert pv.irradiance.to("kilowatt / meter ** 2").magnitude == pytest.approx(0.4)
    assert pv.inverter is battery.inverter
    assert pv.inverter.rated_apparent_power.to("kilova").magnitude == pytest.approx(3)


def test_a_stored_irradiance_is_exported_as_is():
    """B16b: PhotoVoltaicUnit.irradiance, when set, is the GDM irradiance, not the output's share of the panel."""
    exported = GdmExporter().to_model(_golden("der", "der"), name_source="name", system_name="atom")
    roof = exported.get_component(gdm_atoms.DistributionSolar, "roof")
    assert roof.irradiance.to("kilowatt / meter ** 2").magnitude == pytest.approx(0.9)


def test_a_battery_rated_differently_each_way_raises():
    network = _golden("der", "der")
    _named(network, network.cim.BatteryUnit, "ess").minP = network.cim.ActivePower(-100, "kW")
    with pytest.raises(ValueError, match="minP -100.0 kW is not the negative of maxP 250.0 kW"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


def test_a_coupled_reactor_raises():
    network = _golden("reactor", "reactors")
    _named(network, network.cim.SeriesCompensator, "rx3").x0 = network.cim.Reactance(30, "ohm")
    with pytest.raises(ValueError, match="x0 30.0 ohm differ from r 0.0, x 14.8 ohm"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


def test_a_reactor_with_a_varistor_raises():
    network = _golden("reactor", "reactors")
    _named(network, network.cim.SeriesCompensator, "r1").varistorPresent = True
    with pytest.raises(ValueError, match="has a varistor"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


def test_a_control_on_another_terminal_raises():
    network = _golden("capacitor", "capacitors")
    cim = network.cim
    control = _named(network, cim.RegulatingControl, "vc")
    control.Terminal = _named(network, cim.LinearShuntCompensator, "qc").Terminals[0]
    with pytest.raises(ValueError, match="not its own terminal"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


def test_a_disabled_control_exports_no_controller():
    network = _golden("capacitor", "capacitors")
    _named(network, network.cim.RegulatingControl, "vc").enabled = False
    system = GdmExporter().to_model(network, name_source="name", system_name="atom")
    assert system.get_component(gdm_atoms.DistributionCapacitor, "vc").controllers == []


def test_capacitor_targets_invert_the_import():
    system = GdmExporter().to_model(_golden("capacitor", "capacitors"), name_source="name", system_name="atom")
    [controller] = system.get_component(gdm_atoms.DistributionCapacitor, "vc").controllers
    assert (controller.on_voltage.to("volt").magnitude, controller.off_voltage.to("volt").magnitude,
            controller.pt_ratio, controller.delay_on.to("second").magnitude) == pytest.approx((115, 125, 20, 15))


def _only_transformer(name):
    """The transformer golden with one PowerTransformer, ``name``, left to export."""
    network = _golden("transformer", "transformers")
    transformers = network.graph[network.cim.PowerTransformer]
    for key in [key for key, transformer in transformers.items() if transformer.name != name]:
        del transformers[key]
    return network


def test_a_transformer_under_tap_control_has_no_export_yet():
    network = _only_transformer("t_ln")
    control = network.cim.TapChangerControl(mRID="ltc", name="ltc")
    network.add_to_graph(control)
    [tap] = [tap for tap in network.graph[network.cim.RatioTapChanger].values()
             if tap.TransformerEnd.PowerTransformer.name == "t_ln"]
    tap.TapChangerControl = control
    with pytest.raises(ValueError, match="no GDM export yet for a PowerTransformer under tap control"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


def test_a_bank_of_tanks_has_no_export_yet():
    network = _only_transformer("t_ln")
    transformer = _named(network, network.cim.PowerTransformer, "t_ln")
    transformer.TransformerTanks.append(network.cim.TransformerTank(mRID="second_tank"))
    with pytest.raises(ValueError, match="no GDM export yet for a bank of 2 tanks"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


def test_a_three_phase_regulator_has_no_export_yet():
    network = _golden("regulator", "regulators")
    for end in _named(network, network.cim.VoltageRegulator, "r1").AutoTransformerEnd:
        end.Terminal.phases = network.cim.PhaseCode.ABCN
    with pytest.raises(ValueError, match="no GDM export yet for a VoltageRegulator but a single-phase unit"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


def _regulator_controller(network, name):
    system = GdmExporter().to_model(network, name_source="name", system_name="atom")
    return system.get_component(gdm_atoms.DistributionRegulator, name).controllers


def test_regulator_settings_invert_the_import():
    """r1: 2440 V band 40 V on a PT of 20, line drop 0.0857 + j0.257 ohm on a 700 A CT, taps -16..16."""
    [controller] = _regulator_controller(_golden("regulator", "regulators"), "r1")
    volts = [getattr(controller, slot).to("volt").magnitude
             for slot in ("v_setpoint", "bandwidth", "min_v_limit", "max_v_limit", "ldc_R", "ldc_X")]
    assert volts == pytest.approx([122, 2, 110, 130, 3, 9])
    assert (controller.name, controller.tapped_winding, controller.max_step, controller.controlled_phase.value,
            controller.controlled_bus.name) == ("r1", 2, 32, "A", "b3")


def test_unset_regulator_limits_and_line_drop():
    """No limit is the setpoint over the whole tap range (122 V x 0.9 and x 1.1; GDM needs one above 0 V); no line
    drop is 0 V, which ditto 0.1.8 needs to write a RegControl."""
    network = _golden("regulator", "regulators")
    control = _named(network, network.cim.TapChangerControl, "rb_a")
    control.minLimitVoltage = control.maxLimitVoltage = None
    [controller] = _regulator_controller(network, "rb_a")
    volts = [getattr(controller, slot).to("volt").magnitude for slot in ("min_v_limit", "max_v_limit", "ldc_R",
                                                                       "ldc_X")]
    assert volts == pytest.approx([109.8, 134.2, 0, 0])


def test_a_regulator_without_an_enabled_control_raises():
    """GDM requires a controller per phase."""
    network = _golden("regulator", "regulators")
    _named(network, network.cim.RatioTapChanger, "r1").controlEnabled = False
    with pytest.raises(ValueError, match="VoltageRegulator 'vr_r1': no enabled TapChangerControl"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")

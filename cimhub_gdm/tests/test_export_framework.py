"""The exporter's framework: slot coverage, naming, the system name, fail-fast rules (EXPORT_MAPPING.md)."""

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


def test_two_buses_on_one_name_raise():
    network = _source_network()
    _node(network, "b2").name = "b1"
    with pytest.raises(ValueError, match="both named 'b1' in GDM DistributionBus"):
        GdmExporter().to_model(network, name_source="name", system_name="atom")


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


def test_a_geometry_line_has_no_export_yet():
    network = gdm_atoms.type_limit_durations(_golden("line", "lines"))
    with pytest.raises(ValueError, match="no GDM export yet for geometry lines: ACLineSegment 'ln_geo'"):
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

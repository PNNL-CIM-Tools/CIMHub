"""The exported system through ditto's OpenDSS writer and the OpenDSS engine (EXPORT_PLAN.md §4: ditto is a consumer).

The export must write, compile and solve, and solve like the system it came from. What ditto 0.1.8 can't write of the
original is left out of both:
- CircuitBreakerEquipment and DisconnectorEquipment have no writer (strict xfail below);
- t_ln: ditto rejects ln1's 1-based couplings and drops an instance tap (its Transformer has no Tap_wdg). The export
  writes 0-based couplings and puts the tap on the catalog (X3), so it is in the export-only test.

The DER are left out of the comparison, and checked on their own: ditto writes no PV ``active_power`` (OpenDSS
makes Pmpp × Irradiance, and the atoms' irradiance is not their output's share), writes a PV's kV from its bus
rating, line to line taken as line to ground, and has no battery writer at all.

Capacitors are left out of the comparison: ditto reads a bus rating as line to ground in its capacitor writer whatever
its ``voltage_type``, so the original's line-to-line buses put its capacitors at √3 times their voltage. The export's
line-to-ground buses (X6) do not. The atoms' regulators can't be compared: ditto writes no RegControl without line
drop R and X, which the original's rb bank leaves unset, and r1 parallels rb_a at another tap.
"""

import math

import gdm_atoms
import pytest

from cimhub_gdm import GdmExporter, gdm_to_cim

writer = pytest.importorskip("ditto.writers.opendss.write")
opendssdirect = pytest.importorskip("opendssdirect")
opendssdirect.Basic.AllowChangeDir(False)

#: ditto writes their lines but no LineCode for them.
DITTO_UNWRITTEN = ((gdm_atoms.MatrixImpedanceSwitch, "brk"), (gdm_atoms.MatrixImpedanceSwitch, "dis"))
#: ... and of the original, t_ln (see above).
ORIGINAL_UNWRITTEN = (*DITTO_UNWRITTEN, (gdm_atoms.DistributionTransformer, "t_ln"))
VOLTAGE_TOL_PU = 1e-4  # ditto writes BasekV with 1.732 for sqrt(3)

FAMILIES = (gdm_atoms.add_source, gdm_atoms.add_switches, gdm_atoms.add_lines, gdm_atoms.add_loads,
            gdm_atoms.add_transformers)

def _remove(system, component) -> None:
    """``component`` and the inline parts of its equipment, which the cascade leaves behind."""
    system.remove_component(component)
    for winding in getattr(getattr(component, "equipment", None), "windings", []):
        if system.has_component(winding):
            system.remove_component(winding)


def _system(*families, unwritten=DITTO_UNWRITTEN):
    system = gdm_atoms.shell_system()
    for add_family in families:
        add_family(system)
    for component_class, name in unwritten:
        _remove(system, system.get_component(component_class, name))
    return system


def _export(system):
    network = gdm_atoms.type_limit_durations(gdm_to_cim(system))
    return GdmExporter().to_model(network, name_source="name", system_name=system.name)


def _solve(system, folder) -> dict[str, float]:
    """Write ``system`` with ditto, compile and solve it; each node's voltage in pu."""
    folder.mkdir()
    writer.Writer(system).write(folder, separate_substations=False, separate_feeders=False)
    opendssdirect.Text.Command(f'redirect "{folder / "Master.dss"}"')
    opendssdirect.Text.Command("solve")
    assert opendssdirect.Solution.Converged()
    return dict(zip(opendssdirect.Circuit.AllNodeNames(), opendssdirect.Circuit.AllBusMagPu()))


def test_the_export_solves_like_its_original(tmp_path):
    original = _solve(_system(*FAMILIES, unwritten=ORIGINAL_UNWRITTEN), tmp_path / "original")
    exported = _solve(_export(_system(*FAMILIES, unwritten=ORIGINAL_UNWRITTEN)), tmp_path / "exported")
    assert exported.keys() == original.keys()
    assert exported == pytest.approx(original, abs=VOLTAGE_TOL_PU)


def test_the_export_with_capacitors_and_t_ln_solves(tmp_path):
    voltages = _solve(_export(_system(*FAMILIES, gdm_atoms.add_capacitors)), tmp_path / "exported")
    assert all(0.9 < voltages[f"b1.{conductor}"] < 1.1 for conductor in (1, 2, 3))


def test_an_exported_regulator_bank_holds_its_band(tmp_path):
    """rb alone (r1 removed) feeding the loads on b3: each unit's RegControl holds 122 V ± 1 V on its PT of 20."""
    system = _system(gdm_atoms.add_source, gdm_atoms.add_loads, gdm_atoms.add_regulators, unwritten=())
    _remove(system, system.get_component(gdm_atoms.DistributionRegulator, "r1"))
    voltages = _solve(_export(system), tmp_path / "exported")
    base = 4160 / math.sqrt(3)  # b3's line-to-ground volts at 1 pu
    low, high = (121 * 20 / base, 123 * 20 / base)
    assert all(low < voltages[f"b3.{conductor}"] < high for conductor in (1, 2, 3))


def test_an_exported_pv_makes_its_cim_output(tmp_path):
    """Each PV's OpenDSS output is the p and q CIM holds (generation sign), through the irradiance rule."""
    system = _system(gdm_atoms.add_source, gdm_atoms.add_lines, gdm_atoms.add_transformers, gdm_atoms.add_der,
                     unwritten=((gdm_atoms.DistributionTransformer, "t_ln"),))
    expected = {f"{pv.name}.{kind}": getattr(pv, f"{kind}_power").to(unit).magnitude
                for pv in system.get_components(gdm_atoms.DistributionSolar)
                for kind, unit in (("active", "kilowatt"), ("reactive", "kilovar"))}
    _solve(_export(system), tmp_path / "exported")
    made = {}
    for name in opendssdirect.PVsystems.AllNames():
        opendssdirect.Circuit.SetActiveElement(f"PVSystem.{name}")
        powers = opendssdirect.CktElement.Powers()
        made[f"{name}.active"], made[f"{name}.reactive"] = -sum(powers[0::2]), -sum(powers[1::2])
    assert made == pytest.approx(expected, abs=1e-6)


@pytest.mark.xfail(reason="ditto 0.1.8 writes no LineCode for CircuitBreaker or Disconnector equipment",
                   strict=True, raises=Exception)
def test_breakers_and_disconnectors_compile(tmp_path):
    _solve(_export(_system(gdm_atoms.add_source, gdm_atoms.add_switches, unwritten=())), tmp_path / "exported")

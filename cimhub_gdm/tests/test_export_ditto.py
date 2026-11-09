"""The exported system through ditto's OpenDSS writer and the OpenDSS engine (EXPORT_PLAN.md §4: ditto is a consumer).

The export must write, compile and solve, and solve like the system it came from. Capacitors are left out of that
comparison: ditto 0.1.8 reads a bus rating as line to ground in its capacitor writer whatever its ``voltage_type``, so
the original's line-to-line buses put its capacitors at √3 times their voltage. The export's line-to-ground buses
(X6) do not. ditto 0.1.8 has no writer for CircuitBreakerEquipment or DisconnectorEquipment (strict xfail below).
"""

import gdm_atoms
import pytest

from cimhub_gdm import GdmExporter, gdm_to_cim

writer = pytest.importorskip("ditto.writers.opendss.write")
opendssdirect = pytest.importorskip("opendssdirect")
opendssdirect.Basic.AllowChangeDir(False)

#: ditto writes their lines but no LineCode for them.
DITTO_UNWRITTEN = ("brk", "dis")
VOLTAGE_TOL_PU = 1e-4  # ditto writes BasekV with 1.732 for sqrt(3)


def _system(*families, unwritten=DITTO_UNWRITTEN):
    system = gdm_atoms.shell_system()
    for add_family in families:
        add_family(system)
    for name in unwritten:
        system.remove_component(system.get_component(gdm_atoms.MatrixImpedanceSwitch, name))
    return gdm_atoms.without_geometry(system)


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


FAMILIES = (gdm_atoms.add_source, gdm_atoms.add_switches, gdm_atoms.add_lines, gdm_atoms.add_loads)


def test_the_export_solves_like_its_original(tmp_path):
    original = _solve(_system(*FAMILIES), tmp_path / "original")
    exported = _solve(_export(_system(*FAMILIES)), tmp_path / "exported")
    assert exported.keys() == original.keys()
    assert exported == pytest.approx(original, abs=VOLTAGE_TOL_PU)


def test_the_export_with_capacitors_solves(tmp_path):
    voltages = _solve(_export(_system(*FAMILIES, gdm_atoms.add_capacitors)), tmp_path / "exported")
    assert all(0.9 < voltages[f"b1.{conductor}"] < 1.1 for conductor in (1, 2, 3))


@pytest.mark.xfail(reason="ditto 0.1.8 writes no LineCode for CircuitBreaker or Disconnector equipment",
                   strict=True, raises=Exception)
def test_breakers_and_disconnectors_compile(tmp_path):
    _solve(_export(_system(*FAMILIES, unwritten=())), tmp_path / "exported")

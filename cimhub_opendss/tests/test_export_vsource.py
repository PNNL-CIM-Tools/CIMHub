"""Export atoms: EnergySource -> Vsource (EXPORT_MAPPING.md S6a), checked against the original deck in the engine."""
from __future__ import annotations

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import opendssdirect as dss
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssImporter, DssReader
from cimhub_opendss.exporter import vsource
from cimhub_opendss.exporter.cim_to_dss import DssExporter

from conftest import compile_deck
from engine_compare import assert_same_engine_state
from export_atoms import assert_matches_dss_golden, bus_names, export_atom, export_network

ATOMS = Path(__file__).parent / "atoms" / "vsource"
CASES = ["mvasc", "ohms", "isc", "defaults", "single_phase", "fifty_hz"]
PROPERTIES = ("R1", "X1", "R0", "X0", "basekv", "pu", "angle", "phases")


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _source_properties(path: Path) -> dict[str, float]:
    compile_deck(path)
    dss.Circuit.SetActiveElement("Vsource.source")
    return {slot: float(dss.Properties.Value(slot)) for slot in PROPERTIES}


@pytest.mark.parametrize("case", CASES)
def test_export_matches_the_original_in_the_engine(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    written = export_atom(atom, tmp_path, name_source="name")
    expected, actual = _source_properties(atom), _source_properties(written)
    for slot in PROPERTIES:
        assert math.isclose(actual[slot], expected[slot], rel_tol=1e-9, abs_tol=1e-12), slot
    assert_same_engine_state(atom, written)


@pytest.mark.parametrize("case", CASES)
def test_export_under_mrid_and_uri_solves_the_same(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    for name_source in ("mrid", "uri"):
        written, network = export_network(atom, tmp_path, name_source=name_source)
        assert_same_engine_state(atom, written, by_element=False, bus_names=bus_names(network, name_source))


@pytest.mark.parametrize("case", CASES)
def test_export_matches_golden(case, tmp_path):
    written = export_atom(ATOMS / f"{case}.dss", tmp_path, name_source="mrid")
    assert_matches_dss_golden(written, ATOMS / "export" / f"{case}.dss")


def test_fifty_hz_deck_keeps_its_frequency(tmp_path):
    written = export_atom(ATOMS / "fifty_hz.dss", tmp_path, name_source="mrid")
    assert "Set defaultbasefreq=50" in written.read_text().splitlines()


def test_short_circuit_from_thevenin_inverts_the_importer():
    from cimhub_opendss.importer.cimtbl.vsource import thevenin_from_short_circuit
    source = vsource.cim.EnergySource(mRID="src")
    args = (7.2, 100.0, 90.0, 4.0, 3.0)
    thevenin = thevenin_from_short_circuit(*args)
    for value, expected in zip(vsource.short_circuit_from_thevenin(source, 7.2, *thevenin), args[1:]):
        assert math.isclose(value, expected, rel_tol=1e-12)
    with pytest.raises(ValueError, match="no X/R ratio"):
        vsource.short_circuit_from_thevenin(source, 7.2, 0.0, 1.0, 0.1, 0.3)


def test_negative_sequence_a_rounding_error_from_a_zero_positive_is_the_same():
    """IEEE123's R1=0: rel_tol alone never matches r2 1e-15 ohm against r 0, so they also agree within 1e-9 ohm."""
    network = DssImporter("ohms").to_cim(DssReader(ATOMS / "ohms.dss").read_all())
    [source] = network.graph[cim.EnergySource].values()
    source.r2, source.x2 = cim.Resistance(1e-15), source.x
    [record] = DssExporter().to_model(network, name_source="name").list_by_class(vsource.NATIVE_CLASS)
    assert (record.R1, record.X1) == (0.0, pytest.approx(0.0001))

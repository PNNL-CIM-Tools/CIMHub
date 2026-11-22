"""Tier 2 (EXPORT_MAPPING.md, tests): each importer atom deck through the exporter and back.

atom ``.glm`` -> ``glm_to_cim`` -> ``GlmExporter.to_model`` -> ``GlmWriter`` -> ``GlmReader`` -> ``glm_to_cim``: the two
CIM models are equal (``cimtables.diff_models``, in SI) except for the differences the spec lists, each matched here
by name (``EXPECTED``, ``UNUSED``). GLM names are written ``glm_safe_name``'d (X1), so the first model is compared
under those names. The exported deck is committed beside its atom (D6), so a diff shows what an exporter change does.

``catalog.glm`` is not run alone: it is a catalog, and ``line.glm`` includes it and uses its templates.

The transformer forms no GLM deck holds (plan section 8.3) are an atom written as CIM, ``transformer/forms.cimtbl``:
exported, checked against the X3 and X4 values computed here, committed as ``forms.exported.glm`` and solved in
GridLAB-D 6.0.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import cimtables
import pytest

from cimhub_core.cimtbl_testing import assert_text_matches_golden, cim_scope
from cimhub_core.time_points import REGULAR_TIME_POINT_CLASS, rows_by_schedule
from gridlabd_engine import solve
from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter
from cimhub_gridlabd.exporter.naming import glm_safe_name
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim

ATOMS = Path(__file__).parent / "atoms"
DECKS = sorted(path for path in ATOMS.glob("*/*.glm") if path.name != "catalog.glm"
               and not path.name.endswith(".exported.glm"))
#: templates an atom defines and no equipment uses: GLM's configurations are written per use (EXPORT_MAPPING.md)
UNUSED = ("cncab_cn_250", "xc_unused")
#: (difference, why), as EXPORT_MAPPING.md lists them
EXPECTED = [
    (r"(AutoTransformerEnd \S+\.baseU|RatioTapChanger \S+\.neutralU): expected (2401\.78|4160\.00498\d*) volt, "
     r"got (2401\.7771\d*|4159\.99999\d*) volt",
     "a bus's nominal_voltage is its BaseVoltage's (X0): the deck's 2401.78 V is 4160 V / sqrt 3, rounded"),
    (r"BatteryInfo \S+\.numberOfCells: expected 11, got 28",
     "a battery's nominal_voltage is unset (X12, the DCConductingAssetInfo TODO): GridLAB-D's 115 V gives 28 cells"),
    (r"ConformLoad (ld_ld_sched|ld_tl_house): missing|EnergyConsumer (ld_ld_sched|ld_tl_house): extra"
     r"|ConformLoadGroup lg_zipsched: missing",
     "a group with no schedule (zipsched, a player the deck does not define) is written static (X29), so its loads "
     "come back EnergyConsumers"),
]
#: plain floats (ZIP fractions) compare to the last digits the writer's 15 keep
FLOAT_REL = 1e-12
_FLOATS = re.compile(r"expected (-?[0-9.]+(?:e-?\d+)?), got (-?[0-9.]+(?:e-?\d+)?)$")
#: a player's rows are written in GMT (X29): its start comes back the same instant at +00:00
_START = re.compile(r"\.startTime: expected '(.+)', got '(.+)'$")


def _first_import(deck: Path, directory: Path, time_points: dict):
    """The atom's own import, written to ``directory``, then re-read under its GLM-safe names."""
    model = GlmReader(deck).read_all()
    network = glm_to_cim(model, name="atom", artifact_dir=directory, time_points=time_points)
    renames = sorted({(obj.name, glm_safe_name(obj.name)) for obj in model.iter_all()
                      if getattr(obj, "name", None) and glm_safe_name(obj.name) != obj.name},
                     key=lambda rename: -len(rename[0]))
    for artifact in directory.glob("*.cimtbl"):
        text = artifact.read_text()
        for old, new in renames:
            text = text.replace(old, new)
        artifact.write_text(text)
    return network


def _unexpected(difference: str) -> bool:
    if difference.endswith(": missing") and any(root in difference for root in UNUSED):
        return False
    if any(re.fullmatch(pattern, difference) for pattern, _ in EXPECTED):
        return False
    start = _START.search(difference)
    if start and datetime.fromisoformat(start[1]) == datetime.fromisoformat(start[2]):
        return False
    floats = _FLOATS.search(difference)
    return not (floats and math.isclose(float(floats[1]), float(floats[2]), rel_tol=FLOAT_REL))


def _points(network, time_points: dict) -> dict[str, list[float]]:
    """Schedule mRID -> its value1 per point (the sidecar's rows; the two imports' uris may differ)."""
    if not time_points:
        return {}
    rows = rows_by_schedule(time_points[REGULAR_TIME_POINT_CLASS])
    return {schedule.mRID: rows[schedule.uri()].column("value1").to_pylist()
            for schedule in network.graph.get(cim.ConformLoadSchedule, {}).values()}


@pytest.mark.parametrize("deck", DECKS, ids=lambda deck: deck.stem)
def test_an_atom_round_trips_through_the_exporter(deck, tmp_path):
    exported = tmp_path / "exported.glm"
    first_points, second_points = {}, {}
    with cim_scope():
        network = _first_import(deck, tmp_path / "first", first_points)
        GlmWriter().write(GlmExporter(first_points).to_model(network, name_source="name"), exported)
        second_network = glm_to_cim(GlmReader(exported).read_all(), name="atom", artifact_dir=tmp_path / "second",
                                    time_points=second_points)
        assert _points(second_network, second_points) == _points(network, first_points)
    with cim_scope():
        first = cimtables.load_model(tmp_path / "first" / "atom.cimtbl")
        second = cimtables.load_model(tmp_path / "second" / "atom.cimtbl")
        differences = [line for line in cimtables.diff_models(first, second, rel_tol=1e-9) if _unexpected(line)]
    assert not differences, "\n".join(differences)
    assert_text_matches_golden(exported.read_text(), deck.with_suffix(".exported.glm"))
    for tape in sorted(tmp_path.glob("*.player")):  # a player's file, beside the deck (X29)
        assert_text_matches_golden(tape.read_text(), deck.parent / f"{tape.stem}.exported.player")


FORMS = ATOMS / "transformer" / "forms.cimtbl"


def _complex(value) -> complex:
    return complex(value.real, value.imag)


@pytest.fixture(scope="module")
def forms():
    with cim_scope():
        network = cimtables.load_model(FORMS)
        return GlmExporter().to_model(network, name_source="name")


@pytest.mark.parametrize(("unit", "kva", "r", "x"), [
    ("ynd", 500, 0.005 + 0.005, 0.06), ("dyn11", 300, 0.004 + 0.004, 0.05), ("ynz", 200, 0.006 + 0.006, 0.04),
    ("auto", 2000, 0.001, 0.01),
])
def test_a_model_gridlabd_lacks_is_a_wye_wye(forms, unit, kva, r, x):
    """X3: WYE_WYE on winding 1's ratedS, R the ends' r plus the mesh's, X the mesh's."""
    configuration = forms.by_name(f"{unit}_config")
    assert (str(configuration.connect_type), configuration.power_rating) == ("WYE_WYE", kva)
    assert _complex(configuration.impedance) == pytest.approx(complex(r, x))


def test_three_windings_are_a_star_split(forms):
    """X4: Zi = (Zij + Zik - Zjk) / 2 on winding 1's 1000 kVA (winding 3's r 0.6 % on 500 kVA is 1.2 % there), each
    leg on its own winding's ratedS; the d winding's leg DELTA_GWYE into the 1 kV star."""
    z12, z13, z23 = complex(0.003 + 0.003, 0.08), complex(0.003 + 0.012, 0.10), complex(0.003 + 0.012, 0.06)
    star = [(z12 + z13 - z23) / 2, (z12 + z23 - z13) / 2, (z13 + z23 - z12) / 2]
    expected = [("WYE_WYE", 12470, 1000, star[0]), ("WYE_WYE", 4160, 1000, star[1]),
                ("DELTA_GWYE", 480, 500, star[2] * 500 / 1000)]
    for number, (connect_type, primary, kva, z) in enumerate(expected, start=1):
        leg = forms.by_name(f"3w_{number}")
        configuration = forms.by_name(leg.configuration)
        assert (str(configuration.connect_type), configuration.primary_voltage, configuration.secondary_voltage,
                configuration.power_rating, leg.to) == (connect_type, primary, 1000, kva, "3w_star")
        assert _complex(configuration.impedance) == pytest.approx(z)
    assert forms.by_name("3w_star").nominal_voltage == pytest.approx(1000 / math.sqrt(3))


def test_the_forms_atom_is_its_golden_and_solves(forms, tmp_path):
    path = tmp_path / "forms.glm"
    GlmWriter().write(forms, path)
    assert_text_matches_golden(path.read_text(), FORMS.with_suffix(".exported.glm"))
    voltages = solve(path)
    assert abs(voltages["3w_star"][0]) == pytest.approx(1000 / math.sqrt(3), rel=1e-3)  # no load: the ratios


TEMPLATE_CODE = """Profile = cim18v17
Object Feeder: mRID=fdr, name=fdr
Object BaseVoltage: mRID=bv_4p16kv, nominalVoltage (kV)=4.16
Table ConnectivityNode: mRID, name, BaseVoltage, ConnectivityNodeContainer=fdr
    a, a, bv_4p16kv
    b, b, bv_4p16kv
Object EnergySource: mRID=src, name=src, node=a, nominalVoltage (kV)=4.16, voltageMagnitude (kV)=4.16, BaseVoltage=bv_4p16kv, EquipmentContainer=fdr
Object PerLengthPhaseImpedance: mRID=lc_mtx, name=mtx, conductorCount=1
Table PhaseImpedanceData: identifier, PhaseImpedance=lc_mtx, row, column, r (ohm/mi), x (ohm/mi)
    d_11, 1, 1, 1.3292, 1.3475
Object WireConfiguration: mRID=wc_code, name=code, PerLengthImpedance=lc_mtx
Object ACLineSegment: mRID=ln, name=ln, node1=a, node2=b, phases=C, length (ft)=100, WireConfiguration=wc_code, BaseVoltage=bv_4p16kv, EquipmentContainer=fdr
"""


def test_a_template_line_code_is_a_matrix_configuration(tmp_path):
    """X1: a WireConfiguration with a PerLengthImpedance and no WireSpacing (a template LineCode) is not geometry: the
    line's configuration is the code's z-matrix."""
    path = tmp_path / "template_code.cimtbl"
    path.write_text(TEMPLATE_CODE)
    with cim_scope():
        model = GlmExporter().to_model(cimtables.load_model(path), name_source="name")
    line = model.by_name("ln")
    configuration = model.by_name(line.configuration)
    assert (configuration.name, configuration.spacing, configuration.conductor_C) == ("mtx", None, None)
    assert _complex(configuration.z33) == pytest.approx(complex(1.3292, 1.3475))

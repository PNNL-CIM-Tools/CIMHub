"""Tier 4: DSS import -> CIM -> GLM export, solved in GridLAB-D 6.0 against OpenDSS's own solution of the deck
(GLM_REWRITE_PLAN.md section 8, X5). It exercises the exporter on CIM the GLM importer never writes: DSS line codes
and geometry, the native transformer forms, the wye-wye replacement (X3), the three-winding star split (X4), single
-phase banks, a delta regulator bank and IEEE 8500's series reactor (X28) and triplex codes (X27).

Both engines solve one frozen state: OpenDSS with controls off, every regulated winding at CIM's tap (the deck's own
Solve has moved them) and its loads' models kept at any voltage (``Vminpu=0``, as GridLAB-D's); the GLM deck's
regulators MANUAL. A deck that sets no tap freezes at OpenDSS's solved ones (``SOLVED_TAPS``), and one past
GridLAB-D's NR at full load at a load multiplier (``LOAD_MULTIPLIER``). Decks outside git run under
``CIMHUB_DSS_DECKS``, else skip. Bus voltages are compared line to line on three-phase buses (an ungrounded delta's line-to-neutral
voltages float in either engine) and each deck's tolerance names the difference the spec lists for it.
"""
from __future__ import annotations

import cmath
import math
import os
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import gridlabd
import opendssdirect as dss
import pytest
from cimtables.graph_write import get_qty

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.tap_changer import get_tap_ratio
from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.schema import gridlabd as schema
from cimhub_opendss import DssImporter, DssReader

DECKS = Path(__file__).parents[2] / "cimhub_opendss" / "tests" / "decks" / "IEEE"

#: deck -> the worst line-to-line difference allowed, and why (EXPORT_MAPPING.md, expected differences)
TOLERANCE = {
    "IEEE13_original/IEEE13Nodeckt.dss": (1e-3, "GLM's ideal swing and regulators (X6, X5)"),
    "IEEE123/IEEE123Master.dss": (1e-4, "native forms only"),
    "IEEE4_xfmrs/4Bus-YY-Bal.DSS": (5e-4, "WYE_WYE, native"),
    "IEEE4_xfmrs/4Bus-DY-Bal.DSS": (5e-4, "DELTA_GWYE, native"),
    "IEEE4_xfmrs/4Bus-YD-Bal.DSS": (5e-3, "Y-D written WYE_WYE (X3)"),
    "IEEE4_xfmrs/4Bus-GrdYD-Bal.DSS": (5e-3, "Yn-D written WYE_WYE (X3)"),
    "IEEE13_CDPSM/IEEE13_CDPSM.dss": (5e-3, "the star split (X4) solidly grounds Sub3's Xneut winding"),
    "IEEE13_assets/IEEE13_Assets.dss": (3e-2, "geometry: each engine its own line constants"),
    "IEEE37/ieee37.dss": (3e-2, "the open-delta regulator bank written WYE_WYE (X3)"),
    "IEEE8500/Master.dss": (1e-2, "at 0.9 load and OpenDSS's solved taps; measured 5.3e-3 (m1069311), not isolated"),
}
#: decks the export must solve, with no voltage bound: the change the rule makes is the point of the deck
SOLVE_ONLY = {
    "IEEE4_xfmrs/4Bus-OYOD-Bal.DSS": "an open-delta bank written as a full WYE_WYE bank (X3)",
    "IEEE4_xfmrs/4bus-OYOD-UnBal.dss": "the same, unbalanced",
    # three Y-Y-D three-winding cans: one bank (the user's rule), star-split (X4) with a DELTA_GWYE leg; the deck's
    # later Direct solves, Show and Export leave OpenDSS in no base state, so it is no oracle
    "IEEE4_xfmrs/YYD-Master.DSS": "a bank of three-winding cans",
}


#: decks that set no regulator tap, so CIM's taps are neutral and the deck's Solve moves them: frozen there, the feeder
#: collapses (IEEE 8500: 0.70 pu, which GridLAB-D's NR does not solve). Both engines take the taps OpenDSS's own
#: controlled solve reaches, written into CIM's step before the export.
SOLVED_TAPS = {"IEEE8500/Master.dss"}
#: decks both engines solve at a load multiplier, and why: IEEE 8500's undersized secondaries put full load past what
#: GridLAB-D's NR solves (it solves at 0.9, not at 1.0 even with constant-impedance loads or 2000 iterations), so
#: OpenDSS takes ``loadmult`` and the GLM deck's loads the same factor
LOAD_MULTIPLIER = {"IEEE8500/Master.dss": 0.9}
#: the GLM load slots ``load.py`` writes a load's power in
LOAD_POWER_SLOTS = {schema.Load: ("base_power_A", "base_power_B", "base_power_C"),
                    schema.TriplexLoad: ("base_power_1", "base_power_2", "base_power_12")}


def deck_path(relative: str) -> Path:
    """The deck at ``relative`` under ``IEEE/``: vendored, else under ``CIMHUB_DSS_DECKS`` (the DSS spoke's rule for
    the decks kept out of git), else the test skips."""
    vendored = DECKS / relative
    if vendored.exists():
        return vendored
    external = os.environ.get("CIMHUB_DSS_DECKS")
    if external and (Path(external) / "IEEE" / relative).exists():
        return Path(external) / "IEEE" / relative
    pytest.skip(f"IEEE/{relative}: not vendored; set CIMHUB_DSS_DECKS to run it")


def export(relative: str, path: Path) -> dict[tuple[str, int], float]:
    """Export the deck's CIM to ``path`` (regulators MANUAL); return CIM's tap ratio per regulated DSS winding."""
    deck = deck_path(relative)
    taps = {}
    solved = solved_taps(relative) if relative in SOLVED_TAPS else {}
    with cim_scope():
        network = DssImporter(deck.stem).to_cim(DssReader(deck).read_all())
        for tap in network.graph.get(cim.RatioTapChanger, {}).values():
            end = tap.TransformerEnd
            owner = end.PowerTransformer if isinstance(end, cim.PowerTransformerEnd) else end.AutoTransformer
            if solved:
                increment = get_qty(tap, "stepVoltageIncrement", "percent")
                tap.step = tap.neutralStep + round((solved[(owner.name.lower(), end.endNumber)] - 1) * 100 / increment)
            taps[(owner.name, end.endNumber)] = get_tap_ratio(tap, which="actual")
        model = GlmExporter().to_model(network, name_source="mrid")
    for configuration in model.list_by_class(schema.RegulatorConfiguration):
        configuration.Control = "MANUAL"
    multiplier = LOAD_MULTIPLIER.get(relative, 1.0)
    for load_class, slots in LOAD_POWER_SLOTS.items():
        for load in model.list_by_class(load_class):
            for slot in slots:
                if getattr(load, slot) is not None:
                    setattr(load, slot, getattr(load, slot) * multiplier)
    GlmWriter().write(model, path)
    return taps


def solved_taps(relative: str) -> dict[tuple[str, int], float]:
    """Each winding's tap after OpenDSS's own controlled solve of the deck: ``{(transformer, winding): tap}``."""
    dss.Text.Command("Clear")
    dss.Text.Command(f"Compile [{deck_path(relative).resolve()}]")
    dss.Text.Command("Set maxiterations=100")
    dss.Text.Command(f"Set loadmult={LOAD_MULTIPLIER.get(relative, 1.0)}")
    dss.Solution.Solve()
    assert dss.Solution.Converged(), relative
    taps = {}
    for name in dss.Transformers.AllNames():
        dss.Transformers.Name(name)
        for winding in range(1, dss.Transformers.NumWindings() + 1):
            dss.Transformers.Wdg(winding)
            taps[(name.lower(), winding)] = dss.Transformers.Tap()
    return taps


def opendss_voltages(relative: str, taps: dict) -> dict[str, dict[int, complex]]:
    dss.Text.Command("Clear")
    dss.Text.Command("Set defaultbasefreq=60")
    dss.Text.Command(f"Compile [{deck_path(relative).resolve()}]")
    dss.Text.Command("Set controlmode=off")
    dss.Text.Command("Set maxiterations=100")  # a frozen state may take more than OpenDSS's 15
    dss.Text.Command(f"Set loadmult={LOAD_MULTIPLIER.get(relative, 1.0)}")
    dss.Text.Command("BatchEdit Load..* Vminpu=0 Vmaxpu=10")
    for (name, winding), ratio in taps.items():
        dss.Text.Command(f"Transformer.{name}.wdg={winding} tap={ratio}")
    dss.Solution.Solve()
    assert dss.Solution.Converged(), relative
    found = {}
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        values = dss.Bus.VMagAngle()
        found[bus.lower()] = {node: cmath.rect(values[2 * index], math.radians(values[2 * index + 1]))
                              for index, node in enumerate(dss.Bus.Nodes())}
    return found


def gridlabd_voltages(path: Path) -> dict[str, tuple[complex, complex, complex]]:
    engine = gridlabd.GridLabD()
    engine.set_working_directory(str(path.parent))
    assert engine.load_glm([path.name]) == 0, path
    engine.global_setvar("complex_output_format", "RECT")  # the bindings misread GridLAB-D's polar text
    assert engine.run() == 0, path
    return {name: tuple(engine.get_object_property_value(name, f"voltage_{phase}") for phase in "ABC")
            for cls in ("node", "substation") for name in engine.get_objects_by_class(cls)}


def worst_line_to_line(reference: dict, solved: dict) -> tuple[float, str]:
    worst, compared = (0.0, ""), 0
    for bus, nodes in reference.items():
        if bus not in solved or not all(node in nodes for node in (1, 2, 3)):
            continue
        for first, second in ((1, 2), (2, 3), (3, 1)):
            expected = abs(nodes[first] - nodes[second])
            got = abs(solved[bus][first - 1] - solved[bus][second - 1])
            worst = max(worst, (abs(got - expected) / expected, f"{bus}.{first}{second}"))
            compared += 1
    assert compared, "no three-phase bus in both engines"
    return worst


@pytest.mark.parametrize("relative", sorted(TOLERANCE))
def test_the_glm_export_solves_as_opendss(relative, tmp_path):
    path = tmp_path / "exported.glm"
    taps = export(relative, path)
    worst, where = worst_line_to_line(opendss_voltages(relative, taps), gridlabd_voltages(path))
    tolerance, why = TOLERANCE[relative]
    assert worst < tolerance, f"{relative}: {where} differs by {worst:.2e} (allowed {tolerance:.0e}: {why})"


@pytest.mark.parametrize("relative", sorted(SOLVE_ONLY))
def test_the_glm_export_solves(relative, tmp_path):
    path = tmp_path / "exported.glm"
    export(relative, path)
    assert gridlabd_voltages(path)

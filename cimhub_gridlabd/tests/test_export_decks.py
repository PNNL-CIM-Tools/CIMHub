"""X5: the exporter on whole decks. Each vendored deck that binds is exported, written and solved in GridLAB-D 6.0.

- Parity: the Java CIMHub exports (IEEE 13 cdpsm and assets, IEEE 123) solve to the original's bus voltages within
  ``PARITY_REL``. The original is run as the importer reads it (``AS_IMPORTED``): a bus GridLAB-D would make a second
  swing is a plain bus (S1-2), and a battery written CONSTANT_PF is at its CONSTANT_PQ set point (S4b-2).
- The PNNL taxonomy feeders stop at the bind: their regulators are unrated (S3c-2, ``BIND_STOPS``).
- Idempotence: a second export(import()) pass is the same text as the first.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cimhub_core.cimtbl_testing import assert_text_matches_golden
from conftest import deck, defines
from gridlabd_engine import run_file, solve, worst_difference
from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim

#: the original and the export agree to GLM's six written digits, compounded over a feeder
PARITY_REL = 1e-4
JAVA_EXPORTS = ["IEEE/IEEE13_cdpsm.glm", "IEEE/IEEE13_assets.glm", "IEEE/IEEE123.glm"]
#: (deck, text, replacement): the original as the importer reads it
AS_IMPORTED = [
    ("IEEE/IEEE13_cdpsm.glm", "  nominal_voltage 277.13;\n  bustype SWING_PQ;\n", "  nominal_voltage 277.13;\n"),
    *(("IEEE/IEEE13_cdpsm.glm", f"  P_Out {p_out};\n  four_quadrant_control_mode CONSTANT_PF;",
       f"  P_Out {p_out};\n  four_quadrant_control_mode CONSTANT_PQ;") for p_out in ("100000.000", "-5000.000",
                                                                                 "-1000.000")),
]


def export_deck(model, name: str, path: Path) -> str:
    """Import ``model``, export it under the CIM names and write it to ``path``; the deck's text."""
    network = glm_to_cim(model, name=name)
    exported = GlmExporter().to_model(network, name_source="name")
    GlmWriter().write(exported, path)
    return path.read_text()


def original_as_imported(relative: str, directory: Path) -> Path:
    body = directory / Path(relative).name
    text = deck(relative).read_text()
    for target, old, new in AS_IMPORTED:
        if target == relative:
            assert text.count(old) == 1, old
            text = text.replace(old, new)
    body.write_text(text)
    return run_file(body, defines(relative)["VSOURCE"])


@pytest.mark.parametrize("relative", JAVA_EXPORTS)
def test_the_export_solves_as_the_original(relative, scope, tmp_path):
    exported = tmp_path / "exported.glm"
    export_deck(GlmReader(deck(relative), defines=defines(relative)).read_all(), Path(relative).stem, exported)
    original = original_as_imported(relative, tmp_path)
    worst, where = worst_difference(solve(original), solve(exported))
    assert worst < PARITY_REL, f"{relative}: {where} differs by {worst:.2e}"


@pytest.mark.parametrize("relative", JAVA_EXPORTS)
def test_a_second_pass_is_a_fixed_point(relative, scope, tmp_path):
    first = export_deck(GlmReader(deck(relative), defines=defines(relative)).read_all(), Path(relative).stem,
                        tmp_path / "first.glm")
    second = export_deck(GlmReader(tmp_path / "first.glm").read_all(), Path(relative).stem, tmp_path / "second.glm")
    assert second == first


def test_the_ieee13_golden(scope, tmp_path):
    """The exported IEEE13_cdpsm deck is committed beside the importer's golden (D6), so a diff shows a change."""
    text = export_deck(GlmReader(deck(JAVA_EXPORTS[0]), defines=defines(JAVA_EXPORTS[0])).read_all(), "IEEE13_cdpsm",
                       tmp_path / "IEEE13_cdpsm.glm")
    assert_text_matches_golden(text, Path(__file__).parent / "goldens" / "IEEE13_cdpsm" / "IEEE13_cdpsm.exported.glm")

"""S7: series reactors: classification, the atom, GridLAB-D's per-phase impedance through the core getter, fail
fast; the decks run in test_cimtbl_sweep.py."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_core.getters.series_compensator import get_series_compensator
from cimhub_core.getters.terminals import get_conductor_phases
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.cimtbl import series_reactor
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim

ATOM = Path(__file__).parent / "atoms" / "series_reactor"
MODEL = "atom"


def read(path: Path):
    return GlmReader(path).read_all()


def test_every_slot_is_classified():
    check_fields(series_reactor.FIELDS, series_reactor.NATIVE_CLASS)


def test_atom_golden():
    part = next(part for part in GlmImporter(MODEL).to_cimtbl(read(ATOM / "series_reactor.glm")).parts
                if part.name == "series_reactor")
    assert_matches_golden(part, ATOM / "series_reactor.series_reactor.cimtbl")


def test_atom_binds(scope):
    network = glm_to_cim(read(ATOM / "series_reactor.glm"), name=MODEL)
    compensators = {str(item.mRID): item for item in network.list_by_class(cim.SeriesCompensator)}
    assert sorted(compensators) == ["rx_hsb", "rx_r1"]
    # GridLAB-D's phase impedance is r + jx on every phase; no coupling, so the zero sequence equals it
    assert tuple(get_series_compensator(compensators["rx_hsb"])[:4]) == pytest.approx((0, 14.798307, 0, 14.798307))
    assert tuple(get_series_compensator(compensators["rx_r1"])[:4]) == pytest.approx((0.5, 2, 0.5, 2))
    assert get_conductor_phases(compensators["rx_hsb"]) == (cim.SinglePhaseKind.A, cim.SinglePhaseKind.B,
                                                            cim.SinglePhaseKind.C)
    assert get_conductor_phases(compensators["rx_r1"]) == (cim.SinglePhaseKind.B,)


def raises(tmp_path, reactor: str, match: str):
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "series_reactor.glm"}"\nobject node {{ name x1; phases ABCN; '
                    f'nominal_voltage 2401.78; }}\nobject series_reactor {{ name x; from rb1; to x1; {reactor} }}\n')
    with pytest.raises(ValueError, match=match):
        GlmImporter(MODEL).to_cimtbl(read(path))


def test_unequal_phases_raise(tmp_path):
    raises(tmp_path, "phases AB; phase_A_impedance 0+1j; phase_B_impedance 0+2j;",
           "one impedance for every phase")


def test_an_unset_phase_raises(tmp_path):
    raises(tmp_path, "phases AB; phase_A_impedance 0+1j;", "phase_B_impedance unset; GridLAB-D's 0 is a switch")


def test_the_impedance_parts_raise(tmp_path):
    raises(tmp_path, "phases A; phase_A_impedance 0+1j; phase_A_resistance 0.1;",
           "phase_A_resistance set; only phase_X_impedance is mapped")


def test_open_raises(tmp_path):
    raises(tmp_path, "phases A; phase_A_impedance 0+1j; status OPEN;", "status OPEN on a device that is not a switch")

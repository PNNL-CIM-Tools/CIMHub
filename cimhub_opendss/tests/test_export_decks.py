"""Whole decks through import and export (EXPORT_MAPPING.md S6f): power flow parity in the engine, the bus
coordinates, and idempotence (a second pass is a fixed point)."""
from __future__ import annotations

from pathlib import Path

import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssImporter, DssReader
from cimhub_opendss.exporter.cim_to_dss import cim_to_dss

from conftest import deck
from engine_compare import assert_same_power_flow, engine_coordinates
from test_cimtbl_sweep import SWEEP_STOPS

_ROUNDTRIP = pytest.mark.roundtrip
_LIMITS, _PPM = "Load.Vminpu/Vmaxpu", "Transformer.ppm_antifloat"
_TAPS, _CAPS, _EARTH = "Transformer.taps", "Capacitor.states", "earthmodel"
#: decks the engine compiles here -> what the parity solve took from the original (engine_compare.UNTRANSCRIBED).
#: earthmodel is listed only on decks without geometry (S6g): there it has no EarthResistivity and computes nothing.
#: Not here: YYD-Master (it ends in a fault study and writes result files beside itself), IEEE8500 Master-unbal (it
#: redirects a file the original lacks).
PARITY = {
    "IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss": {_EARTH, _LIMITS},
    "IEEE/IEEE13_original/IEEE13Nodeckt.dss": {_TAPS},
    "IEEE/IEEE123/IEEE123Master.dss": {_PPM},
    "IEEE/IEEE37/ieee37.dss": {_TAPS},
    "IEEE/IEEE13_assets/IEEE13_Assets.dss": {_CAPS},
    "IEEE/IEEE4_xfmrs/4Bus-DY-Bal.DSS": {_LIMITS},
    "IEEE/IEEE4_xfmrs/4Bus-GrdYD-Bal.DSS": {_LIMITS},
    "IEEE/IEEE4_xfmrs/4Bus-OYOD-Bal.DSS": {_LIMITS},
    "IEEE/IEEE4_xfmrs/4Bus-YD-Bal.DSS": {_LIMITS},
    "IEEE/IEEE4_xfmrs/4Bus-YY-Bal.DSS": {_LIMITS},
    "IEEE/IEEE4_xfmrs/4bus-OYOD-UnBal.dss": {_LIMITS, _PPM},
    "IEEE/IEEE123_PV/IEEE123Master_fixedVR.dss": {_EARTH, _PPM, _TAPS},
    "IEEE/IEEE123_deconfliction/IEEE123Master.dss": {_PPM, _TAPS},
    "IEEE/IEEE8500/Master.dss": {_LIMITS, _PPM},
    "PNNL/IEEE9500/Master-unbal-initial-config.dss": {_EARTH, _LIMITS, _PPM, _TAPS},
    "UAF/ACEP_PSIL.dss": {_EARTH},
}
#: decks under CIMHUB_DSS_DECKS (not vendored): slow, so marked roundtrip
EXTERNAL = {"IEEE/IEEE123_PV/IEEE123Master_fixedVR.dss", "IEEE/IEEE123_deconfliction/IEEE123Master.dss",
            "IEEE/IEEE8500/Master.dss", "IEEE/IEEE8500/Master-unbal.dss",
            "PNNL/IEEE9500/Master-unbal-initial-config.dss", "UAF/ACEP_PSIL.dss"}
#: every sweep deck that binds
BINDING = sorted(relative for relative, stop in SWEEP_STOPS.items() if stop is None)


def _decks(relatives):
    return [pytest.param(relative, marks=_ROUNDTRIP) if relative in EXTERNAL else relative for relative in relatives]


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _export(original: Path, written: Path) -> Path:
    cim_to_dss(DssImporter(original.stem).to_cim(DssReader(original).read_all()), written, name_source="name")
    return written


@pytest.mark.parametrize("relative", _decks(PARITY))
def test_deck_solves_alike_and_keeps_its_coordinates(relative, tmp_path):
    original = deck(relative)
    written = _export(original, tmp_path / original.name)
    assert assert_same_power_flow(original, written) == PARITY[relative]
    assert engine_coordinates(written) == engine_coordinates(original)


@pytest.mark.parametrize("relative", _decks(BINDING))
def test_second_export_is_a_fixed_point(relative, tmp_path):
    first = _export(deck(relative), tmp_path / "first" / Path(relative).name)
    second = _export(first, tmp_path / "second" / first.name)
    assert second.read_text(encoding="utf-8") == first.read_text(encoding="utf-8")
    for csv in first.parent.glob("*.csv"):
        assert (second.parent / csv.name).read_text(encoding="utf-8") == csv.read_text(encoding="utf-8"), csv.name

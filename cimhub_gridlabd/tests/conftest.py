"""Shared fixtures for the GridLAB-D tests.

Decks: the small public decks are vendored in ``tests/decks/`` (origins in its README). The others stay out of git;
point ``CIMHUB_GLM_DECKS`` at a directory with the same layout (``PNNL/orig_R5-12.47-3.glm``) to run them,
otherwise their tests skip.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from cimhub_core.cimtbl_testing import cim_scope

DECKS = Path(__file__).parent / "decks"

#: The Java CIMHub exports reference ``${VSOURCE}`` without defining it (GLM-15): the source's phase-to-neutral
#: volts on 115 kV, as ``gridlabd -D VSOURCE=...`` would pass it.
DEFINES = {"VSOURCE": "66395.28"}

#: Every public Powergrid-Models GLM deck, by its path under ``models/feeders/GridLABD``.
ALL_DECKS = [
    "IEEE/IEEE13_cdpsm.glm", "IEEE/IEEE13_assets.glm", "IEEE/IEEE13_houses.glm", "IEEE/IEEE123.glm",
    "IEEE/IEEE123_transactive.glm",
    *(f"PNNL/orig_{feeder}.glm" for feeder in (
        "GC-12.47-1", "R1-12.47-1", "R1-12.47-2", "R1-12.47-3", "R1-12.47-4", "R1-25.00-1", "R2-12.47-1",
        "R2-12.47-2", "R2-12.47-3", "R2-25.00-1", "R2-35.00-1", "R3-12.47-1", "R3-12.47-2", "R3-12.47-3",
        "R4-12.47-1", "R4-12.47-2", "R4-25.00-1", "R5-12.47-1", "R5-12.47-2", "R5-12.47-3", "R5-12.47-4",
        "R5-12.47-5", "R5-25.00-1", "R5-35.00-1")),
]

#: The vendored decks.
VENDORED_DECKS = [
    "IEEE/IEEE13_cdpsm.glm", "IEEE/IEEE13_assets.glm", "IEEE/IEEE13_houses.glm", "IEEE/IEEE123.glm",
    "PNNL/orig_GC-12.47-1.glm", "PNNL/orig_R1-12.47-3.glm",
]


def deck(relative: str) -> Path:
    """The deck at ``relative``: vendored, else under ``CIMHUB_GLM_DECKS``, else the test skips."""
    vendored = DECKS / relative
    if vendored.exists():
        return vendored
    external = os.environ.get("CIMHUB_GLM_DECKS")
    if external and (Path(external) / relative).exists():
        return Path(external) / relative
    pytest.skip(f"{relative}: not vendored; set CIMHUB_GLM_DECKS to run it")


def deck_params(stops: dict[str, str]) -> list:
    """``ALL_DECKS`` as pytest params: the vendored ones run by default, the rest only with ``--roundtrip``; each
    carries the error it is expected to stop with (``None`` for a deck that goes through)."""
    return [pytest.param(relative, stops.get(relative), id=relative,
                         marks=() if relative in VENDORED_DECKS else pytest.mark.roundtrip)
            for relative in ALL_DECKS]


def pytest_addoption(parser):
    parser.addoption("--roundtrip", action="store_true", default=False,
                     help="run the tests on the decks that are not vendored (marked roundtrip)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--roundtrip"):
        return
    skip = pytest.mark.skip(reason="external deck; pass --roundtrip (and set CIMHUB_GLM_DECKS) to run it")
    for item in items:
        if "roundtrip" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def scope():
    """Put back the CIM profile and model scope a ``.cimtbl`` load sets process-wide."""
    with cim_scope():
        yield

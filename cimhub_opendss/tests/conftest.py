"""Shared fixtures for the OpenDSS tests.

Decks: the small public decks are vendored in ``tests/decks/`` (origins in its README). The large ones
(EPRI J1, IEEE8500, IEEE9500, ...) stay out of git; point ``CIMHUB_DSS_DECKS`` at a directory with the same
layout (``IEEE/IEEE8500/Master.dss``) to run them, otherwise their tests skip.
"""
from __future__ import annotations

import os
from pathlib import Path

import opendssdirect
import pytest
from cimtables.document import Document

from cimhub_core.cimtbl import CIM_PROFILE
from cimhub_opendss.importer.dss_to_cimtbl import limit_types

# OpenDSS ``Compile`` chdirs the whole process into the deck's directory; once a temp dir is gone the next
# ``Compile`` segfaults. Keep the process cwd fixed.
opendssdirect.Basic.AllowChangeDir(False)
# ``Show`` and ``FileEdit`` in a deck open the result in an editor window and block until it closes.
opendssdirect.Basic.AllowEditor(False)

DECKS = Path(__file__).parent / "decks"

#: Decks the engine compiles here (K1 and M1 redirect with the wrong file-name case for Linux).
ENGINE_DECKS = [
    "IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss",
    "IEEE/IEEE13_original/IEEE13Nodeckt.dss",
    "IEEE/IEEE123/IEEE123Master.dss",
    "IEEE/IEEE37/ieee37.dss",
    "IEEE/IEEE4_xfmrs/4bus-OYOD-UnBal.dss",
    "IEEE/IEEE13_assets/IEEE13_Assets.dss",
    pytest.param("IEEE/IEEE13_OCHRE/Master.dss", marks=pytest.mark.roundtrip),
    pytest.param("EPRI/J1/Master.dss", marks=pytest.mark.roundtrip),
    pytest.param("IEEE/IEEE8500/Master.dss", marks=pytest.mark.roundtrip),
    pytest.param("PNNL/IEEE9500/Master-unbal-initial-config.dss", marks=pytest.mark.roundtrip),
]


#: The engine's ``LineUnits`` codes as length units.
ENGINE_UNIT = {1: "mi", 2: "kft", 3: "km", 4: "m", 5: "ft", 6: "in", 7: "cm", 8: "mm"}

#: Decks with wire catalogs and geometries the engine compiles here (not YYD-Master: its Export commands write
#: files next to the deck).
CATALOG_DECKS = [
    "IEEE/IEEE13_assets/IEEE13_Assets.dss",
    "IEEE/IEEE4_xfmrs/4Bus-YY-Bal.DSS",
]


def clear_engine() -> None:
    """Clear the engine's circuit. ``Set defaultbasefreq`` outlives ``Clear``, so it is put back to the engine's
    60 Hz too: a 50 Hz deck must not change the next deck's frequency."""
    opendssdirect.Text.Command("Clear")
    opendssdirect.Text.Command("Set defaultbasefreq=60")


def compile_deck(path: Path) -> None:
    """Compile a deck in the engine, from a clean circuit."""
    clear_engine()
    opendssdirect.Text.Command(f"Compile [{path.resolve()}]")


def deck(relative: str) -> Path:
    """The deck at ``relative`` (``IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss``): vendored, else under
    ``CIMHUB_DSS_DECKS``, else the test skips."""
    vendored = DECKS / relative
    if vendored.exists():
        return vendored
    external = os.environ.get("CIMHUB_DSS_DECKS")
    if external and (Path(external) / relative).exists():
        return Path(external) / relative
    pytest.skip(f"{relative}: not vendored; set CIMHUB_DSS_DECKS to run it")


def pytest_addoption(parser):
    parser.addoption("--roundtrip", action="store_true", default=False,
                     help="run the slow whole-deck tests (marked roundtrip)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--roundtrip"):
        return
    skip = pytest.mark.skip(reason="whole-deck test; pass --roundtrip to run")
    for item in items:
        if "roundtrip" in item.keywords:
            item.add_marker(skip)


def limits() -> Document:
    """The master's OperationalLimitTypes as a part of their own, for atoms that bind rated catalogs or lines."""
    return Document(name="limits", statements=[limit_types()], profile=CIM_PROFILE)

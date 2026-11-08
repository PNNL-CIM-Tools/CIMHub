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

# OpenDSS ``Compile`` chdirs the whole process into the deck's directory; once a temp dir is gone the next
# ``Compile`` segfaults. Keep the process cwd fixed.
opendssdirect.Basic.AllowChangeDir(False)

DECKS = Path(__file__).parent / "decks"


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

"""Unit tests for the export naming switch (name, mRID or uri)."""

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.names import NAME_SOURCE_ENV, export_name, resolve_name_source


def test_name_source_argument_wins_over_the_environment(monkeypatch):
    monkeypatch.setenv(NAME_SOURCE_ENV, "uri")
    assert resolve_name_source("name") == "name"
    assert resolve_name_source() == "uri"


def test_name_source_defaults_to_mrid(monkeypatch):
    monkeypatch.delenv(NAME_SOURCE_ENV, raising=False)
    assert resolve_name_source() == "mrid"


def test_unknown_name_source_raises(monkeypatch):
    with pytest.raises(ValueError, match="name source must be one of"):
        resolve_name_source("safename")
    monkeypatch.setenv(NAME_SOURCE_ENV, "MRID")
    with pytest.raises(ValueError, match="not 'MRID'"):
        resolve_name_source()


def test_export_name_reads_name_mrid_or_uri():
    source = cim.EnergySource(mRID="src_source", name="source")
    assert export_name(source, "name") == "source"
    assert export_name(source, "mrid") == "src_source"
    assert export_name(source, "uri") == source.uri()
    assert len(export_name(source, "uri")) == 36


def test_export_name_unset_or_blank_raises():
    with pytest.raises(ValueError, match="EnergySource 'src_x': has no name"):
        export_name(cim.EnergySource(mRID="src_x"), "name")
    with pytest.raises(ValueError, match="has no name"):
        export_name(cim.EnergySource(mRID="src_y", name="  "), "name")

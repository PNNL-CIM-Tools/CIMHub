"""Unit tests for clean_cim_name — the CIM-name/lookup-key/bus-id sanitizer."""

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core import clean_cim_name
from cimhub_core.names import NAME_SOURCE_ENV, export_name, resolve_name_source


def test_strips_xml_illegal_characters():
    # The <NULL> case that broke the exported CIM XML: no < or > survives.
    cleaned = clean_cim_name("Cable_1P_1C_2GA_AL-<NULL>")
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert cleaned == "Cable_1P_1C_2GA_AL-_NULL_"


def test_strips_dss_delimiter_dot():
    # The "." is the OpenDSS node delimiter; a coordinate-pair NodeID must not
    # keep it or the bus name parses into bus/node fragments.
    assert clean_cim_name("7674067.786_551037.964") == "7674067_786_551037_964"


def test_clean_name_is_returned_unchanged():
    assert clean_cim_name("SAFE_NAME_123") == "SAFE_NAME_123"


def test_is_idempotent():
    once = clean_cim_name("Cable-<NULL> (bad)")
    assert clean_cim_name(once) == once


def test_none_returns_default():
    assert clean_cim_name(None) == "UNKNOWN"
    assert clean_cim_name(None, default="SOURCE") == "SOURCE"


def test_empty_and_whitespace_return_default():
    assert clean_cim_name("") == "UNKNOWN"
    assert clean_cim_name("   ") == "UNKNOWN"


def test_non_string_is_coerced():
    assert clean_cim_name(1234) == "1234"


@pytest.mark.parametrize("ch", ['<', '>', '&', '"', "'", "[", "]", "{", "}",
                                 "(", ")", ",", "=", "~", "|", ".", " "])
def test_each_unsafe_character_is_replaced(ch):
    assert ch not in clean_cim_name(f"a{ch}b")


# --- export naming (DSS_REWRITE_PLAN.md E1) ---


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

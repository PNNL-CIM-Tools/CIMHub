"""Unit tests for clean_cim_name — the CIM-name/lookup-key/bus-id sanitizer."""

import pytest

from cimhub_core import clean_cim_name


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

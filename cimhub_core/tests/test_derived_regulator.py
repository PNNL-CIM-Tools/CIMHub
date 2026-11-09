"""cimhub_core.derived.regulator: PT-secondary settings and their primary values (IEEE13_CDPSM Reg1's)."""

import pytest

from cimhub_core.derived.regulator import line_drop_ohms, line_drop_volts, primary_to_secondary, secondary_to_primary


def test_band_centre_is_primary_volts_and_back():
    assert secondary_to_primary(122, 20) == 2440
    assert primary_to_secondary(2440, 20) == 122


def test_line_drop_is_primary_ohms_and_back():
    ohms = line_drop_ohms(3, 20, 700)
    assert ohms == pytest.approx(3 * 20 / 700, rel=1e-15)
    assert line_drop_volts(ohms, 20, 700) == pytest.approx(3, rel=1e-15)

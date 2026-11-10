"""cimhub_core.derived.control_band: a CapControl's ON/OFF pair and CIM's target and deadband (caps atom's)."""

from cimhub_core.derived.control_band import band_from_on_off, on_off_from_band


def test_voltage_band_has_on_below_off():
    assert band_from_on_off(115, 125) == (120, 10)
    assert on_off_from_band(120, 10, on_above=False) == (115, 125)


def test_kvar_band_has_on_above_off():
    assert band_from_on_off(150, -225) == (-37.5, 375)
    assert on_off_from_band(-37.5, 375, on_above=True) == (150, -225)

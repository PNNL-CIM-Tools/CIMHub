"""cimhub_core.derived.capacitance: b = 2 pi f C and its inverse (plan E5)."""

import math

import pytest

from cimhub_core.derived.capacitance import b_from_c, c_from_b


def test_b_from_c_in_nano_units():
    assert b_from_c(3.4, 60.0) == pytest.approx(2 * math.pi * 60 * 3.4)
    assert b_from_c(0.0, 60.0) == 0.0


@pytest.mark.parametrize("c, frequency", [(10.4308823411236, 60.0), (4.6658, 50.0), (-0.8999, 60.0)])
def test_c_from_b_inverts_b_from_c(c, frequency):
    assert c_from_b(b_from_c(c, frequency), frequency) == pytest.approx(c, rel=1e-12)


def test_c_from_b_needs_a_positive_frequency():
    with pytest.raises(ValueError, match="positive frequency"):
        c_from_b(1.0, 0.0)

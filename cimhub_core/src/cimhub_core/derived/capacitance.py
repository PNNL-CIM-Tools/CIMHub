"""Shunt susceptance and capacitance at one frequency: b = 2 pi f C (plan E5).

The units go with the values: C in nF and f in Hz give b in nS, and back. A caller reads b with ``get_qty`` in nS
(per its length unit) and gets C in nF (per the same length), so no unit factor appears here.
"""

from __future__ import annotations

import math


def b_from_c(c: float, frequency: float) -> float:
    """Susceptance from capacitance: b = 2 pi f C. C in nF and f in Hz give b in nS."""
    return 2 * math.pi * frequency * c


def c_from_b(b: float, frequency: float) -> float:
    """Capacitance from susceptance: C = b / (2 pi f). b in nS and f in Hz give C in nF."""
    if frequency <= 0:
        raise ValueError(f"a capacitance needs a positive frequency, not {frequency}")
    return b / (2 * math.pi * frequency)

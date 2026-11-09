"""A switched control's ON/OFF pair as a CIM target and deadband, and back (S6d; EPRI ExportCIMXML's convention).

A DSS CapControl switches at two settings, ON and OFF. CIM's ``RegulatingControl`` holds the band's midpoint
(``targetValue``) and its full width (``targetDeadband``, positive). Which side ON is on follows from the control's
mode: below OFF when the control acts on a falling value (voltage, time), above it when on a rising one (current,
reactive power). So the pair is rebuilt without a sign.
"""

from __future__ import annotations


def band_from_on_off(on: float, off: float) -> tuple[float, float]:
    """``(target, deadband)``: the midpoint and full width of the ON/OFF band."""
    return (on + off) / 2, abs(off - on)


def on_off_from_band(target: float, deadband: float, *, on_above: bool) -> tuple[float, float]:
    """``(on, off)`` of the band ``target`` +- ``deadband`` / 2; ``on_above``: ON is the upper setting."""
    low, high = target - deadband / 2, target + deadband / 2
    return (high, low) if on_above else (low, high)

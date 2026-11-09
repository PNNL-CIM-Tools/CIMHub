"""Voltage regulator settings between the PT secondary and the primary (S6c; the importer's pair moved here).

A regulator relay works on its PT secondary: a band centre in volts on the 120 V side, and a line drop compensator
in volts at rated CT current. CIM holds both on the primary: target volts, and line drop ohms. ``ptratio`` is the PT
ratio and ``ct_primary`` the CT primary rating in A, so every conversion is a ratio and no unit factor appears.
"""

from __future__ import annotations


def secondary_to_primary(volts: float, ptratio: float) -> float:
    """A setting in volts on the PT secondary as primary volts."""
    return volts * ptratio


def primary_to_secondary(volts: float, ptratio: float) -> float:
    """Primary volts as a setting in volts on the PT secondary."""
    return volts / ptratio


def line_drop_ohms(volts: float, ptratio: float, ct_primary: float) -> float:
    """A line drop compensator setting in volts (at rated CT current) as primary ohms."""
    return volts * ptratio / ct_primary


def line_drop_volts(ohms: float, ptratio: float, ct_primary: float) -> float:
    """Primary line drop ohms as a compensator setting in volts at rated CT current."""
    return ohms * ct_primary / ptratio

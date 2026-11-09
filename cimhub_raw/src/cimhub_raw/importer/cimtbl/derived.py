"""Derived values of the RAW mappers: named, tested functions, each stated in the mapping spec.

A value is derived only where CIM has no attribute for the source quantity, or (``kv_from_per_unit``) where the
per-unit base sits one association further than cimtables reaches (RAW-14, RAW-19).
"""

from __future__ import annotations


def kv_from_per_unit(per_unit: float, base_kv: float) -> float:
    """A voltage in kV from a per-unit value on a base in kV: kV = pu x base.

    Bus voltage limits (NVHI, NVLO, EVHI, EVLO) and solved bus voltages (VM) are pu of the bus's BASKV.
    """
    return per_unit * base_kv

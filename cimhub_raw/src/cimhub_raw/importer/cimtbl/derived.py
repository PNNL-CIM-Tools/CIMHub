"""Derived values of the RAW mappers: named, tested functions, each stated in the mapping spec.

A value is derived only where CIM has no attribute for the source quantity, or (``kv_from_per_unit``) where the
per-unit base sits one association further than cimtables reaches (RAW-14, RAW-19), or (``ka_from_rating``) where
the source states a current as a power.
"""

from __future__ import annotations

import math

from cimprofiles.units.units import ureg


def kv_from_per_unit(per_unit: float, base_kv: float) -> float:
    """A voltage in kV from a per-unit value on a base in kV: kV = pu x base.

    Bus voltage limits (NVHI, NVLO, EVHI, EVLO) and solved bus voltages (VM) are pu of the bus's BASKV.
    """
    return per_unit * base_kv


def ka_from_rating(rating_mva: float, base_kv: float) -> float:
    """A current in kA from a rating "in current expressed as MVA" (NXFRAT/XFRRAT > 0; RAW-9).

    The spec's MVA_rated = sqrt(3) x E_base x I_rated, so kA = MVA / (sqrt(3) x kV).
    """
    return rating_mva / (math.sqrt(3) * base_kv)


def volts_from_per_unit(per_unit: float, base_kv: float) -> float:
    """A voltage in V from a per-unit value on a base in kV, through the units library: a ``RegulatingControl``
    target is a plain float in V for mode voltage (switched shunt VSWHI/VSWLO; R2)."""
    return ureg.Quantity(per_unit * base_kv, "kV").to("V").magnitude


def per_unit_from_mva(value_mva: float, base_mva: float) -> float:
    """An admittance in pu on the system base from "MW / Mvar at one per unit voltage": pu = value / SBASE.

    Fixed shunt GL/BL and switched shunt Bi (R2); cimtables then converts ``(pu system)`` on nomU and SBASE.
    """
    return value_mva / base_mva


def load_p_q(record) -> tuple[float, float]:
    """A load's p (MW) and q (Mvar) at 1 pu voltage, CIM's nominal: p = PL + IP + YP, q = QL + IQ - YQ.

    YQ is negative for an inductive load (RAW v34), so it enters q with a minus sign.
    """
    p = record.constant_real_power + record.constant_current_real_power + record.constant_admittance_real_power
    q = record.constant_imag_power + record.constant_current_imag_power - record.constant_admittance_imag_power
    return p, q


def _side_fractions(components: tuple[float, float, float], side: str, record_id) -> tuple[float, float, float]:
    total = sum(components)
    if not any(components):
        return 1.0, 0.0, 0.0
    if total == 0:
        raise ValueError(f"load {record_id}: the {side} components {components} cancel to 0; their ZIP fractions "
                         "are undefined")
    return tuple(0.0 if part == 0 else part / total for part in components)


def zip_mix(record) -> tuple[float, ...]:
    """The six ZIP fractions of a load: p constant power, current, impedance, then q's.

    p: PL/p, IP/p, YP/p; q: QL/q, IQ/q, -YQ/q. A side whose components are all 0 counts as constant power; a side
    whose nonzero components cancel raises.
    """
    p_side = (record.constant_real_power, record.constant_current_real_power, record.constant_admittance_real_power)
    q_side = (record.constant_imag_power, record.constant_current_imag_power, -record.constant_admittance_imag_power)
    return _side_fractions(p_side, "p", record.ID) + _side_fractions(q_side, "q", record.ID)


def block_sections(binit: float, blocks: list[tuple[int, float]], record_id) -> list[float]:
    """The sections in service of each switched-shunt block ``(Ni, Bi)``, from the total BINIT (Mvar at 1 pu).

    RAW's switching order (ADJM = 0): BINIT < 0 fills the reactor blocks (Bi < 0) in input order, BINIT > 0 the
    capacitor blocks. Each block in turn takes up to its Ni steps; the block where BINIT runs out takes the rest as
    a fraction of a step (CIM allows a non-integer ``sections``: MODSW 2, or an ADJM = 1 combination with the same
    total). BINIT beyond the blocks' total raises.
    """
    tolerance = 1e-9 * max(1.0, abs(binit))
    sections = [0.0] * len(blocks)
    remaining = binit
    for index, (steps, step) in enumerate(blocks):
        if abs(remaining) <= tolerance:
            break
        if (step < 0) != (remaining < 0):
            continue
        sections[index] = min(float(steps), remaining / step)
        remaining -= sections[index] * step
    if abs(remaining) > tolerance:
        raise ValueError(f"switched shunt {record_id}: BINIT={binit!r} is beyond its blocks {blocks}")
    return sections

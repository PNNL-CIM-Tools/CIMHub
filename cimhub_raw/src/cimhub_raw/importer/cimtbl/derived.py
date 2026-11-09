"""Derived values of the RAW mappers: named, tested functions, each stated in the mapping spec.

A value is derived only where CIM has no attribute for the source quantity, or (``kv_from_per_unit``) where the
per-unit base sits one association further than cimtables reaches (RAW-14, RAW-19), or (``ka_from_rating``) where
the source states a current as a power.
"""

from __future__ import annotations

import math
from typing import NamedTuple

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


def ohms_from_per_unit(per_unit: float, base_kv: float, base_mva: float) -> float:
    """An impedance in ohm from pu on a base kV and MVA: ohm = pu x kV^2 / MVA (kV^2 / MVA is exactly ohm).

    Generator ZR, in pu on the machine's MBASE and its bus's BASKV (R3).
    """
    return per_unit * base_kv ** 2 / base_mva


def siemens_from_per_unit(per_unit: float, base_kv: float, base_mva: float) -> float:
    """An admittance in S from pu on a base kV and MVA: S = pu x MVA / kV^2 (MVA / kV^2 is exactly S).

    Transformer MAG1/MAG2 (CM 1, R4).
    """
    return per_unit * base_mva / base_kv ** 2


def vars_from_mvar(value_mvar: float) -> float:
    """A reactive power in VAr from Mvar, through the units library: a ``TapChangerControl`` target in mode
    reactivePower (transformer COD 2 VMA/VMI, R4)."""
    return ureg.Quantity(value_mvar, "MVAr").to("VAr").magnitude


def _per_unit_from_watts(watts: float, base_mva: float) -> float:
    """A loss in W as pu of a base in MVA."""
    return ureg.Quantity(watts, "W").to("MW").magnitude / base_mva


def transformer_ohms(r: float, x: float, cz: int, *, base_kv: float, nominal_kv: float, pair_mva: float,
                     system_mva: float, record_id) -> tuple[float, float]:
    """A transformer winding pair's (r, x) in ohm, seen from winding i, from RAW's R/X under impedance code CZ (R4):

    - CZ 1: pu on SBASE and bus i's BASKV;
    - CZ 2: pu on the pair's SBASEij and NOMVi (``nominal_kv``: NOMVi, or BASKV when 0);
    - CZ 3: R = the load loss in W, X = |Z| in pu on SBASEij and NOMVi; r = loss / SBASEij, x = sqrt(|Z|^2 - r^2).

    PSS/E's own conversion between the codes keeps these ohms the same. CZ 3 with |Z| < r raises.
    """
    if cz == 1:
        return ohms_from_per_unit(r, base_kv, system_mva), ohms_from_per_unit(x, base_kv, system_mva)
    if cz == 2:
        return ohms_from_per_unit(r, nominal_kv, pair_mva), ohms_from_per_unit(x, nominal_kv, pair_mva)
    if cz == 3:
        r_per_unit = _per_unit_from_watts(r, pair_mva)
        if x < r_per_unit:
            raise ValueError(f"{record_id}: CZ 3 |Z| = {x} pu is less than its load-loss r = {r_per_unit} pu")
        x_per_unit = math.sqrt(x ** 2 - r_per_unit ** 2)
        return ohms_from_per_unit(r_per_unit, nominal_kv, pair_mva), ohms_from_per_unit(x_per_unit, nominal_kv, pair_mva)
    raise ValueError(f"{record_id}: CZ {cz} is not an impedance code (1, 2, 3)")


def magnetizing_siemens(mag1: float, mag2: float, cm: int, *, base_kv: float, nominal_kv: float, pair_mva: float,
                        system_mva: float, record_id) -> tuple[float, float]:
    """A transformer's magnetizing (g, b) in S at winding 1, from RAW's MAG1/MAG2 under admittance code CM (R4):

    - CM 1: G, B in pu on SBASE and bus 1's BASKV;
    - CM 2: MAG1 = the no-load loss in W, MAG2 = the exciting current I in pu on SBASE1-2 and NOMV1; g = loss /
      SBASE1-2, b = -sqrt(I^2 - g^2) (inductive).

    The sign of a CM 1 B is kept: CIM's b allows either. CM 2 with I < g raises.
    """
    if cm == 1:
        return siemens_from_per_unit(mag1, base_kv, system_mva), siemens_from_per_unit(mag2, base_kv, system_mva)
    if cm == 2:
        g_per_unit = _per_unit_from_watts(mag1, pair_mva)
        if mag2 < g_per_unit:
            raise ValueError(f"{record_id}: CM 2 exciting current {mag2} pu is less than its no-load-loss g = "
                             f"{g_per_unit} pu")
        b_per_unit = 0.0 - math.sqrt(mag2 ** 2 - g_per_unit ** 2)
        return siemens_from_per_unit(g_per_unit, nominal_kv, pair_mva), siemens_from_per_unit(b_per_unit, nominal_kv,
                                                                                              pair_mva)
    raise ValueError(f"{record_id}: CM {cm} is not a magnetizing code (1, 2)")


def winding_unit_kv(cw: int, base_kv: float, nominal_kv: float, record_id) -> float:
    """The kV of one unit of a winding's WINDV, RMA and RMI under winding code CW (R4): pu of the bus's BASKV (1),
    kV (2), or pu of NOMV (3; ``nominal_kv``: NOMV, or BASKV when 0)."""
    units = {1: base_kv, 2: 1.0, 3: nominal_kv}
    if cw not in units:
        raise ValueError(f"{record_id}: CW {cw} is not a winding code (1, 2, 3)")
    return units[cw]


class TapPosition(NamedTuple):
    """A ``RatioTapChanger``'s neutral and position over steps 1..NTP (``ratio_tap``)."""

    neutral_step: int
    neutral_kv: float
    increment_percent: float
    step: float


def ratio_tap(windv: float, rma: float, rmi: float, ntp: int, *, unit_kv: float, rated_kv: float,
              record_id) -> TapPosition:
    """A winding's tap over steps 1..NTP, from RMI (step 1) to RMA (step NTP) in equal steps (R4, RAW-6).

    WINDV, RMA and RMI are in winding units of ``unit_kv`` kV (``winding_unit_kv``):

    - stepVoltageIncrement = (RMA - RMI) / (NTP - 1), in percent of ratedU;
    - neutralStep = the step nearest ratio 1 (WINDV x unit = ratedU; a tie takes the upper), and neutralU = the
      voltage at that step: CIM's neutralStep is an integer, and RAW's ratio 1 often falls between steps;
    - step = neutralStep + (WINDV - the neutral ratio) / the step size, a float (CIM allows a non-integer
      step); measured from the neutral, so a WINDV at ratio 1 is exactly neutralStep.

    NTP < 2, RMA <= RMI, or a WINDV outside RMI..RMA (CIM: lowStep <= step <= highStep) raises.
    """
    if ntp < 2:
        raise ValueError(f"{record_id}: NTP {ntp} gives no tap range (at least 2 positions)")
    if rma <= rmi:
        raise ValueError(f"{record_id}: RMA {rma} is not above RMI {rmi}")
    if not rmi <= windv <= rma:
        raise ValueError(f"{record_id}: WINDV {windv} is outside RMI..RMA ({rmi}..{rma})")
    step_size = (rma - rmi) / (ntp - 1)
    nearest = math.floor((rated_kv / unit_kv - rmi) / step_size + 0.5)
    neutral_offset = min(max(nearest, 0), ntp - 1)
    neutral = rmi + step_size * neutral_offset
    return TapPosition(
        neutral_step=1 + neutral_offset,
        neutral_kv=neutral * unit_kv,
        increment_percent=ureg.Quantity(step_size * unit_kv / rated_kv, "").to("percent").magnitude,
        step=1 + neutral_offset + (windv - neutral) / step_size,
    )


def generation_p_q(record) -> tuple[float, float]:
    """A generator's (p, q) under the CIM load sign convention: (-PG, -QG), with 0 kept 0.0, not -0.0 (R3)."""
    return 0.0 - record.p_output, 0.0 - record.q_output


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

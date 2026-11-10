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


def per_unit_from_kv(kv: float, base_kv: float) -> float:
    """The exporter's inverse of ``kv_from_per_unit``: pu = kV / base."""
    return kv / base_kv


def ka_from_rating(rating_mva: float, base_kv: float) -> float:
    """A current in kA from a rating "in current expressed as MVA" (NXFRAT/XFRRAT > 0; RAW-9).

    The spec's MVA_rated = sqrt(3) x E_base x I_rated, so kA = MVA / (sqrt(3) x kV).
    """
    return rating_mva / (math.sqrt(3) * base_kv)


def rating_from_ka(current_ka: float, base_kv: float) -> float:
    """The exporter's inverse of ``ka_from_rating``: MVA = sqrt(3) x kV x kA."""
    return math.sqrt(3) * base_kv * current_ka


def volts_from_per_unit(per_unit: float, base_kv: float) -> float:
    """A voltage in V from a per-unit value on a base in kV, through the units library: a ``RegulatingControl``
    target is a plain float in V for mode voltage (switched shunt VSWHI/VSWLO; R2)."""
    return ureg.Quantity(per_unit * base_kv, "kV").to("V").magnitude


def per_unit_from_mva(value_mva: float, base_mva: float) -> float:
    """An admittance in pu on the system base from "MW / Mvar at one per unit voltage": pu = value / SBASE.

    Fixed shunt GL/BL and switched shunt Bi (R2); cimtables then converts ``(pu system)`` on nomU and SBASE.
    """
    return value_mva / base_mva


def mva_from_per_unit(per_unit: float, base_mva: float) -> float:
    """"MW / Mvar at one per unit voltage" from an admittance in pu on the system base: value = pu x SBASE.

    The inverse of ``per_unit_from_mva``: the exporter's fixed shunt GL/BL and switched shunt Bi/BINIT (E2).
    """
    return per_unit * base_mva


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


def watts_from_mw(value_mw: float) -> float:
    """An active power in W from MW, through the units library: a ``TapChangerControl`` target in mode activePower
    (transformer COD 3 VMA/VMI, R4b)."""
    return ureg.Quantity(value_mw, "MW").to("W").magnitude


def vars_from_mvar(value_mvar: float) -> float:
    """A reactive power in VAr from Mvar, through the units library: a ``TapChangerControl`` target in mode
    reactivePower (transformer COD 2 VMA/VMI, R4)."""
    return ureg.Quantity(value_mvar, "MVAr").to("VAr").magnitude


def reactive_band(vswlo: float, vswhi: float, q_min_mvar: float, q_max_mvar: float) -> tuple[float, float]:
    """A switched shunt's reactive-power ``(targetValue, targetDeadband)`` in VAr (MODSW 3 and 6, R2b).

    VSWLO..VSWHI are pu of the controlled device's range q_min..q_max (Mvar, output sign): the band is
    q_min + VSWLO x span .. q_min + VSWHI x span. The target is its midpoint under the CIM load sign at the device's
    terminal (-midpoint, 0 kept 0.0, as the machine's q = -QG); the deadband is its width.
    """
    span = q_max_mvar - q_min_mvar
    low, high = q_min_mvar + vswlo * span, q_min_mvar + vswhi * span
    return vars_from_mvar(0.0 - (low + high) / 2), vars_from_mvar(high - low)


def band_fractions(target_mvar: float, deadband_mvar: float, q_min_mvar: float,
                   q_max_mvar: float) -> tuple[float, float]:
    """A switched shunt's ``(VSWLO, VSWHI)`` from its reactive-power target and deadband in Mvar at the device's
    terminal (CIM load sign), as pu of the device's range q_min..q_max (Mvar, output sign): the inverse of
    ``reactive_band`` (the exporter's MODSW 3 and 6, E2). A range of zero width raises."""
    span = q_max_mvar - q_min_mvar
    if span == 0:
        raise ValueError(f"the reactive range {q_min_mvar}..{q_max_mvar} Mvar has no width; VSWLO/VSWHI are "
                         "fractions of it")
    middle = 0.0 - target_mvar
    low, high = middle - deadband_mvar / 2, middle + deadband_mvar / 2
    return (low - q_min_mvar) / span, (high - q_min_mvar) / span


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
    """A ``RatioTapChanger``'s steps, neutral and position (``ratio_tap``)."""

    low_step: int
    high_step: int
    neutral_step: int
    neutral_kv: float
    increment_percent: float
    step: float


def usable_tap_range(windv: float, rma: float, rmi: float) -> bool:
    """Whether RMI..RMA is a tap range that holds WINDV: RMA > RMI and RMI <= WINDV <= RMA (R4b-4)."""
    return rma > rmi and rmi <= windv <= rma


def ratio_tap(windv: float, rma: float, rmi: float, ntp: int, *, unit_kv: float, rated_kv: float,
              record_id) -> TapPosition:
    """A winding's tap over steps 1..NTP, from RMI (step 1) to RMA (step NTP) in equal steps (R4, RAW-6).

    WINDV, RMA and RMI are in winding units of ``unit_kv`` kV (``winding_unit_kv``):

    - stepVoltageIncrement = (RMA - RMI) / (NTP - 1), in percent of ratedU;
    - neutralStep = the step nearest ratio 1 (WINDV x unit = ratedU; a tie takes the upper), and neutralU = the
      voltage at that step: CIM's neutralStep is an integer, and RAW's ratio 1 often falls between steps;
    - step = neutralStep + (WINDV - the neutral ratio) / the step size, a float (CIM allows a non-integer
      step); measured from the neutral, so a WINDV at ratio 1 is exactly neutralStep;
    - a WINDV outside RMI..RMA extends lowStep below 1 or highStep above NTP to the first whole step past it
      (R4b-5; CIM: lowStep <= step <= highStep).

    NTP < 2 or RMA <= RMI raises.
    """
    if ntp < 2:
        raise ValueError(f"{record_id}: NTP {ntp} gives no tap range (at least 2 positions)")
    if rma <= rmi:
        raise ValueError(f"{record_id}: RMA {rma} is not above RMI {rmi}")
    step_size = (rma - rmi) / (ntp - 1)
    nearest = math.floor((rated_kv / unit_kv - rmi) / step_size + 0.5)
    neutral_offset = min(max(nearest, 0), ntp - 1)
    neutral = rmi + step_size * neutral_offset
    step = 1 + neutral_offset + (windv - neutral) / step_size
    return TapPosition(
        low_step=min(1, math.floor(step)),
        high_step=max(ntp, math.ceil(step)),
        neutral_step=1 + neutral_offset,
        neutral_kv=neutral * unit_kv,
        increment_percent=ureg.Quantity(step_size * unit_kv / rated_kv, "").to("percent").magnitude,
        step=step,
    )


def cim_angle(angle_degrees: float) -> float:
    """A PSS/E angle in CIM's sign (R4b-1): PSS/E's ANG is positive when the winding's bus leads the transformer's
    internal voltage; CIM's ``phaseShift`` and ``PhaseTapChanger`` angles are positive from the terminal into the
    transformer, the opposite. Used for ANGk, a shifter's step, and an impedance table's angle points."""
    return 0.0 - angle_degrees  # not -angle: 0.0 stays 0.0, not -0.0


class PhaseTap(NamedTuple):
    """A ``PhaseTapChangerLinear``'s neutral, increment and position (``phase_tap``), and how far PSS/E's 0 deg lies
    off its grid."""

    neutral_step: int
    increment_degrees: float  # in CIM's sign
    step: float
    zero_offset_degrees: float  # PSS/E's angle at neutralStep: 0 when 0 deg is on the grid


def phase_tap(angle: float, rma: float, rmi: float, ntp: int, record_id) -> PhaseTap:
    """A phase shifter's tap (COD +-3, R4b-3) over steps 1..NTP from RMI to RMA (PSS/E angles, deg):

    - neutralStep = the step nearest 0 deg (a tie takes the upper); CIM has no neutral angle, so a shifter whose
      0 deg falls between steps moves its end steps' angles by that offset (``zero_offset_degrees``);
    - stepPhaseShiftIncrement = (RMA - RMI) / (NTP - 1), in CIM's sign (``cim_angle``);
    - step = neutralStep + ANG / the step size, a float, so ANG itself is exact.

    NTP < 2, RMA <= RMI, or an ANG outside RMI..RMA raises.
    """
    if ntp < 2:
        raise ValueError(f"{record_id}: NTP {ntp} gives no tap range (at least 2 positions)")
    if rma <= rmi:
        raise ValueError(f"{record_id}: RMA {rma} is not above RMI {rmi}")
    if not rmi <= angle <= rma:
        raise ValueError(f"{record_id}: ANG {angle} is outside RMI..RMA ({rmi}..{rma})")
    step_size = (rma - rmi) / (ntp - 1)
    neutral_offset = min(max(math.floor(-rmi / step_size + 0.5), 0), ntp - 1)
    return PhaseTap(neutral_step=1 + neutral_offset, increment_degrees=cim_angle(step_size),
                    step=1 + neutral_offset + angle / step_size,
                    zero_offset_degrees=rmi + step_size * neutral_offset)


def impedance_deviation_percent(factor: float) -> float:
    """An impedance correction factor F as CIM's deviation in percent of the nominal impedance, 100 x (F - 1),
    through the units library (``ImpedanceTapChangerTablePoint.rEnd1``/``xEnd1``, R4b-10)."""
    return ureg.Quantity(factor - 1.0, "").to("percent").magnitude


def is_angle_table(t_values: list[float]) -> bool:
    """PSS/E's rule for an impedance correction table (R4b-10): a first T below 0.5 or a last T above 1.5 makes it
    a table of phase shift angles (deg); otherwise of off-nominal turns ratios."""
    return t_values[0] < 0.5 or t_values[-1] > 1.5


def net_import(pdes: float) -> float:
    """``ControlArea.netInterchange`` (MW, positive into the area) from PDES (MW, the desired net export): -PDES,
    written ``0.0 - PDES`` so that 0 stays ``0.0`` (R5)."""
    return 0.0 - pdes


def net_export(net_interchange: float) -> float:
    """The exporter's inverse of ``net_import``: PDES (MW) = -netInterchange, ``0.0 - ...`` so 0 stays ``0.0``."""
    return 0.0 - net_interchange


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


#: valves per six-pulse bridge (a two-terminal DC converter's NB bridges in series)
VALVES_PER_BRIDGE = 6


def converter_transformer_ohms(per_bridge_ohm: float, bridges: int, ratio: float) -> float:
    """A two-terminal converter's equivalent transformer r or x on end 1, in ohm (P2-5): RC / XC are per bridge on
    the valve side (EBAS x TR), and the NB bridges' transformers are in parallel on the AC side, so
    Z1 = Z_bridge / (NB x TR^2)."""
    return per_bridge_ohm / (bridges * ratio ** 2)


def converter_tap(tap: float, tmx: float, tmn: float, stp: float, *, ebas_kv: float, record_id) -> tuple[TapPosition,
                                                                                                         float]:
    """A converter transformer's tap on end 1 (P2-5): ``ratio_tap`` over the STP grid from TMN (step 1) up to the
    last whole step at or below TMX, so stepVoltageIncrement is exactly STP; TAP is a ratio of EBAS. Returns the tap
    and the grid's top ratio, which differs from TMX when TMX - TMN is no whole number of steps."""
    if stp <= 0:
        raise ValueError(f"{record_id}: STP {stp} must be positive")
    positions = math.floor((tmx - tmn) / stp + 1e-9) + 1
    top = tmn + (positions - 1) * stp
    return ratio_tap(tap, top, tmn, positions, unit_kv=ebas_kv, rated_kv=ebas_kv, record_id=record_id), top

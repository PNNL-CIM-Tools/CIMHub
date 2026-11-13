"""A shunt compensator's reactive power (skill `export-getters`, semantic rule 4).

One formula: Q = bPerSection × V² × sections. The caller names both factors:

- ``sections``: ``'actual'`` (sections), ``'normal'`` (normalSections) or ``'maximum'`` (maximumSections);
- ``voltage``: ``'nominal'`` (``nomU``, the rating ``bPerSection`` was derived on; DSS and GLM) or ``'base'`` (the
  BaseVoltage; RAW's B at 1 pu). ``nomU`` is across the unit: phase to neutral for one phase conductor, else line to
  line, so the base voltage is read in the same form.

Positive Q is a capacitor's (CIM ``nomQ`` sign). Per phase is the total split evenly over the phase conductors.
``nomQ`` is not read (b and nomU are), and a set ``gPerSection`` or per-phase ``bPerSection`` raises until a producer
writes one.

**Admittance** (bus-branch formats: RAW's G + jB): g and b of the sections in service, ``gPerSection`` and
``bPerSection`` times the section count, in siemens or in pu on the shunt's ``nomU`` and the system base power
(``cimtables.impedance.z_base``, as a ``(pu system)`` column writes it). An unset ``gPerSection`` is 0.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.terminals import get_conductor_phases

# which sections -> the ShuntCompensator attribute that holds them
SECTIONS_ATTRIBUTE = {"actual": "sections", "normal": "normalSections", "maximum": "maximumSections"}
VOLTAGES = ("nominal", "base")
ADMITTANCE_UNITS = ("S", "pu")


class ShuntReactivePower(NamedTuple):
    phases: tuple[cim.SinglePhaseKind, ...]  # the phase conductors; no neutral
    connection: cim.PhaseShuntConnectionKind | None
    grounded: bool | None
    voltage: float  # voltage_unit: the V in Q = b V² n
    sections: float
    total: float  # unit
    per_phase: dict[cim.SinglePhaseKind, float]


class ShuntAdmittance(NamedTuple):
    g: float  # unit, the sections in service; 0 when gPerSection is unset
    b: float
    sections: float


def get_shunt_reactive_power(shunt: cim.LinearShuntCompensator, unit: str = "VAr", *, sections: str, voltage: str,
                             voltage_unit: str = "V") -> ShuntReactivePower:
    """Q of the ``sections`` in service at the ``voltage`` base, in total and per phase."""
    if voltage not in VOLTAGES:
        raise ValueError(f"voltage must be one of {list(VOLTAGES)}, not {voltage!r}")
    _check_linear(shunt)
    if shunt.gPerSection is not None:
        raise ValueError(f"{describe(shunt)}: gPerSection is not read")

    phases = tuple(phase for phase in get_conductor_phases(shunt) if phase is not cim.SinglePhaseKind.N)
    b = required_qty(shunt, "bPerSection", "S")
    if voltage == "nominal":
        volts = required_qty(shunt, "nomU", "V")
    else:
        volts = get_base_voltage(shunt, "V", form="LN" if len(phases) == 1 else "LL")
    count = _section_count(shunt, sections)

    total = cim.ReactivePower(b * volts ** 2 * count).to(unit)
    return ShuntReactivePower(
        phases=phases,
        connection=shunt.phaseConnection,
        grounded=shunt.grounded,
        voltage=cim.Voltage(volts).to(voltage_unit),
        sections=count,
        total=total,
        per_phase={phase: total / len(phases) for phase in phases},
    )


def get_shunt_admittance(shunt: cim.LinearShuntCompensator, unit: str = "S", *, sections: str,
                         base_power=None) -> ShuntAdmittance:
    """g and b of the ``sections`` in service, in ``unit`` (module docstring). ``base_power`` is
    ``network.base_power``, needed for 'pu'."""
    if unit not in ADMITTANCE_UNITS:
        raise ValueError(f"unit must be one of {list(ADMITTANCE_UNITS)}, not {unit!r}")
    _check_linear(shunt)
    count = _section_count(shunt, sections)
    b = required_qty(shunt, "bPerSection", unit, system_base=base_power)
    g = get_qty(shunt, "gPerSection", unit, system_base=base_power) or 0.0
    return ShuntAdmittance(g=g * count, b=b * count, sections=count)


def _check_linear(shunt) -> None:
    if not isinstance(shunt, cim.LinearShuntCompensator):
        raise ValueError(f"{describe(shunt)}: only a LinearShuntCompensator has a susceptance per section")
    if any(getattr(phase, "bPerSection", None) is not None for phase in shunt.ShuntCompensatorPhase):
        raise ValueError(f"{describe(shunt)}: a per-phase bPerSection is not read")


def _section_count(shunt, sections: str) -> float:
    if sections not in SECTIONS_ATTRIBUTE:
        raise ValueError(f"sections must be one of {sorted(SECTIONS_ATTRIBUTE)}, not {sections!r}")
    count = getattr(shunt, SECTIONS_ATTRIBUTE[sections])
    if count is None:
        raise ValueError(f"{describe(shunt)}: {SECTIONS_ATTRIBUTE[sections]} is unset")
    return count

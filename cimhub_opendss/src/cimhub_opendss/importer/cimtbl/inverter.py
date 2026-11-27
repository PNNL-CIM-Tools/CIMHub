"""The ``PowerElectronicsConnection`` row of an inverter-based DSS device (PVSystem, Storage), shape ``der``.

The CIM load sign throughout: generation and discharge are negative p, and q = -kvar (S4b-1). ratedU is line to
line (``injection.line_kv``, S4b-4). maxQ/minQ are the inverter's kvar limits, maxIFault is 1 / Vminpu (the
engine's CIM export convention: the per-unit current a constant-power inverter reaches at Vminpu).

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md``, section S4b.
"""

from __future__ import annotations

from cimtables.document import Column, Row

from cimhub_core.cimtbl import cell, mrid, phases_cell
from cimhub_opendss.importer.cimtbl.injection import DeviceTerminal, line_kv

CONNECTION = "PowerElectronicsConnection"


def max_fault_current(vminpu: float) -> float:
    """``maxIFault`` (per unit of rated current) of an inverter that holds its power down to ``vminpu``."""
    if vminpu <= 0:
        raise ValueError(f"Vminpu={vminpu} must be positive")
    return 1 / vminpu


def connection_columns(container: str) -> list[Column]:
    return [Column("mRID"), Column("name"), Column("node"), Column("phases"), Column("phaseConnection"),
            Column("ratedS", "kVA"), Column("ratedU", "kV"), Column("p", "kW"), Column("q", "kVAr"),
            Column("maxQ", "kVAr"), Column("minQ", "kVAr"), Column("maxIFault"), Column("normallyInService"),
            Column("BaseVoltage"), Column("EquipmentContainer", default=container)]


def connection_row(prefix: str, device, terminal: DeviceTerminal, *, kva: float, p: float, q: float,
                   comment: str | None) -> Row:
    """The connection row of ``device`` (defaults filled): ``p``/``q`` in kW/kvar, already in the load sign (a
    negated zero is written as 0)."""
    kvar_max = float(device.kvarMax) if device.kvarMax is not None else kva
    kvar_max_abs = float(device.kvarMaxAbs) if device.kvarMaxAbs is not None else kva
    return Row([
        mrid(prefix, device.name, lowercase=True), str(device.name), terminal.bus, phases_cell(terminal.phases),
        terminal.connection, cell(kva), cell(line_kv(float(device.kv), terminal)), cell(p + 0.0), cell(q + 0.0),
        cell(kvar_max), cell(-kvar_max_abs + 0.0), cell(max_fault_current(float(device.Vminpu))), cell(device.enabled),
        terminal.system.base_voltage,
    ], comment=comment)


def unit_id(prefix: str, device) -> str:
    """``<pec>_unit``: the PhotoVoltaicUnit or BatteryUnit of a connection."""
    return f"{mrid(prefix, device.name, lowercase=True)}_unit"

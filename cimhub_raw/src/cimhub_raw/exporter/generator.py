"""SynchronousMachine, PowerElectronicsConnection (+ unit, plant control, step-up) -> Generator
(``EXPORT_MAPPING.md#e3-generator``).

The inverse of the importer's R3, R3b and R3c. A machine on a node without a busNumber sits behind a step-up
(R3b, the core shape ``behind_transformer``): its RT, XT and GTAP come back from that transformer, which
``step_ups`` names so that E4 leaves it out. IREG, VS and RMPCT are plant quantities, shared by the machines at bus I.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_core.getters import describe
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.control import get_regulating_control
from cimhub_core.getters.der import (get_der_output, get_inverter_rating, get_inverter_unit, get_machine_impedance,
                                     get_machine_rating, get_unit_limits)
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.tap_changer import get_tap_steps
from cimhub_core.getters.transformer import get_transformer_model, get_transformer_units
from cimhub_raw.exporter.bus import raw_bus
from cimhub_raw.exporter.identity import keyed_ids
from cimhub_raw.importer.cimtbl.derived import per_unit_from_kv
from cimhub_raw.importer.cimtbl.generator import CONVERTER_PREFIXES, FIXED_POWER_FACTOR, MACHINE_PREFIXES

NATIVE_CLASS = schema.GeneratorRecord
CIM_CLASSES = (cim.SynchronousMachine, cim.PowerElectronicsConnection)
PREFIX = {cim.SynchronousMachine: MACHINE_PREFIXES[0], cim.PowerElectronicsConnection: CONVERTER_PREFIXES[0]}
CONVENTIONAL, RENEWABLE = 0, 1  # WMOD; WMOD 2 comes back 1 (X1)
ID_WIDTH = 2
REL_TOL = 1e-9

_NO_HOME = Slot("unset", "ownership is an asset concept (CIM 18 gap)")
_PLANT = "a plant quantity: the machines at bus I must agree, else it raises"
SLOTS = {NATIVE_CLASS: {
    "bus_number": Slot("written", "I: the busNumber of the machine's node, or of the bus across its step-up (raw_bus)"),
    "gen_id": Slot("written", "ID: the sm_<I>_<ID> / pec_<I>_<ID> key, else the next free (X2)"),
    "p_output": Slot("written", "PG: get_der_output(sign='generation').total p (MW)"),
    "q_output": Slot("written", "QG: get_der_output(sign='generation').total q (Mvar)"),
    "max_q_output": Slot("written", "QT: get_machine_rating / get_inverter_rating(sign='generation').max_q (Mvar)"),
    "min_q_output": Slot("written", "QB: get_machine_rating / get_inverter_rating(sign='generation').min_q (Mvar)"),
    "regulated_voltage_setpoint": Slot("written", "VS: a voltage control's get_regulating_control target as pu of "
                                                  f"the regulated bus's BASKV; blank for WMOD 3; {_PLANT}"),
    "regulated_bus_number": Slot("written", "IREG: the busNumber of raw_bus of the voltage control's terminal, its "
                                            f"own bus included (E3-4); blank for WMOD 3; {_PLANT}"),
    "rated_mva": Slot("written", "MBASE: the rating's rated_s (MVA)"),
    "zr": Slot("written", "ZR: a SynchronousMachine's get_machine_impedance('pu').r, on its ratedU and ratedS "
                          "(BASKV, MBASE; E3-1); a connection's has no CIM home (R3c-3)"),
    "zx": Slot("unset", "ZX: cim18v17 has no positive-sequence machine reactance (UPSTREAM U13)"),
    "rt": Slot("written", "RT: the step-up's winding r summed, pu on MBASE (get_transformer_model); 0 without one"),
    "xt": Slot("written", "XT: the step-up's mesh (1, 2) x, pu on MBASE (get_transformer_model); 0 without one"),
    "gtap": Slot("written", "GTAP: neutralU / ratedU1 of the step-up's fixed tap (get_tap_steps), 1 without a tap; "
                            "blank without a step-up (R3b-4's GTAP has no CIM home)"),
    "status": Slot("rule", "STAT: 0 when inService is false, else 1"),
    "rmpct": Slot("written", "RMPCT: the qPercent of the plant's SynchronousMachines (get_machine_rating), on every "
                             f"record of the plant; a plant of connections only has no CIM home (R3c-3); {_PLANT}"),
    "max_p_output": Slot("written", "PT: get_unit_limits(sign='generation').max_p of the GeneratingUnit or the "
                                    "connection's PowerElectronicsUnit (MW)"),
    "min_p_output": Slot("written", "PB: get_unit_limits(sign='generation').min_p (MW)"),
    **{f"{kind}{n}": _NO_HOME for n in range(1, 5) for kind in ("o", "f")},
    "wmod": Slot("written", "WMOD: SynchronousMachine 0; PowerElectronicsConnection 3 under a powerFactor control, "
                            "else 1 (WMOD 2 has no CIM home, R3c-1)"),
    "wpf": Slot("written", "WPF: WMOD 3: the powerFactor control's target, as stored (signed, R3c-2); else blank"),
    "nreg": Slot("unset", "NREG: a node of a node-breaker bus, written by E5"),
}}


def step_ups(context) -> dict[cim.PowerTransformer, object]:
    """Each implicit step-up transformer (R3b) with the machine behind it. E4 leaves these out."""
    return {_step_up(device): device for device in context.objects(*CIM_CLASSES)
            if _node(device) not in context.bus_numbers}


def export(context) -> list[schema.GeneratorRecord]:
    """One Generator per machine or connection, by key."""
    devices = [(device, context.bus_numbers[raw_bus(_node(device), context)])
               for device in context.objects(*CIM_CLASSES)]
    ids = keyed_ids([(device, PREFIX[type(device)], (bus,)) for device, bus in devices], ID_WIDTH)
    plants: dict[int, list] = {}
    for device, bus in devices:
        plants.setdefault(bus, []).append(device)
    records = []
    for bus, members in plants.items():
        regulation = _plant_regulation(bus, members, context)
        rmpct = _plant_rmpct(bus, members)
        for device in members:
            records.append(_record(device, bus, ids[device], regulation, rmpct, context))
    return sorted(records, key=lambda record: (record.bus_number, record.gen_id))


def _node(device) -> cim.TopologicalNode:
    return device.Terminals[0].TopologicalNode


def _record(device, bus: int, gen_id: str, regulation: tuple, rmpct: float | None,
            context) -> schema.GeneratorRecord:
    output = get_der_output(device, "MW", "MVAr", sign="generation").total
    if isinstance(device, cim.SynchronousMachine):
        rating = get_machine_rating(device, "MVA", "MVAr", sign="generation", voltage_unit="kV")
        unit, zr, wmod, wpf = device.GeneratingUnit, get_machine_impedance(device, "pu").r, CONVENTIONAL, None
    else:
        rating = get_inverter_rating(device, "MVA", "MVAr", sign="generation", voltage_unit="kV")
        unit, zr, wmod, wpf = get_inverter_unit(device), None, RENEWABLE, _power_factor(device)
        if wpf is not None:
            wmod, regulation = FIXED_POWER_FACTOR, (None, None)
    min_p, max_p = (None, None) if unit is None else get_unit_limits(unit, "MW", sign="generation")
    rt, xt, gtap = (0.0, 0.0, None) if _node(device) in context.bus_numbers else _fold_back(device, rating.rated_s,
                                                                                             context)
    ireg, vs = regulation
    return schema.GeneratorRecord(
        bus_number=bus, gen_id=gen_id, p_output=output.p, q_output=output.q, max_q_output=rating.max_q,
        min_q_output=rating.min_q, regulated_voltage_setpoint=vs, regulated_bus_number=ireg,
        rated_mva=rating.rated_s, zr=zr, rt=rt, xt=xt, gtap=gtap,
        status=0 if get_in_service(device, which="actual") is False else 1, rmpct=rmpct, max_p_output=max_p,
        min_p_output=min_p, wmod=wmod, wpf=wpf)


def _power_factor(connection) -> float | None:
    """The target of a powerFactor control (WMOD 3, R3c-2), as stored; None under any other control."""
    control = connection.RegulatingControl
    if control is None or control.mode is not cim.RegulatingControlModeKind.powerFactor:
        return None
    return get_regulating_control(control).target


def _plant_regulation(bus: int, members: list, context) -> tuple[int | None, float | None]:
    """``(IREG, VS)`` of the plant's voltage control; blank without one. Members that disagree raise."""
    found = set()
    for device in members:
        control = device.RegulatingControl
        if control is None or (isinstance(device, cim.PowerElectronicsConnection) and _power_factor(device)
                               is not None):
            continue
        if control.mode is not cim.RegulatingControlModeKind.voltage:
            raise ValueError(f"{describe(control)} of {describe(device)}: mode {control.mode}; a plant regulates "
                             "voltage, or a connection its power factor")
        regulated = raw_bus(control.Terminal.TopologicalNode, context)
        target_kv = get_regulating_control(control, "kV").target
        found.add((context.bus_numbers[regulated],
                   per_unit_from_kv(target_kv, get_base_voltage(regulated, "kV", form="LL"))))
    if len(found) > 1:
        raise ValueError(f"plant {bus}: its machines' controls disagree on (IREG, VS): {sorted(found)}; PSS/E treats "
                         "them as plant quantities")
    return found.pop() if found else (None, None)


def _plant_rmpct(bus: int, members: list) -> float | None:
    """The qPercent of the plant's SynchronousMachines, for every record of it; None when none has one."""
    percents = {get_machine_rating(device, sign="generation").q_percent for device in members
                if isinstance(device, cim.SynchronousMachine)} - {None}
    if len(percents) > 1:
        raise ValueError(f"plant {bus}: its machines' qPercent disagree: {sorted(percents)}; RMPCT is a plant "
                         "quantity")
    return percents.pop() if percents else None


def _step_up(device) -> cim.PowerTransformer:
    """The one transformer that, with the device, is all a step-up's internal node holds; anything else raises."""
    node = _node(device)
    others = [terminal.ConductingEquipment for terminal in node.Terminal if terminal.ConductingEquipment is not device]
    if len(others) != 1 or not isinstance(others[0], cim.PowerTransformer):
        raise ValueError(f"{describe(device)}: its {describe(node)} has no busNumber and holds "
                         f"{[describe(other) for other in others]}; a step-up's node holds the machine and one "
                         "transformer")
    return others[0]


def _fold_back(device, mbase: float, context) -> tuple[float, float, float]:
    """``(RT, XT, GTAP)`` of the device's step-up (R3b inverted), pu on MBASE."""
    transformer = _step_up(device)
    if get_in_service(transformer, which="actual") is False:
        raise ValueError(f"{describe(transformer)}: out of service; a RAW step-up has no status of its own")
    [unit] = get_transformer_units(transformer)
    model = get_transformer_model(unit, "pu", base_power=mbase, voltage_unit="kV", power_unit="MVA")
    if len(model.windings) != 2 or any(model.core):
        raise ValueError(f"{describe(transformer)}: {len(model.windings)} windings, core {tuple(model.core)}; a RAW "
                         "step-up is 2 windings without a core")
    first, second = model.windings
    if first.end.Terminal.TopologicalNode not in context.bus_numbers or \
            second.end.Terminal.TopologicalNode is not _node(device):
        raise ValueError(f"{describe(transformer)}: a step-up has winding 1 on the bus and winding 2 on "
                         f"{describe(device)}'s node")
    for winding in (first, second):
        base_kv = get_base_voltage(winding.end.Terminal.TopologicalNode, "kV", form="LL")
        if not math.isclose(winding.rated_u, base_kv, rel_tol=REL_TOL):
            raise ValueError(f"{describe(winding.end)}: ratedU {winding.rated_u} kV is not its node's BaseVoltage "
                             f"{base_kv} kV; RAW's step-up is per unit on both")
    if second.end.RatioTapChanger is not None or first.end.PhaseTapChanger is not None \
            or second.end.PhaseTapChanger is not None:
        raise ValueError(f"{describe(transformer)}: a RAW step-up has only a ratio tap on winding 1")
    mesh = model.mesh[(1, 2)]
    rt = (first.r or 0.0) + (second.r or 0.0) + (mesh.r or 0.0)
    return rt, mesh.x, _gtap(first)


def _gtap(first) -> float:
    """neutralU / ratedU1 of winding 1's fixed ratio tap; 1 without one. A tap that moves raises."""
    tap = first.end.RatioTapChanger
    if tap is None:
        return 1.0
    steps = get_tap_steps(tap, "kV")
    if steps.low != steps.high or steps.neutral_u is None:
        raise ValueError(f"{describe(tap)}: steps {steps.low}..{steps.high}, neutralU {steps.neutral_u}; GTAP is one "
                         "fixed ratio")
    return per_unit_from_kv(steps.neutral_u, first.rated_u)

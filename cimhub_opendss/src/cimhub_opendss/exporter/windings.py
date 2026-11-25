"""A transformer unit's DSS winding values, shared by the Transformer, XfmrCode and RegControl modules
(``EXPORT_MAPPING.md#s6c-transformers-xfmrcode-regulators-regcontrol``).

Every value comes from ``get_transformer_model`` on the base DSS puts its percents on: winding 1's kVA (T1). A coil
(a 1-phase unit, a regulator) is written with its own ``baseU``/``baseS``, so a center-tap half carries the can's
kVA as every deck writes it; a 3-phase unit with its nameplate ``ratedU`` (LL) and ``ratedS``. An AutoTransformer has
no core and no winding r: its mesh r is split over the two windings (T7, the engine's stand-in, DSS-13).
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.tap_changer import get_tap_ratio, get_tap_steps
from cimhub_core.getters.transformer import (TransformerForm, TransformerModel, Winding, get_transformer_model,
                                             get_transformer_units)
from cimhub_opendss.exporter.buses import bus_ref
from cimhub_opendss.exporter.naming import Names

TRANSFORMER_CLASSES = (cim.PowerTransformer, cim.AutoTransformer, cim.VoltageRegulator)
NAMESPACE = "Transformer"
TEMPLATE_FORMS = (TransformerForm.BY_TANK_ENDS, TransformerForm.BY_LUGS)
PHASE, N = cim.SinglePhaseKind, cim.SinglePhaseKind.N
THREE_PHASES = (PHASE.A, PHASE.B, PHASE.C)
#: T6: a wye neutral that is not solidly grounded goes on its own node (on node 0 an Rneut would be shorted); an
#: ungrounded coil neutral too, so a bank's cans share one floating neutral on the bus
NEUTRAL_NODE = 4
COIL_NEUTRAL_NODE = 0
CONNECTION = {cim.WindingConnection.D: "delta", cim.WindingConnection.Y: "wye", cim.WindingConnection.Yn: "wye",
              cim.WindingConnection.I: "wye"}
#: (i, j) mesh -> the Transformer slot (XfmrCode spells them Xhl, Xht, Xlt)
MESH_SLOTS = {(1, 2): "XHL", (1, 3): "XHT", (2, 3): "XLT"}


class UnitModel(NamedTuple):
    unit: object  # a TransformerTank, a PowerTransformer without tanks, or an AutoTransformer
    model: TransformerModel  # on winding 1's DSS kVA, voltages in kV, powers in kVA
    conductors: tuple[cim.SinglePhaseKind, ...]  # a polyphase unit's phase conductors (``_conductors``); () a coil
    kvas: tuple[float, ...]  # each winding's DSS kVA

    @property
    def polyphase(self) -> bool:
        return bool(self.conductors)


def units(transformer) -> tuple:
    """The transformer's units (``get_transformer_units``): one DSS Transformer each (T4)."""
    return get_transformer_units(transformer)


def unit_name(transformer, unit, names: Names) -> str:
    """A transformer with one unit is named by itself, each tank of a several-tank one by the tank (T4)."""
    if len(units(transformer)) == 1:
        return names.name(transformer, NAMESPACE)
    return names.name(unit, NAMESPACE)


def read_unit(unit) -> UnitModel:
    """The unit's model on winding 1's DSS kVA."""
    stored = get_transformer_model(unit, voltage_unit="kV", power_unit="kVA")
    if len(stored.windings) not in (2, 3):
        raise ValueError(f"{describe(unit)}: has {len(stored.windings)} windings; 2 or 3 are mapped (Xscarray is not)")
    conductors = _conductors(unit, stored.windings)
    kvas = tuple(_kva(unit, winding, bool(conductors)) for winding in stored.windings)
    model = get_transformer_model(unit, base_power=kvas[0], voltage_unit="kV", power_unit="kVA")
    return UnitModel(unit, model, conductors, kvas)


def winding_values(unit_model: UnitModel) -> dict:
    """The values a Transformer and an XfmrCode share, under the Transformer's slot names."""
    unit, model, conductors, kvas = unit_model
    auto = model.form is TransformerForm.AUTO
    return dict(
        phases=len(conductors) or 1,
        windings=len(model.windings),
        conns=[_connection(unit, winding, auto) for winding in model.windings],
        kVs=[winding_kv(unit_model, winding) for winding in model.windings],
        kVAs=list(kvas),
        pct_Rs=_resistances(unit_model),
        **_reactances(unit_model),
        pct_imag=model.core.b,
        pct_noloadloss=model.core.g,
        **_neutral_impedance(unit_model),
        RdcOhms=_dc_resistances(unit_model),
    )


def _dc_resistances(unit_model: UnitModel) -> list[float] | None:
    """Each winding's rDC (ohm), when the windings have them (a tank's or a template's; an end has none). Some
    windings with and some without raise: DSS would take its default for those."""
    values = [winding.r_dc for winding in unit_model.model.windings]
    if all(value is None for value in values):
        return None
    if None in values:
        raise ValueError(f"{describe(unit_model.unit)}: rDC on some windings only ({values}); DSS's RdcOhms needs "
                         "every winding's, else the engine's default")
    return values


def winding_buses(unit_model: UnitModel, names: Names) -> list[str]:
    """Each winding's bus reference (E7, T6)."""
    return [_bus(unit_model, winding, names) for winding in unit_model.model.windings]


def winding_kv(unit_model: UnitModel, winding: Winding) -> float:
    """A coil's ``baseU`` (a PowerTransformerEnd's is derived from its ``ratedU``, ``get_transformer_model``), a
    polyphase winding's ``ratedU`` (LL), in kV; an AutoTransformerEnd has only ``baseU`` (the deck's kV, LL on a
    3-phase unit)."""
    by_rating = unit_model.polyphase and unit_model.model.form is not TransformerForm.AUTO
    attribute = "ratedU" if by_rating else "baseU"
    value = winding.rated_u if by_rating else winding.base_u
    if value is None:
        raise ValueError(f"{describe(unit_model.unit)}: winding {winding.number} has no {attribute}")
    return value


def tap_values(unit_model: UnitModel, *, shared: bool) -> dict:
    """``taps``, ``MaxTap``, ``MinTap``, ``NumTaps`` of the unit's RatioTapChanger; none is ``{}``. ``shared``: the
    unit is one of several tanks on the tap's end."""
    found = tap_windings(unit_model)
    if not found:
        return {}
    if shared:
        raise ValueError(f"{describe(unit_model.unit)}: a tap changer on a several-tank transformer is not mapped (T4)")
    if len(found) > 1:
        raise ValueError(f"{describe(unit_model.unit)}: tap changers on windings {[w.number for w, _ in found]}; DSS "
                         f"has one tap range per transformer")
    [(winding, tap)] = found
    steps = get_tap_steps(tap, "kV")
    kv = winding_kv(unit_model, winding)
    if steps.neutral_u is not None and not math.isclose(steps.neutral_u, kv, rel_tol=1e-6):
        raise ValueError(f"{describe(tap)}: neutralU {steps.neutral_u} kV is not its winding's {kv} kV; DSS has no "
                         f"home for it")
    taps = [1.0] * len(unit_model.model.windings)
    taps[winding.number - 1] = get_tap_ratio(tap, which="actual")
    return dict(taps=taps, MaxTap=get_tap_ratio(tap, which="high"), MinTap=get_tap_ratio(tap, which="low"),
                NumTaps=steps.high - steps.low)


def tap_windings(unit_model: UnitModel) -> list[tuple[Winding, cim.RatioTapChanger]]:
    """``(winding, tap)`` for each winding whose end holds a RatioTapChanger; an end with two windings raises."""
    windings = unit_model.model.windings
    found = []
    for winding in windings:
        end = winding.end
        if end.PhaseTapChanger is not None:
            raise ValueError(f"{describe(end)}: a PhaseTapChanger is not mapped")
        if end.RatioTapChanger is None:
            continue
        if sum(other.end is end for other in windings) > 1:
            raise ValueError(f"{describe(end.RatioTapChanger)}: its end holds several windings (a center-tap "
                             f"secondary); DSS taps one winding")
        found.append((winding, end.RatioTapChanger))
    return found


def _conductors(unit, windings: tuple[Winding, ...]) -> tuple[cim.SinglePhaseKind, ...]:
    """A polyphase unit's phase conductors: every winding on A, B and C, or every winding on the same two phases and
    N (a 2-phase wye, GLM's ``WYE_WYE`` on two phases: DSS ``phases=2``, whose per-phase base is the coil's). ()
    when each winding is a coil of two conductors; anything else raises."""
    phase_sets = {tuple(phase for phase in winding.phases if phase is not N) for winding in windings}
    if phase_sets == {THREE_PHASES}:
        return THREE_PHASES
    two_phase_wye = all(len(winding.phases) == 3 and N in winding.phases for winding in windings)
    if len(phase_sets) == 1 and two_phase_wye:
        return phase_sets.pop()
    odd = [winding.number for winding in windings if len(winding.phases) != 2]
    if odd:
        raise ValueError(f"{describe(unit)}: windings {odd} are neither polyphase (ABC, or one pair of phases and N "
                         f"on every winding) nor a coil of two conductors")
    return ()


def _kva(unit, winding: Winding, polyphase: bool) -> float:
    """A coil's ``baseS`` (an AutoTransformerEnd has none: its ``ratedS``), a polyphase winding's ``ratedS``."""
    value = winding.rated_s if polyphase or winding.base_s is None else winding.base_s
    if value is None:
        raise ValueError(f"{describe(unit)}: winding {winding.number} has no ratedS")
    return value


def _connection(unit, winding: Winding, auto: bool) -> str:
    """D -> delta, Y/Yn/I -> wye; an AutoTransformerEnd has no kind: wye with a neutral, else delta."""
    if winding.connection is None:
        if not auto:
            raise ValueError(f"{describe(winding.end)}: connectionKind is unset")
        return "wye" if N in winding.phases else "delta"
    if winding.connection not in CONNECTION:
        raise ValueError(f"{describe(winding.end)}: connectionKind {winding.connection.value} is not mapped")
    return CONNECTION[winding.connection]


def _resistances(unit_model: UnitModel) -> list[float]:
    """%R per winding on its own kVA; an unset r is 0 so the engine's 0.2 % never applies. AUTO: the mesh r halved."""
    unit, model, _, kvas = unit_model
    if model.form is TransformerForm.AUTO:
        if len(model.windings) != 2 or kvas[0] != kvas[1]:
            raise ValueError(f"{describe(unit)}: an AutoTransformer is mapped with two windings of one kVA")
        r = model.mesh[(1, 2)].r if (1, 2) in model.mesh else None
        half = 0.0 if r is None else r / 2
        return [half, half]
    return [(0.0 if winding.r is None else winding.r) * kva / kvas[0] for winding, kva in zip(model.windings, kvas)]


def _reactances(unit_model: UnitModel) -> dict:
    """XHL, XHT, XLT from the mesh, on winding 1's kVA; a missing pair, or a mesh r outside AUTO, raises."""
    unit, model = unit_model.unit, unit_model.model
    pairs = [(1, 2)] if len(model.windings) == 2 else list(MESH_SLOTS)
    missing = [pair for pair in pairs if pair not in model.mesh]
    if missing:
        raise ValueError(f"{describe(unit)}: no mesh impedance between windings {missing}")
    if model.form is not TransformerForm.AUTO:
        with_r = [pair for pair in pairs if model.mesh[pair].r not in (None, 0.0)]
        if with_r:
            raise ValueError(f"{describe(unit)}: a mesh r between windings {with_r}; DSS takes r per winding")
    return {MESH_SLOTS[pair]: model.mesh[pair].x for pair in pairs}


def _neutral_impedance(unit_model: UnitModel) -> dict:
    """``wdg``, ``Rneut``, ``Xneut`` of the one winding grounded through rground/xground (T6)."""
    windings = [winding for winding in unit_model.model.windings if _has_neutral_impedance(winding)]
    if not windings:
        return {}
    if len(windings) > 1 or not unit_model.polyphase:
        raise ValueError(f"{describe(unit_model.unit)}: a neutral impedance on windings "
                         f"{[w.number for w in windings]}; one polyphase winding is mapped (the record has one wdg)")
    [winding] = windings
    return dict(wdg=winding.number, Rneut=winding.rground or 0.0, Xneut=winding.xground or 0.0)


def _has_neutral_impedance(winding: Winding) -> bool:
    return winding.rground is not None or winding.xground is not None


def _bus(unit_model: UnitModel, winding: Winding, names: Names) -> str:
    terminal = winding.end.Terminal
    if terminal is None or terminal.ConnectivityNode is None:
        raise ValueError(f"{describe(winding.end)}: has no Terminal on a ConnectivityNode")
    node = terminal.ConnectivityNode
    if not unit_model.polyphase:
        if N in winding.phases and winding.grounded is None:
            raise ValueError(f"{describe(winding.end)}: a coil neutral with grounded unset")
        neutral = COIL_NEUTRAL_NODE if winding.grounded else NEUTRAL_NODE  # T6: a floating neutral on its own node
        return bus_ref(node, winding.phases, names, neutral=neutral)
    wye = _connection(unit_model.unit, winding, unit_model.model.form is TransformerForm.AUTO) == "wye"
    if not wye:
        if N in winding.phases:
            raise ValueError(f"{describe(winding.end)}: a delta winding with a neutral")
        return bus_ref(node, unit_model.conductors, names)
    if winding.grounded is None:
        raise ValueError(f"{describe(winding.end)}: a wye winding with grounded unset")
    if winding.grounded and not _has_neutral_impedance(winding):
        return bus_ref(node, unit_model.conductors, names)  # the engine's neutral is on node 0
    return bus_ref(node, (*unit_model.conductors, N), names, neutral=NEUTRAL_NODE)

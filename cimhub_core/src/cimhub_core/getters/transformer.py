"""A transformer's windings, mesh impedance and core as one model, whatever CIM form holds them (skill
`export-getters`, semantic rule 5).

The getter reads one transformer unit: a ``TransformerTank``, a ``PowerTransformer`` without tanks, or an
``AutoTransformer`` (``get_transformer_units`` lists a transformer's). It reads five forms (``TransformerForm``):

- BY_ENDS: ``PowerTransformerEnd`` ratings and ``r``, ``TransformerMeshImpedance`` between ends, the core's
  ``g``/``b`` on one end. A PowerTransformerEnd has no ``baseU``, so an end of two conductors (a single-phase coil)
  takes its coil voltage from ``ratedU``, the phase-to-phase nameplate: as is between two phases, over √3 from a
  phase to the neutral.
- AUTO: ``AutoTransformerEnd`` (``baseU``, ``ratedS``) and a mesh between ends; no core.
- BY_PHASE_ENDS: the tank's ``TransformerWinding``s, each a coil between two ``TransformerPhaseEnd``s (matched to
  the ``PowerTransformerEnd`` by ``endNumber``), a mesh between windings, the tank's ``noLoadLoss`` and
  ``percentMagnetizingCurrent``.
- BY_TANK_ENDS: the tank's ``TankConfiguration``, one winding per ``TransformerTankEnd``; template end n is instance
  end n, and connection and grounding set on both must agree. The kinds agree up to the grounding (Y and Yn), which
  is the instance's, so the instance's kind wins. A coil's phases are its instance end's ``TransformerPhaseEnd``s in
  ``sequenceNumber`` order when it has them (a 1-phase coil's direction), else the end's terminal phases.
- BY_LUGS: the configuration's windings run lug to lug, and a lug's ``sequenceNumber`` names the instance
  ``TransformerPhaseEnd`` it lands on (a centre tap). A bank of template tanks is lugged, every can: the lugs say
  which of the bank's phase ends each can serves.
- Either template form may hold its impedance as the configuration's ``percentImpedance`` and ``loadLoss`` instead
  of winding ``r`` and a mesh (GLM's %Z): read as BY_TANK_IMPEDANCE's below, on winding 1's ``ratedS``, when no
  winding has an ``r`` or a mesh (with one, the percentImpedance beside it is the nameplate's figure, not read). Its
  windings are two, or a centre tap's three, the halves x→N and N→y (s1, s2 on a service; a, b on a delta bank's
  lighting can).
- BY_TANK_IMPEDANCE: two ``PowerTransformerEnd``s and one tank with ``percentImpedance`` (and ``loadLoss``), nothing
  else: a GIS's nameplate kVA and %Z. |z| is on end 1's ``ratedS``, r = loadLoss / ratedS (0 unset), x = √(z² − r²).
  An end on s1s2N with connectionKind I is a centre tap: two halves, s1→N and N→s2, each at half the end's ``ratedU``
  and ``ratedS`` on the can's kVA, split by Hopkinson's rule for an interlaced secondary (``CENTER_TAP_SPLIT``, as the
  ``transformer_template_1ph`` shape). Otherwise r is halved over the two windings (DSS's %loadloss). A bank is one
  such tank per can, each on its own ``baseS`` (the can's kVA), placed in tank order (``_bank_windings``).

Every impedance and admittance comes out in percent or pu on one power base: ``base_power`` (in ``power_unit``) when
the caller declares one (RAW's MBASE), else winding 1's ``ratedS`` (DSS and GLM put every percent on it); an ideal
AutoTransformer without one has none. The voltage is always the From winding's own (``ratedU``, or a coil's
``baseU``). An end form with a declared ``base_power`` reads each ohm and siemens on that power directly
(``get_qty(power_base=)``), so its ends need no ``ratedS`` (a RAW 3-winding unit's have none). Otherwise CIM's
value is read as a percent on its From winding's own ``baseU²/baseS`` and moved to the declared base by the power
only: z × S_new/S_old, y × S_old/S_new. A winding's ``baseS`` is per phase, so its whole-unit power is winding 1's
``ratedS`` scaled by the two ``baseS``. A set rating (``ratedU``, ``ratedS``, ``baseU``, ``baseS``) of 0 or less
raises, since every percent is on one.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.terminals import get_terminal_phases

IMPEDANCE_UNITS = {"percent": 1.0, "pu": 0.01}  # the result unit -> its factor on a percent
N = cim.SinglePhaseKind.N


class TransformerForm(Enum):
    BY_ENDS = "by ends"
    AUTO = "by auto-transformer ends"
    BY_PHASE_ENDS = "by phase ends"
    BY_TANK_ENDS = "by template tank ends"
    BY_LUGS = "by template lugs"
    BY_TANK_IMPEDANCE = "by ends with a tank percentImpedance"


END_FORMS = (TransformerForm.BY_ENDS, TransformerForm.AUTO)
TEMPLATE_FORMS = (TransformerForm.BY_TANK_ENDS, TransformerForm.BY_LUGS)
#: BY_TANK_IMPEDANCE: each winding's share of the can's r, and each mesh pair's share of its x. A centre tap is split
#: by Hopkinson's rule for an interlaced secondary (H - X1X2 = H - X2X3 = 1.5R + j1.2X, X1X2 - X2X3 = 2R + j0.8X).
TWO_WINDING_SPLIT = ((0.5, 0.5), {(1, 2): 1.0})
CENTER_TAP_SPLIT = ((0.5, 1.0, 1.0), {(1, 2): 1.2, (1, 3): 1.2, (2, 3): 0.8})
#: a single can's baseS against its end's ratedS, and a bank's cans against the ends' total
RATING_REL_TOL = 1e-6
WYE_KINDS = (cim.WindingConnection.Y, cim.WindingConnection.Yn)
#: the phases of a centre-tap end, and its two halves
CENTER_TAP_PHASES = frozenset({cim.SinglePhaseKind.s1, cim.SinglePhaseKind.s2, N})
CENTER_TAP_HALVES = ((cim.SinglePhaseKind.s1, N), (N, cim.SinglePhaseKind.s2))
#: a grounded kind -> its kind without the grounding, which is the instance's (BY_TANK_ENDS)
_UNGROUNDED = {cim.WindingConnection.Yn: cim.WindingConnection.Y, cim.WindingConnection.Zn: cim.WindingConnection.Z}


class Winding(NamedTuple):
    """One winding, in winding order (by end number; a coil's by its lowest phase end ``sequenceNumber``)."""

    number: int
    end: cim.TransformerEnd  # the instance end it lands on: a PowerTransformerEnd or an AutoTransformerEnd
    phases: tuple[cim.SinglePhaseKind, ...]  # a coil: its two phase ends; else its end's terminal phases
    connection: cim.WindingConnection | None
    grounded: bool | None
    rground: float | None  # ohm
    xground: float | None  # ohm
    rated_u: float | None  # voltage_unit; an AutoTransformerEnd has none
    rated_s: float | None  # power_unit; winding 1's is required
    base_u: float | None  # the coil voltage; a PowerTransformerEnd's is derived for a coil, else None
    base_s: float | None  # per phase; a PowerTransformerEnd has none
    r: float | None  # on the model's base_power
    phase_shift: float | None  # deg: the instance PowerTransformerEnd's fixed phaseShift
    r_dc: float | None = None  # ohm: a TransformerWinding's rDC; an end has none


class MeshImpedance(NamedTuple):
    """Between two windings, on the model's base_power."""

    r: float | None
    x: float


class CoreAdmittance(NamedTuple):
    """The magnetizing branch on the model's base_power: g from the no-load loss, b from the magnetizing current."""

    g: float | None
    b: float | None


class TransformerModel(NamedTuple):
    form: TransformerForm
    windings: tuple[Winding, ...]
    mesh: dict[tuple[int, int], MeshImpedance]  # {(i, j): ...}, i < j winding numbers
    core: CoreAdmittance
    base_power: float | None  # power_unit: what every percent or pu is on; None on an unrated ideal AutoTransformer


class _Coil(NamedTuple):
    """A winding before numbering: what holds its values, and the instance end and phases it lands on."""

    key: tuple[int, ...]
    source: cim.TransformerEnd | cim.TransformerWinding  # holds the ratings, r and the From mesh impedances
    end: cim.TransformerEnd
    phases: tuple[cim.SinglePhaseKind, ...]
    settings: tuple  # the objects holding connectionKind, grounded, rground and xground


def get_transformer_units(transformer: cim.PowerTransformer | cim.AutoTransformer) -> tuple:
    """The units ``get_transformer_model`` reads: a PowerTransformer's tanks, else the transformer itself."""
    if isinstance(transformer, cim.PowerTransformer) and transformer.TransformerTanks:
        return tuple(transformer.TransformerTanks)
    return (transformer,)


def get_transformer_model(unit, impedance_unit: str = "percent", *, base_power: float | None = None,
                          voltage_unit: str = "V", power_unit: str = "VA") -> TransformerModel:
    """The unit's windings, mesh impedance and core. ``impedance_unit`` is ``'percent'`` or ``'pu'``, on
    ``base_power`` (in ``power_unit``, like every power the model returns), else on winding 1's ``ratedS``, which
    only an ideal AutoTransformer (no mesh) may leave unset. Raises when a form is ambiguous, a rating a value needs
    is unset, or two places that hold the same value disagree."""
    if impedance_unit not in IMPEDANCE_UNITS:
        raise ValueError(f"impedance_unit must be one of {sorted(IMPEDANCE_UNITS)}, not {impedance_unit!r}")
    if base_power is not None:
        base_power = cim.ApparentPower(base_power, power_unit)
    form = _form(unit)
    if form is TransformerForm.BY_TANK_IMPEDANCE:
        return _tank_impedance_model(unit, impedance_unit, base_power, voltage_unit, power_unit)
    coils = _coils(unit, form)
    _check_ratings(coil.source for coil in coils)
    first = coils[0].source
    direct = base_power is not None and form in END_FORMS  # ohm and S read on base_power: no ratedS needed
    ideal = form is TransformerForm.AUTO and not any(coil.source.FromMeshImpedance for coil in coils)
    if ideal:
        first_va = get_qty(first, "ratedS", "VA")
    elif direct:
        first_va = None
    else:
        first_va = required_qty(first, "ratedS", "VA")
    result_va = first_va if base_power is None else base_power.to("VA")
    factor = IMPEDANCE_UNITS[impedance_unit]

    def stored_va(source) -> float:
        """The whole-unit power a percent on ``source``'s own base is on."""
        if form in END_FORMS:
            return required_qty(source, "ratedS", "VA")
        return first_va * required_qty(source, "baseS", "VA") / required_qty(first, "baseS", "VA")

    def impedance(holder, attribute: str, source) -> float | None:
        if direct:
            value = get_qty(holder, attribute, "percent", power_base=base_power)
            return None if value is None else value * factor
        value = get_qty(holder, attribute, "percent")
        return None if value is None else value * result_va / stored_va(source) * factor

    def admittance(holder, attribute: str) -> float | None:
        if direct:
            value = get_qty(holder, attribute, "percent", power_base=base_power)
            return None if value is None else value * factor
        value = get_qty(holder, attribute, "percent")
        return None if value is None else value * stored_va(holder) / result_va * factor

    if form in TEMPLATE_FORMS and _by_nameplate(unit.TankConfiguration, coils):
        resistances, mesh = _template_nameplate(unit.TankConfiguration, coils, first_va, result_va / first_va * factor)
    else:
        # an AutoTransformerEnd has no r
        resistances = [impedance(coil.source, "r", coil.source) if _has(coil.source, "r") else None for coil in coils]
        mesh = _mesh(unit, coils, impedance)
    windings = [_winding(number, coil, r, voltage_unit, power_unit)
                for number, (coil, r) in enumerate(zip(coils, resistances, strict=True), start=1)]
    if form is TransformerForm.BY_ENDS:
        core = _end_core(unit, coils, admittance)
    elif form is TransformerForm.AUTO:
        core = CoreAdmittance(None, None)
    else:
        core = _tank_core(unit, first_va, result_va, factor)
    base = get_qty(first, "ratedS", power_unit) if base_power is None else base_power.to(power_unit)
    return TransformerModel(form, tuple(windings), mesh, core, base)


def _form(unit) -> TransformerForm:
    if isinstance(unit, cim.AutoTransformer):
        return TransformerForm.AUTO
    if isinstance(unit, cim.PowerTransformer):
        if unit.TransformerTanks:
            raise ValueError(f"{describe(unit)}: has tanks; read each unit get_transformer_units gives")
        return TransformerForm.BY_ENDS
    if not isinstance(unit, cim.TransformerTank):
        raise ValueError(f"{describe(unit)}: is not a TransformerTank, PowerTransformer or AutoTransformer")
    if unit.PowerTransformer is None:
        raise ValueError(f"{describe(unit)}: has no PowerTransformer")
    config = unit.TankConfiguration
    if config is None:
        if unit.TransformerWindings:
            return TransformerForm.BY_PHASE_ENDS
        if unit.percentImpedance is None:
            raise ValueError(f"{describe(unit)}: has no TransformerWindings, no TankConfiguration and no "
                             f"percentImpedance")
        others = [tank for tank in unit.PowerTransformer.TransformerTanks if tank.TankConfiguration is not None
                  or tank.TransformerWindings or tank.percentImpedance is None]
        if others:
            raise ValueError(f"{describe(unit.PowerTransformer)}: a bank mixes tanks by percentImpedance with "
                             f"{describe(others[0])}")
        return TransformerForm.BY_TANK_IMPEDANCE
    if unit.TransformerWindings:
        raise ValueError(f"{describe(unit)}: has its own TransformerWindings and a TankConfiguration")
    if not config.TransformerWinding:
        raise ValueError(f"{describe(config)}: has no TransformerWinding")
    lugged = {winding.FromTransformerLug is not None for winding in config.TransformerWinding}
    if lugged == {True, False}:
        raise ValueError(f"{describe(config)}: some windings run between lugs and some from a TransformerTankEnd")
    tanks = unit.PowerTransformer.TransformerTanks
    if len(tanks) > 1 and not all(_lugged_template(tank) for tank in tanks):
        raise ValueError(f"{describe(unit.PowerTransformer)}: a bank of template tanks says which phases each tank "
                         f"serves only by lugs; {describe(next(t for t in tanks if not _lugged_template(t)))} has none")
    return TransformerForm.BY_LUGS if lugged == {True} else TransformerForm.BY_TANK_ENDS


def _lugged_template(tank: cim.TransformerTank) -> bool:
    """A tank by template whose every winding runs between lugs, which name the instance phase ends it lands on."""
    config = tank.TankConfiguration
    return (config is not None and bool(config.TransformerWinding)
            and all(winding.FromTransformerLug is not None for winding in config.TransformerWinding))


def _tank_impedance_model(tank: cim.TransformerTank, impedance_unit: str, base_power, voltage_unit: str,
                          power_unit: str) -> TransformerModel:
    """BY_TANK_IMPEDANCE: the windings from the two ends, r and x from the tank's percentImpedance and loadLoss on the
    can's kVA."""
    tanks = list(tank.PowerTransformer.TransformerTanks)
    ends = [end for _, end in sorted(_instance_ends(tank.PowerTransformer).items())]
    if len(ends) != 2:
        raise ValueError(f"{describe(tank.PowerTransformer)}: {len(ends)} ends; a tank percentImpedance is between two")
    for end in ends:
        held = [name for name in ("r", "x", "g", "b") if getattr(end, name) is not None]
        if held or end.FromMeshImpedance or end.ToMeshImpedance:
            raise ValueError(f"{describe(end)}: {held or 'a TransformerMeshImpedance'} beside {describe(tank)}'s "
                             f"percentImpedance; one value would have two homes")
    _check_ratings([*ends, tank])
    first_va = _can_va(tank, tanks, ends[0])
    result_va = first_va if base_power is None else base_power.to("VA")
    factor = IMPEDANCE_UNITS[impedance_unit]
    if len(tanks) == 1:
        windings = [winding for end in ends for winding in _end_windings(end, voltage_unit, power_unit)]
    else:
        position = next(index for index, other in enumerate(tanks) if other is tank)
        windings = _bank_windings(position, len(tanks), ends, get_qty(tank, "baseS", power_unit), voltage_unit,
                                  power_unit)
    resistances, mesh = _nameplate_split(tank, first_va, len(windings) == 3, result_va / first_va * factor)
    windings = tuple(winding._replace(number=number, r=r)
                     for number, (winding, r) in enumerate(zip(windings, resistances, strict=True), start=1))
    base = windings[0].rated_s if base_power is None else base_power.to(power_unit)
    return TransformerModel(TransformerForm.BY_TANK_IMPEDANCE, windings, mesh,
                            _tank_core(tank, first_va, result_va, factor), base)


def _nameplate_split(holder, first_va: float, center_tap: bool,
                     scale: float) -> tuple[list[float], dict[tuple[int, int], MeshImpedance]]:
    """Each winding's r and the mesh x from ``holder``'s nameplate (a tank or its TankConfiguration): |z| is
    ``percentImpedance`` on ``first_va``, r = loadLoss / first_va (0 unset), x = √(z² − r²), split over two windings
    or a centre tap's three (``TWO_WINDING_SPLIT``, ``CENTER_TAP_SPLIT``), then times ``scale``."""
    z = get_qty(holder, "percentImpedance", "percent")
    loss = get_qty(holder, "loadLoss", "W")
    r = 0.0 if loss is None else loss / first_va * 100
    if r > z:
        raise ValueError(f"{describe(holder)}: loadLoss {loss:g} W is {r:.4g} % of {first_va / 1000:g} kVA, above "
                         f"its percentImpedance {z:g} %")
    x = math.sqrt(z ** 2 - r ** 2)
    r_shares, x_shares = CENTER_TAP_SPLIT if center_tap else TWO_WINDING_SPLIT
    return ([share * r * scale for share in r_shares],
            {pair: MeshImpedance(None, share * x * scale) for pair, share in x_shares.items()})


def _by_nameplate(config: cim.TransformerTankConfiguration, coils: list[_Coil]) -> bool:
    """The template's impedance is its ``percentImpedance`` (GLM's %Z, S3b-5) when no winding holds an r or a
    TransformerMeshImpedance. Where one does, that is the impedance, and a percentImpedance beside it is the
    nameplate's figure, not read (the CIMTBL-Models templates carry both)."""
    series = any(coil.source.r is not None or coil.source.FromMeshImpedance for coil in coils)
    return config.percentImpedance is not None and not series


def _template_nameplate(config, coils: list[_Coil], first_va: float,
                        scale: float) -> tuple[list[float], dict[tuple[int, int], MeshImpedance]]:
    """A TankConfiguration's percentImpedance and loadLoss as each winding's r and the mesh, by ``_nameplate_split``:
    two windings, or a centre tap's three (``_is_center_tap``)."""
    center_tap = _is_center_tap(coils)
    if len(coils) != 2 and not center_tap:
        raise ValueError(f"{describe(config)}: percentImpedance on {len(coils)} windings; it is between two, or over "
                         f"a centre tap's three")
    return _nameplate_split(config, first_va, center_tap, scale)


def _is_center_tap(coils: list[_Coil]) -> bool:
    """Three windings whose 2 and 3 are the halves of one secondary joined at its neutral tap, x→N and N→y: s1→N and
    N→s2 on a split-phase service, a→N and N→b on the lighting can of a four-wire or open delta bank."""
    if len(coils) != 3 or any(len(coil.phases) != 2 for coil in coils[1:]):
        return False
    (outer, tap), (tap_again, other) = coils[1].phases, coils[2].phases
    return tap is N and tap_again is N and N not in (outer, other) and outer is not other


def _can_va(tank: cim.TransformerTank, tanks: list, first: cim.PowerTransformerEnd) -> float:
    """The can's kVA in VA: a single can's end 1 ``ratedS`` (its ``baseS``, when set, must agree), a bank's can its
    own ``baseS``. A bank's cans must add up to end 1's ``ratedS``, the bank's total."""
    end_va = required_qty(first, "ratedS", "VA")
    own = get_qty(tank, "baseS", "VA")
    if len(tanks) == 1:
        if own is not None and not math.isclose(own, end_va, rel_tol=RATING_REL_TOL):
            raise ValueError(f"{describe(tank)}: baseS {own / 1000:g} kVA is not {describe(first)}'s ratedS "
                             f"{end_va / 1000:g} kVA")
        return end_va
    cans = [get_qty(other, "baseS", "VA") for other in tanks]
    if None in cans:
        raise ValueError(f"{describe(tanks[cans.index(None)])}: a tank in a bank needs its baseS (the can's kVA)")
    if not math.isclose(sum(cans), end_va, rel_tol=RATING_REL_TOL):
        raise ValueError(f"{describe(tank.PowerTransformer)}: its tanks' baseS add up to {sum(cans) / 1000:g} kVA, not "
                         f"{describe(first)}'s ratedS {end_va / 1000:g} kVA")
    return own


def _bank_windings(position: int, count: int, ends: list, can_s: float, voltage_unit: str,
                   power_unit: str) -> list[Winding]:
    """Can ``position`` (tank order) of a bank of ``count``: its primary from end 1's phase ``position`` to N; its
    secondary to N on a wye end, across phases (position, position + 1) on a delta end (ANSI YNd1; an open delta's
    cans are L a-b and T b-c), the a-b can centre-tapped to N on a 4-wire delta (the CIMTBL-Models bank templates)."""
    primary, secondary = ends
    high, low = _phase_conductors(primary), _phase_conductors(secondary)
    if primary.connectionKind not in WYE_KINDS or N not in _terminal_phases(primary) or len(high) != count:
        raise ValueError(f"{describe(primary)}: a bank of {count} cans is read from a wye end with a neutral and one "
                         f"phase per can")
    coils = [(primary, (high[position], N), False)]
    if secondary.connectionKind in WYE_KINDS and N in _terminal_phases(secondary) and len(low) == count:
        coils.append((secondary, (low[position], N), False))
    elif secondary.connectionKind is cim.WindingConnection.D and len(low) == 3 and count in (2, 3):
        leg = (low[position], low[(position + 1) % 3])
        if position == 0 and N in _terminal_phases(secondary):
            coils += [(secondary, (leg[0], N), True), (secondary, (N, leg[1]), True)]  # the lighting leg
        else:
            coils.append((secondary, leg, False))
    else:
        raise ValueError(f"{describe(secondary)}: a bank of {count} cans is read onto a wye end with a neutral and "
                         f"one phase per can, or a 3-phase delta end (open with 2 cans)")
    return [_can_winding(end, phases, half, can_s, voltage_unit, power_unit) for end, phases, half in coils]


def _can_winding(end: cim.PowerTransformerEnd, phases: tuple, half: bool, can_s: float, voltage_unit: str,
                 power_unit: str) -> Winding:
    """A bank can's coil on ``end``: its nameplate ``ratedU`` (phase to phase) and the can's kVA; the coil voltage is
    half of it on a centre-tap half, over √3 from a phase to N, else all of it."""
    winding = _winding(0, _Coil((_end_number(end),), end, end, _terminal_phases(end), (end,)), None, voltage_unit,
                       power_unit)
    rated_u = winding.rated_u
    if rated_u is None:
        base_u = None
    elif half:
        base_u = rated_u / 2
    else:
        base_u = rated_u / math.sqrt(3) if N in phases else rated_u
    return winding._replace(phases=phases, rated_s=can_s / 2 if half else can_s, base_u=base_u, base_s=can_s)


def _phase_conductors(end: cim.PowerTransformerEnd) -> tuple[cim.SinglePhaseKind, ...]:
    return tuple(phase for phase in _terminal_phases(end) if phase is not N)


def _end_windings(end: cim.PowerTransformerEnd, voltage_unit: str, power_unit: str) -> list[Winding]:
    """The end's winding; a centre-tap end (s1s2N, connectionKind I) is two halves, each at half its ratedU and
    ratedS, on the can's kVA (``base_s``) as a centre-tap template's."""
    coil = _Coil((_end_number(end),), end, end, _terminal_phases(end), (end,))
    winding = _winding(0, coil, None, voltage_unit, power_unit)
    if end.connectionKind is not cim.WindingConnection.I or set(coil.phases) != CENTER_TAP_PHASES:
        return [winding]
    half_u = None if winding.rated_u is None else winding.rated_u / 2
    half_s = None if winding.rated_s is None else winding.rated_s / 2
    return [winding._replace(phases=half, rated_s=half_s, base_u=half_u, base_s=winding.rated_s)
            for half in CENTER_TAP_HALVES]


def _coils(unit, form: TransformerForm) -> list[_Coil]:
    """The unit's windings in winding order; two with the same place raise."""
    if form in END_FORMS:
        ends = unit.AutoTransformerEnd if form is TransformerForm.AUTO else unit.PowerTransformerEnd
        coils = [_Coil((_end_number(end),), end, end, _terminal_phases(end), (end,)) for end in ends]
    else:
        ends = _instance_ends(unit.PowerTransformer)
        if form is TransformerForm.BY_PHASE_ENDS:
            coils = [_coil(winding, (winding.FromTransformerEnd, winding.ToTransformerEnd), ends)
                     for winding in unit.TransformerWindings]
        elif form is TransformerForm.BY_LUGS:
            phase_ends = _instance_phase_ends(ends.values())
            coils = [_coil(winding, (_lug_phase_end(winding, "FromTransformerLug", phase_ends),
                                     _lug_phase_end(winding, "ToTransformerLug", phase_ends)), ends)
                     for winding in unit.TankConfiguration.TransformerWinding]
        else:
            coils = [_tank_end_coil(winding, ends) for winding in unit.TankConfiguration.TransformerWinding]
    if not coils:
        raise ValueError(f"{describe(unit)}: has no windings")
    coils.sort(key=lambda coil: coil.key)
    keys = [coil.key for coil in coils]
    if len(set(keys)) != len(keys):
        raise ValueError(f"{describe(unit)}: two windings have the same place {keys}")
    return coils


def _coil(winding: cim.TransformerWinding, pair: tuple, ends: dict[int, cim.PowerTransformerEnd]) -> _Coil:
    """A winding between two instance TransformerPhaseEnds of one end."""
    if not all(isinstance(phase_end, cim.TransformerPhaseEnd) for phase_end in pair):
        raise ValueError(f"{describe(winding)}: must run between two TransformerPhaseEnds")
    numbers = {_end_number(phase_end) for phase_end in pair}
    if len(numbers) != 1:
        raise ValueError(f"{describe(winding)}: its phase ends are on different ends {sorted(numbers)}")
    end = _end(ends, numbers.pop(), winding)
    sequence = min(_sequence_number(phase_end) for phase_end in pair)
    return _Coil((end.endNumber, sequence), winding, end, tuple(phase_end.phase for phase_end in pair), (end,))


def _tank_end_coil(winding: cim.TransformerWinding, ends: dict[int, cim.PowerTransformerEnd]) -> _Coil:
    """A template winding on a TransformerTankEnd: template end n is instance end n."""
    tank_end = winding.FromTransformerEnd
    if not isinstance(tank_end, cim.TransformerTankEnd):
        raise ValueError(f"{describe(winding)}: has no TransformerTankEnd (FromTransformerEnd)")
    end = _end(ends, _end_number(tank_end), winding)
    return _Coil((end.endNumber,), winding, end, _ordered_phases(end), (end, tank_end))


def _ordered_phases(end: cim.PowerTransformerEnd) -> tuple[cim.SinglePhaseKind, ...]:
    """The end's TransformerPhaseEnds in sequenceNumber order (a coil's From -> To), else its terminal phases."""
    phase_ends = _instance_phase_ends([end])
    phases = _terminal_phases(end)
    if not phase_ends:
        return phases
    ordered = tuple(phase_ends[number].phase for number in sorted(phase_ends))
    if sorted(phase.value for phase in ordered) != sorted(phase.value for phase in phases):
        raise ValueError(f"{describe(end)}: its TransformerPhaseEnds {[phase.value for phase in ordered]} are not "
                         f"its terminal's phases {[phase.value for phase in phases]}")
    return ordered


def _lug_phase_end(winding: cim.TransformerWinding, attribute: str,
                   phase_ends: dict[int, cim.TransformerPhaseEnd]) -> cim.TransformerPhaseEnd:
    lug = getattr(winding, attribute)
    if lug is None or lug.sequenceNumber not in phase_ends:
        raise ValueError(f"{describe(winding)}: its {attribute} names no instance TransformerPhaseEnd "
                         f"(sequenceNumber {lug and lug.sequenceNumber}; the instance has {sorted(phase_ends)})")
    return phase_ends[lug.sequenceNumber]


def _instance_ends(transformer: cim.PowerTransformer) -> dict[int, cim.PowerTransformerEnd]:
    ends = {}
    for end in transformer.PowerTransformerEnd:
        number = _end_number(end)
        if number in ends:
            raise ValueError(f"{describe(transformer)}: two ends have endNumber {number}")
        ends[number] = end
    return ends


def _instance_phase_ends(ends) -> dict[int, cim.TransformerPhaseEnd]:
    """The instance TransformerPhaseEnds on the ends' terminals, by sequenceNumber."""
    phase_ends = {}
    for end in ends:
        for phase_end in _terminal(end).TransformerEnd:
            if isinstance(phase_end, cim.TransformerPhaseEnd):
                number = _sequence_number(phase_end)
                if number in phase_ends:
                    raise ValueError(f"{describe(phase_end)}: a second TransformerPhaseEnd with sequenceNumber "
                                     f"{number}")
                phase_ends[number] = phase_end
    return phase_ends


def _winding(number: int, coil: _Coil, r: float | None, voltage_unit: str, power_unit: str) -> Winding:
    source = coil.source
    return Winding(
        number=number,
        end=coil.end,
        phases=coil.phases,
        connection=_connection(coil.settings),
        grounded=_agreed(coil.settings, "grounded", lambda obj: obj.grounded),
        rground=_agreed(coil.settings, "rground", lambda obj: get_qty(obj, "rground", "ohm")),
        xground=_agreed(coil.settings, "xground", lambda obj: get_qty(obj, "xground", "ohm")),
        rated_u=get_qty(source, "ratedU", voltage_unit) if _has(source, "ratedU") else None,
        rated_s=get_qty(source, "ratedS", power_unit),
        base_u=_coil_voltage(coil, voltage_unit),
        base_s=get_qty(source, "baseS", power_unit) if _has(source, "baseS") else None,
        r=r,
        phase_shift=get_qty(coil.end, "phaseShift", "deg") if isinstance(coil.end, cim.PowerTransformerEnd) else None,
        r_dc=get_qty(source, "rDC", "ohm") if isinstance(source, cim.TransformerWinding) else None,
    )


def _coil_voltage(coil: _Coil, voltage_unit: str) -> float | None:
    """``baseU``; a PowerTransformerEnd has none, so an end of two conductors (a coil) derives it from ``ratedU``,
    the phase-to-phase nameplate: as is between two phases, over √3 from a phase to the neutral. A PowerTransformerEnd
    of more conductors has none."""
    source = coil.source
    if _has(source, "baseU"):
        return get_qty(source, "baseU", voltage_unit)
    rated = get_qty(source, "ratedU", voltage_unit)
    if rated is None or len(coil.phases) != 2:
        return None
    return rated / math.sqrt(3) if N in coil.phases else rated


def _mesh(unit, coils: list[_Coil], impedance) -> dict[tuple[int, int], MeshImpedance]:
    """Every TransformerMeshImpedance from one of the unit's windings to another, else the ends' star x summed by
    pair (``_star_mesh``), on the model's base."""
    numbers = {id(coil.source): number for number, coil in enumerate(coils, start=1)}
    star = {number: impedance(coil.source, "x", coil.source) for number, coil in enumerate(coils, start=1)
            if isinstance(coil.source, cim.PowerTransformerEnd) and coil.source.x is not None}
    mesh = {}
    for coil in coils:
        for impedance_object in coil.source.FromMeshImpedance:
            to = impedance_object.ToWinding or impedance_object.ToTransformerEnd
            if id(to) not in numbers:
                raise ValueError(f"{describe(impedance_object)}: its To winding or end is not in {describe(unit)}")
            pair = tuple(sorted((numbers[id(coil.source)], numbers[id(to)])))
            if pair in mesh:
                raise ValueError(f"{describe(unit)}: two mesh impedances between windings {pair}")
            x = impedance(impedance_object, "x", coil.source)
            if x is None:
                raise ValueError(f"{describe(impedance_object)}: x is unset")
            mesh[pair] = MeshImpedance(impedance(impedance_object, "r", coil.source), x)
    if star and mesh:
        raise ValueError(f"{describe(unit)}: both a star impedance (PowerTransformerEnd.x) and a mesh impedance")
    if star:
        return _star_mesh(unit, star, len(coils))
    return dict(sorted(mesh.items()))


def _star_mesh(unit, star: dict[int, float], windings: int) -> dict[tuple[int, int], MeshImpedance]:
    """(i, j) x = xᵢ + xⱼ for every pair of windings; r is per winding, so the mesh has none. Two windings may hold
    the whole x on one end (CIM's two-winding rule: the other end is zero); with more, every end needs its own x."""
    if windings > 2 and len(star) < windings:
        unset = sorted(set(range(1, windings + 1)) - set(star))
        raise ValueError(f"{describe(unit)}: the star x of winding(s) {unset} is unset; with {windings} windings "
                         f"every end needs its own")
    return {(i, j): MeshImpedance(None, star.get(i, 0.0) + star.get(j, 0.0))
            for i in range(1, windings + 1) for j in range(i + 1, windings + 1)}


def _end_core(unit, coils: list[_Coil], admittance) -> CoreAdmittance:
    """g and b of the one PowerTransformerEnd that holds them, on the model's base. An end whose g and b are zero
    holds none (CIM: the secondary end is zero), so zeros on several ends are one zero core."""
    set_ends = [coil.source for coil in coils if coil.source.g is not None or coil.source.b is not None]
    holders = [end for end in set_ends if get_qty(end, "g", "S") or get_qty(end, "b", "S")] or set_ends[:1]
    if not holders:
        return CoreAdmittance(None, None)
    if len(holders) > 1:
        raise ValueError(f"{describe(unit)}: more than one end holds the core admittance "
                         f"{[holder.mRID for holder in holders]}")
    [end] = holders
    return CoreAdmittance(admittance(end, "g"), admittance(end, "b"))


def _tank_core(tank: cim.TransformerTank, first_va: float, result_va: float, factor: float) -> CoreAdmittance:
    """g from ``noLoadLoss``, b from ``percentMagnetizingCurrent`` (on winding 1's rating), on the tank or its
    configuration; both setting one raises."""
    holders = [tank] if tank.TankConfiguration is None else [tank, tank.TankConfiguration]
    for holder in holders:
        core = holder.TransformerCore
        if core is not None and any(getattr(core, name) is not None for name in ("g", "b", "g0", "b0")):
            raise ValueError(f"{describe(core)}: its g/b are not read; use noLoadLoss and percentMagnetizingCurrent "
                             f"on {describe(holder)}")
    loss = _one_holder(holders, "noLoadLoss", "W")
    magnetizing = _one_holder(holders, "percentMagnetizingCurrent", "percent")
    return CoreAdmittance(
        g=None if loss is None else loss / result_va * 100 * factor,
        b=None if magnetizing is None else magnetizing * first_va / result_va * factor,
    )


def _one_holder(holders: list, attribute: str, unit: str) -> float | None:
    values = [(holder, value) for holder in holders if (value := get_qty(holder, attribute, unit)) is not None]
    if len(values) > 1:
        raise ValueError(f"{describe(holders[0])}: both it and {describe(holders[1])} set {attribute}")
    return values[0][1] if values else None


def _agreed(objects: tuple, what: str, read):
    """The value the objects that set it give; two that differ raise."""
    found = [(obj, value) for obj in objects if (value := read(obj)) is not None]
    for obj, value in found[1:]:
        first_obj, first = found[0]
        same = math.isclose(value, first) if isinstance(value, float) else value == first
        if not same:
            raise ValueError(f"{describe(first_obj)} and {describe(obj)}: {what} {first} and {value} differ")
    return found[0][1] if found else None



def _connection(objects: tuple) -> cim.WindingConnection | None:
    """The first setter's connectionKind (the instance end); the others must agree up to the grounding."""
    found = [(obj, kind) for obj in objects if (kind := getattr(obj, "connectionKind", None)) is not None]
    for obj, kind in found[1:]:
        first_obj, first = found[0]
        if _UNGROUNDED.get(kind, kind) is not _UNGROUNDED.get(first, first):
            raise ValueError(f"{describe(first_obj)} and {describe(obj)}: connectionKind {first.value} and "
                             f"{kind.value} differ")
    return found[0][1] if found else None


#: a winding's ratings, which every percent on it is read on (cimtables' z_base)
RATINGS = (("ratedU", "V"), ("ratedS", "VA"), ("baseU", "V"), ("baseS", "VA"))


def _check_ratings(sources) -> None:
    """Each set rating of each source is positive: a 0 divides by zero, a negative one flips an impedance's sign."""
    for source in sources:
        for attribute, unit in RATINGS:
            value = get_qty(source, attribute, unit) if _has(source, attribute) else None
            if value is not None and value <= 0:
                raise ValueError(f"{describe(source)}: {attribute} {value:g} {unit}; a winding's rating is positive")


def _has(obj, attribute: str) -> bool:
    return attribute in getattr(obj, "__dataclass_fields__", {})


def _end(ends: dict[int, cim.PowerTransformerEnd], number: int, winding: cim.TransformerWinding):
    if number not in ends:
        raise ValueError(f"{describe(winding)}: its transformer has no end {number} (it has {sorted(ends)})")
    return ends[number]


def _end_number(end: cim.TransformerEnd) -> int:
    if end.endNumber is None:
        raise ValueError(f"{describe(end)}: endNumber is unset")
    return end.endNumber


def _sequence_number(phase_end: cim.TransformerPhaseEnd) -> int:
    if phase_end.sequenceNumber is None:
        raise ValueError(f"{describe(phase_end)}: sequenceNumber is unset")
    return phase_end.sequenceNumber


def _terminal(end: cim.TransformerEnd) -> cim.Terminal:
    if end.Terminal is None:
        raise ValueError(f"{describe(end)}: has no Terminal")
    return end.Terminal


def _terminal_phases(end: cim.TransformerEnd) -> tuple[cim.SinglePhaseKind, ...]:
    return get_terminal_phases(_terminal(end))

"""A transformer's windings, mesh impedance and core as one model, whatever CIM form holds them (skill
`export-getters`, semantic rule 5).

The getter reads one transformer unit: a ``TransformerTank``, a ``PowerTransformer`` without tanks, or an
``AutoTransformer`` (``get_transformer_units`` lists a transformer's). It reads five forms (``TransformerForm``):

- BY_ENDS: ``PowerTransformerEnd`` ratings and ``r``, ``TransformerMeshImpedance`` between ends, the core's
  ``g``/``b`` on one end. Without a mesh impedance, the ends' star ``x`` (CGMES's form, cim18v17's 2-winding form:
  all on end 1) gives the mesh: (i, j) x = xᵢ + xⱼ, an unset end x 0, each on its own end's base; the mesh r is
  None, since r is per winding either way. A unit with both an end x and a mesh impedance raises.
- AUTO: ``AutoTransformerEnd`` (``baseU``, ``ratedS``) and a mesh between ends; no core.
- BY_PHASE_ENDS: the tank's ``TransformerWinding``s, each a coil between two ``TransformerPhaseEnd``s (matched to
  the ``PowerTransformerEnd`` by ``endNumber``), a mesh between windings, the tank's ``noLoadLoss`` and
  ``percentMagnetizingCurrent``.
- BY_TANK_ENDS: the tank's ``TankConfiguration``, one winding per ``TransformerTankEnd``; template end n is instance
  end n, and connection and grounding set on both must agree. The kinds agree up to the grounding (Y and Yn), which
  is the instance's, so the instance's kind wins. A coil's phases are its instance end's ``TransformerPhaseEnd``s in
  ``sequenceNumber`` order when it has them (a 1-phase coil's direction), else the end's terminal phases.
- BY_LUGS: the configuration's windings run lug to lug, and a lug's ``sequenceNumber`` names the instance
  ``TransformerPhaseEnd`` it lands on (a centre tap).

Every impedance and admittance comes out in percent or pu on one power base: ``base_power`` when the caller declares
one (``network.base_power`` for RAW), else winding 1's ``ratedS`` (DSS and GLM put every percent on it). CIM stores
a percent on its From winding's own ``baseU²/baseS``, read with ``get_qty``. Moving it to the declared base changes
only the power, because the voltage stays the From winding's: z × S_new/S_old, y × S_old/S_new. A winding's
``baseS`` is per phase, so its whole-unit power is winding 1's ``ratedS`` scaled by the two ``baseS``.
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


class TransformerForm(Enum):
    BY_ENDS = "by ends"
    AUTO = "by auto-transformer ends"
    BY_PHASE_ENDS = "by phase ends"
    BY_TANK_ENDS = "by template tank ends"
    BY_LUGS = "by template lugs"


END_FORMS = (TransformerForm.BY_ENDS, TransformerForm.AUTO)
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
    base_u: float | None  # the coil voltage; a PowerTransformerEnd has none
    base_s: float | None  # per phase; a PowerTransformerEnd has none
    r: float | None  # on the model's base_power


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
    base_power: float  # power_unit: what every percent or pu is on


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


def get_transformer_model(unit, impedance_unit: str = "percent", *, base_power=None, voltage_unit: str = "V",
                          power_unit: str = "VA") -> TransformerModel:
    """The unit's windings, mesh impedance and core. ``impedance_unit`` is ``'percent'`` or ``'pu'``, on
    ``base_power`` (an ApparentPower such as ``network.base_power``), else on winding 1's ``ratedS``. Raises when
    a form is ambiguous, a rating a value needs is unset, or two places that hold the same value disagree."""
    if impedance_unit not in IMPEDANCE_UNITS:
        raise ValueError(f"impedance_unit must be one of {sorted(IMPEDANCE_UNITS)}, not {impedance_unit!r}")
    form = _form(unit)
    coils = _coils(unit, form)
    first = coils[0].source
    first_va = required_qty(first, "ratedS", "VA")
    result_va = first_va if base_power is None else base_power.to("VA")
    factor = IMPEDANCE_UNITS[impedance_unit]

    def stored_va(source) -> float:
        """The whole-unit power a percent on ``source``'s own base is on."""
        if form in END_FORMS:
            return required_qty(source, "ratedS", "VA")
        return first_va * required_qty(source, "baseS", "VA") / required_qty(first, "baseS", "VA")

    def impedance(holder, attribute: str, source) -> float | None:
        value = get_qty(holder, attribute, "percent")
        return None if value is None else value * result_va / stored_va(source) * factor

    windings = []
    for number, coil in enumerate(coils, start=1):
        r = impedance(coil.source, "r", coil.source) if _has(coil.source, "r") else None  # an AutoTransformerEnd has none
        windings.append(_winding(number, coil, r, voltage_unit, power_unit))
    mesh = _mesh(unit, coils, impedance)
    if form is TransformerForm.BY_ENDS:
        core = _end_core(unit, coils, stored_va, result_va, factor)
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
        if not unit.TransformerWindings:
            raise ValueError(f"{describe(unit)}: has no TransformerWindings and no TankConfiguration")
        return TransformerForm.BY_PHASE_ENDS
    if unit.TransformerWindings:
        raise ValueError(f"{describe(unit)}: has its own TransformerWindings and a TankConfiguration")
    if len(unit.PowerTransformer.TransformerTanks) > 1:
        raise ValueError(f"{describe(unit.PowerTransformer)}: a bank of template tanks does not say which phases "
                         f"each tank serves (open until a multi-can form is settled)")
    if not config.TransformerWinding:
        raise ValueError(f"{describe(config)}: has no TransformerWinding")
    lugged = {winding.FromTransformerLug is not None for winding in config.TransformerWinding}
    if lugged == {True, False}:
        raise ValueError(f"{describe(config)}: some windings run between lugs and some from a TransformerTankEnd")
    return TransformerForm.BY_LUGS if lugged == {True} else TransformerForm.BY_TANK_ENDS


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
        base_u=get_qty(source, "baseU", voltage_unit) if _has(source, "baseU") else None,
        base_s=get_qty(source, "baseS", power_unit) if _has(source, "baseS") else None,
        r=r,
    )


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
        return _star_mesh(star, len(coils))
    return dict(sorted(mesh.items()))


def _star_mesh(star: dict[int, float], windings: int) -> dict[tuple[int, int], MeshImpedance]:
    """(i, j) x = xᵢ + xⱼ for every pair of windings, an unset end x 0; r is per winding, so the mesh has none."""
    return {(i, j): MeshImpedance(None, star.get(i, 0.0) + star.get(j, 0.0))
            for i in range(1, windings + 1) for j in range(i + 1, windings + 1)}


def _end_core(unit, coils: list[_Coil], stored_va, result_va: float, factor: float) -> CoreAdmittance:
    """g and b of the one PowerTransformerEnd that holds them, moved from its own base."""
    holders = [coil.source for coil in coils if coil.source.g is not None or coil.source.b is not None]
    if not holders:
        return CoreAdmittance(None, None)
    if len(holders) > 1:
        raise ValueError(f"{describe(unit)}: more than one end holds the core admittance "
                         f"{[holder.mRID for holder in holders]}")
    [end] = holders

    def admittance(attribute: str) -> float | None:
        value = get_qty(end, attribute, "percent")
        return None if value is None else value * stored_va(end) / result_va * factor

    return CoreAdmittance(admittance("g"), admittance("b"))


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

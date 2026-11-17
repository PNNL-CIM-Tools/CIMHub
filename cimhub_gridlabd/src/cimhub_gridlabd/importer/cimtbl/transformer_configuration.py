"""GLM ``transformer_configuration`` -> ``transformer_configuration.cimtbl``: one template each (S3b).

GLM stores a transformer's impedance as %Z: one series R + jX in per unit and a parallel shunt, on GridLAB-D's own
base, ``secondary_voltage``² / ``power_rating`` as written (line to line, the whole unit; ``transformer.cpp:266``).
So it goes on the ``TransformerTankConfiguration``'s nameplate fields, ``percentImpedance``, ``loadLoss``,
``noLoadLoss`` and ``percentMagnetizingCurrent``, moved to the tank's own nameplate by ``k = 3 S_coil / S_total``
so GridLAB-D's ohms are kept (S3b-4, S3b-5). No winding ``r``, no mesh.

Three forms (S3b-2): one tank by ``TransformerTankEnd``; a bank of lugged cans under a
``TransformerBankConfiguration`` (a ``WYE_WYE`` whose wired phases are rated unequally, S3b-9); a center tap by
lugs H1 H2 X1 X3 X2, whose %Z is the full winding's that GridLAB-D splits into its star (``transformer.cpp:788``).
``SINGLE_PHASE`` is a ``WYE_WYE`` (one case in ``transformer.cpp:282``). A wye's voltages rate the line (the Java
CIMHub exports, S3b-3) or the coil, phase to neutral (the Milsoft WindMil exports), as the deck says
(``topology.coil_rated``, S6).
A template is the configuration as its instances wire it, so every instance of one configuration must wire it the
same; every configuration is written, used or not (S3b-1).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s3b-transformers``.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from cimprofiles.units import units
from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem, System

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_values
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl.catalog import HEADER_FIELDS, label, native_name, referenced
from cimhub_gridlabd.importer.topology import WYE_CONNECTIONS, coil_rated, line_voltage, service_phases
from cimhub_gridlabd.schema import gridlabd as schema

NATIVE_CLASS = schema.TransformerConfiguration
PREFIX = "xc_"
BANK_PREFIX = "xb_"
CENTER_TAP = "SINGLE_PHASE_CENTER_TAPPED"
WYE_WYE = "WYE_WYE"
#: connect_type -> (end 1, end 2) TransformerTankEnd.connectionKind; the grounding is the instance's.
CONNECTIONS = {WYE_WYE: ("Y", "Y"), "SINGLE_PHASE": ("Y", "Y"), "DELTA_GWYE": ("D", "Y"), "DELTA_DELTA": ("D", "D")}
#: GridLAB-D's center-tap star of the full winding's R + jX (``transformer.cpp:788``): primary, then each half.
STAR_PRIMARY = (0.5, 0.8)
STAR_HALF = (1.0, 0.4)
#: Center-tap lugs (IEEE C57.12.70) with their instance phase-end numbers, and its windings lug to lug from the
#: polarity end: H1->H2, X1->X2 (s1->N), X2->X3 (N->s2). As the DSS import (S3b-11).
CENTER_TAP_LUGS = (("H1", 1), ("H2", 2), ("X1", 3), ("X3", 4), ("X2", 5))
CENTER_TAP_WINDINGS = (("h1", "h2"), ("x1", "x2"), ("x2", "x3"))

_CONFIGURATION = "TransformerTankConfiguration"
_THERMAL = Field("untranscribed", note="thermal aging model and siting; no network-profile home")
_INRUSH = Field("untranscribed", note="inrush model")
_NOT_MAPPED = "raises when set: it replaces the impedances on a center tap (transformer_configuration.cpp:283), and no deck sets it"
_SERIES = Field("derived", note="percentImpedance = |R + jX| x k x 100, loadLoss = R x k x S (S3b-4, S3b-5); a "
                                "center tap's are the full winding's")
_HALF = Field("derived", note="a center tap's star given whole: must be GridLAB-D's split of one R + jX (impedance = "
                              "0.5R + j0.8X, both halves R + j0.4X); any other split, or on another connection, raises")
_SHUNT = Field("derived", note="noLoadLoss = S / (Rsh x k), percentMagnetizingCurrent = 100 / (Xsh x k) (S3b-6); "
                               "unset: GridLAB-D's 999999999 pu (lossless) is not filled; on a delta connection raises")

FIELDS = {
    "name": Field("copied", ((_CONFIGURATION, "name", None),), "mRID = xc_ + name; a bank xb_ + name, its cans "
                                                                "xc_ + name + _<phase>"),
    **HEADER_FIELDS,
    "connect_type": Field("structural", note="the form and connectionKinds: WYE_WYE and SINGLE_PHASE Y/Y, DELTA_GWYE "
                                             "D/Y, DELTA_DELTA D/D, SINGLE_PHASE_CENTER_TAPPED lugs; unset raises"),
    "install_type": _THERMAL,
    "coolant_type": _THERMAL,
    "cooling_type": _THERMAL,
    "primary_voltage": Field("structural", note="winding 1 ratedU (line to line) and baseU (the coil), S3b-3; a "
                                                "coil-rated wye's is baseU, ratedU on its bus's system (S6)"),
    "secondary_voltage": Field("structural", note="winding 2 ratedU and baseU; a center tap's half (ratedU x 2)"),
    "power_rating": Field("structural", note="ratedS: the whole unit's kVA, else the phase sum (init())"),
    **{f"power{letter}_rating": Field("structural", note="a can's kVA in a bank; a center tap's S on its phase; on a "
                                                         "one-tank WYE_WYE unused, listed when it is not S / n")
       for letter in "ABC"},
    "resistance": _SERIES,
    "reactance": _SERIES,
    "impedance": _SERIES,
    **{f"{part}{half}": _HALF for half in "12" for part in ("resistance", "reactance", "impedance")},
    "shunt_resistance": _SHUNT,
    "shunt_reactance": _SHUNT,
    "shunt_impedance": _SHUNT,
    **{slot: _THERMAL for slot in ("core_coil_weight", "tank_fittings_weight", "oil_volume",
                                   "rated_winding_time_constant", "rated_winding_hot_spot_rise", "rated_top_oil_rise",
                                   "installed_insulation_life")},
    "no_load_loss": Field("structural", note=_NOT_MAPPED),
    "full_load_loss": Field("structural", note=_NOT_MAPPED),
    "reactance_resistance_ratio": Field("structural", note="raises when set: used only with no_load_loss and "
                                                           "full_load_loss"),
    **{slot: _INRUSH for slot in ("magnetization_location", "inrush_saturation_enabled", "L_A", "phi_K", "phi_M",
                                  "I_M", "T_D")},
}


class Wiring(NamedTuple):
    """How instances wire a configuration: what its template depends on beyond the configuration itself."""
    letters: str              # the wired phase letters in ABC order; a one-tank wye's, the first as many of ABC (S6)
    primary: System | None    # a center tap's or a coil-rated wye's primary system (ratedU); None when no instance says
    secondary: System | None = None  # a coil-rated wye's secondary system
    coil_rated: bool = False  # a wye whose voltages rate the coil, phase to neutral (S6)
    service: str | None = None  # a one-phase service's split-phase conductors (topology.service_phases)


def _complex(record, slot: str, real: str, imaginary: str) -> tuple[float, float] | None:
    """``(re, im)`` of a complex slot or its two real slots; both forms set and different raise."""
    whole = getattr(record, slot)
    parts = (getattr(record, real), getattr(record, imaginary))
    split = None if parts == (None, None) else tuple(float(part or 0.0) for part in parts)
    given = None if whole is None else (float(whole.real or 0.0), float(whole.imag or 0.0))
    if given is not None and split is not None and given != split:
        raise ValueError(f"{label(record)}: {native_name(record, slot)} {given} differs from "
                         f"{native_name(record, real)}/{native_name(record, imaginary)} {split}")
    return given or split


def series(config) -> tuple[float, float]:
    """``(R, X)`` per unit of the whole unit (a center tap: the full winding); both must be positive (``:337``)."""
    z = _complex(config, "impedance", "resistance", "reactance")
    halves = [_complex(config, f"impedance{n}", f"resistance{n}", f"reactance{n}") for n in "12"]
    if any(halves):
        if str(config.connect_type) != CENTER_TAP:
            raise ValueError(f"{label(config)}: impedance1/impedance2 on {config.connect_type}; GridLAB-D ignores "
                             "them (a center tap's only)")
        if None in halves or halves[0] != halves[1]:
            raise ValueError(f"{label(config)}: impedance1 {halves[0]} and impedance2 {halves[1]}; only GridLAB-D's "
                             "split (both halves equal) is mapped")
        r, x = halves[0][0] / STAR_HALF[0], halves[0][1] / STAR_HALF[1]
        expected = (STAR_PRIMARY[0] * r, STAR_PRIMARY[1] * x)
        if z is None or not all(math.isclose(a, b, rel_tol=1e-9) for a, b in zip(z, expected)):
            raise ValueError(f"{label(config)}: impedance {z} with halves {halves[0]} is not GridLAB-D's split of one "
                             f"R + jX (impedance would be {expected}); a center tap's own star is not mapped")
        return r, x
    if z is None or z[0] <= 0 or z[1] <= 0:
        raise ValueError(f"{label(config)}: impedance {z}; resistance and reactance must be positive "
                         "(transformer_configuration.cpp:337)")
    return z


def shunt(config) -> tuple[float | None, float | None]:
    """``(Rsh, Xsh)`` per unit of the parallel branch; an unset part is GridLAB-D's lossless 999999999."""
    z = _complex(config, "shunt_impedance", "shunt_resistance", "shunt_reactance")
    if z is None:
        return None, None
    if str(config.connect_type) not in (*WYE_CONNECTIONS, CENTER_TAP):
        raise ValueError(f"{label(config)}: a shunt on {config.connect_type}; GridLAB-D ignores it")
    resistance = config.shunt_resistance if config.shunt_impedance is None else z[0]
    reactance = config.shunt_reactance if config.shunt_impedance is None else z[1]
    return (None if resistance is None else float(resistance)), (None if reactance is None else float(reactance))


def phase_kva(config, letter: str) -> float:
    """The kVA of phase ``letter``: its rating, else (no phase rated) a third of the total (``init():190``)."""
    rated = [getattr(config, f"power{other}_rating") for other in "ABC"]
    if not any(rated):
        return total_kva(config) / 3
    return float(getattr(config, f"power{letter}_rating") or 0.0)


def total_kva(config) -> float:
    """``power_rating``, else the phase sum; a sum that misses it by more than 1 % raises (``:234``)."""
    phases = sum(float(getattr(config, f"power{letter}_rating") or 0.0) for letter in "ABC")
    total = float(config.power_rating) if config.power_rating else phases
    if total <= 0:
        raise ValueError(f"{label(config)}: power_rating unset or 0 (transformer_configuration.cpp:227)")
    if phases and abs(total - phases) / total > 0.01:
        raise ValueError(f"{label(config)}: phase ratings sum to {phases}, not power_rating {total} "
                         "(transformer_configuration.cpp:234)")
    return total


def check(config) -> None:
    """What GridLAB-D throws on, and the slots no mapping covers yet."""
    if str(config.connect_type) not in (*CONNECTIONS, CENTER_TAP):
        raise ValueError(f"{label(config)}: connect_type {config.connect_type or 'unset'}; mapped are "
                         f"{', '.join((*CONNECTIONS, CENTER_TAP))}")
    for slot in ("primary_voltage", "secondary_voltage"):
        if not getattr(config, slot):
            raise ValueError(f"{label(config)}: {slot} unset or 0 (transformer_configuration.cpp:211)")
    for slot in ("no_load_loss", "full_load_loss", "reactance_resistance_ratio"):
        if getattr(config, slot) is not None:
            raise ValueError(f"{label(config)}: {slot} set; not mapped (no deck sets it)")


def default_wiring(config) -> Wiring:
    """An unused configuration's wiring: the phases it rates, else all three."""
    rated = "".join(letter for letter in "ABC" if getattr(config, f"power{letter}_rating"))
    if str(config.connect_type) == CENTER_TAP:
        if len(rated) != 1:
            raise ValueError(f"{label(config)}: an unused center tap rated on {rated or 'no phase'}; its phase is "
                             "unknown")
        return Wiring(rated, None)
    return Wiring(rated if str(config.connect_type) in WYE_CONNECTIONS and rated else "ABC", None)


def center_tapped(config, wiring: Wiring) -> bool:
    """A center tap's template: ``SINGLE_PHASE_CENTER_TAPPED``, or a 240 V one-phase service (the user's rule:
    s1 N s2, its one coil written as GridLAB-D's center-tap star)."""
    return str(config.connect_type) == CENTER_TAP or wiring.service == "s1s2N"


def is_bank(config, wiring: Wiring) -> bool:
    """A wye whose wired phases are all rated, unequally (S3b-9)."""
    if str(config.connect_type) not in WYE_CONNECTIONS:
        return False
    kvas = [getattr(config, f"power{letter}_rating") for letter in wiring.letters]
    return all(kvas) and len(set(kvas)) > 1


def bank_numbers(letters: str) -> dict[tuple[int, str], int]:
    """``{(end, phase): conductor}`` of a bank, numbered end 1's phases then N, then end 2's (S3b-9)."""
    numbers, sequence = {}, 1
    for end in (1, 2):
        for phase in (*letters, "N"):
            numbers[(end, phase)] = sequence
            sequence += 1
    return numbers


def tank_name(config, letter: str | None = None) -> str:
    """The TankConfiguration mRID of a configuration, or of its can on ``letter`` in a bank."""
    return mrid(PREFIX, f"{config.name}_{letter}" if letter else config.name)


class _Tank(NamedTuple):
    """One TankConfiguration's nameplate values."""
    s_tank: float   # kVA of the tank
    k: float        # GridLAB-D's per unit -> the tank's own (S3b-4)


def _percent(per_unit: float) -> float:
    return units.Quantity(per_unit, "dimensionless").to("percent").magnitude


def _kw(model: GlmModel, config, kva: float) -> float:
    return units.Quantity(kva, registry_unit(model.unit(config, "power_rating"))).to("kW").magnitude


def _nameplate(model: GlmModel, config, tank: _Tank) -> list[str | None]:
    """``percentImpedance``, ``loadLoss`` (kW), ``noLoadLoss`` (kW), ``percentMagnetizingCurrent`` of one tank."""
    r, x = series(config)
    resistance, reactance = shunt(config)
    no_load = None if resistance is None else _kw(model, config, tank.s_tank / (resistance * tank.k))
    magnetizing = None if reactance is None else _percent(1 / (reactance * tank.k))
    return [cell(_percent(math.hypot(r, x) * tank.k)), cell(_kw(model, config, r * tank.k * tank.s_tank)),
            cell(no_load), cell(magnetizing)]


_NAMEPLATE = [Column("percentImpedance", "percent"), Column("loadLoss", "kW"), Column("noLoadLoss", "kW"),
              Column("percentMagnetizingCurrent", "percent")]


class _Statements:
    """Rows by (class, columns), written in reference order."""
    ORDER = ("TransformerBankConfiguration", _CONFIGURATION, "TransformerTankEnd", "TransformerLug",
             "TransformerWinding")

    def __init__(self):
        self.rows: dict[tuple[str, tuple[Column, ...]], list[Row]] = {}

    def add(self, cls: str, columns: list[Column], row: Row) -> None:
        self.rows.setdefault((cls, tuple(columns)), []).append(row)

    def tables(self) -> list[Table]:
        keys = sorted(self.rows, key=lambda key: self.ORDER.index(key[0]))
        return [Table(cls, list(columns), self.rows[(cls, columns)]) for cls, columns in keys]


def _winding_columns(model: GlmModel, config, ends: list[Column]) -> list[Column]:
    volts = registry_unit(model.unit(config, "primary_voltage"))
    if registry_unit(model.unit(config, "secondary_voltage")) != volts:
        raise ValueError(f"{label(config)}: primary and secondary voltages in different units")
    kva = registry_unit(model.unit(config, "power_rating"))
    return [Column("mRID"), Column("TankConfiguration"), Column("ratedU", volts), Column("baseU", volts),
            Column("ratedS", kva), Column("baseS", kva), *ends]


def _k(wiring: Wiring, s_coil: float, s_total: float) -> float:
    """GridLAB-D's per unit (on the written ``secondary_voltage`` and the whole unit's kVA) -> a coil's own
    (``baseU``² / ``baseS``), S3b-4: ``3 S_coil / S_total`` when the written voltage is line to line, ``S_coil /
    S_total`` when it is the coil's (S6)."""
    return (1 if wiring.coil_rated else 3) * s_coil / s_total


def _voltages(config, wiring: Wiring, slot: str, kind: str) -> tuple[float, float]:
    """``(ratedU, baseU)`` of the winding ``slot`` gives: the written voltage line to line and its coil (S3b-3), or
    the coil's and its line voltage on the system its bus is on (S6)."""
    written = float(getattr(config, slot))
    if wiring.coil_rated:
        return line_voltage(written, wiring.primary if slot == "primary_voltage" else wiring.secondary), written
    return written, written / math.sqrt(3) if kind == "Y" else written


def _tank_ends(model: GlmModel, config, wiring: Wiring, out: _Statements, comment: str | None) -> None:
    xc = tank_name(config)
    total = total_kva(config)
    n = len(wiring.letters)
    out.add(_CONFIGURATION, [Column("mRID"), Column("name"), *_NAMEPLATE],
            Row([xc, str(config.name), *_nameplate(model, config, _Tank(total, _k(wiring, total / n, total)))],
                comment=comment))
    columns = _winding_columns(model, config, [Column("FromTransformerEnd")])
    kinds = CONNECTIONS[str(config.connect_type)]
    if wiring.service == "s1N":  # a 120 V service's leg is one split-phase half, as a center tap's (S6-10)
        kinds = (kinds[0], "I")
    for number, (kind, slot) in enumerate(zip(kinds, ("primary_voltage", "secondary_voltage")), start=1):
        out.add("TransformerTankEnd", [Column("mRID"), Column("TankConfiguration"), Column("endNumber"),
                                       Column("connectionKind")], Row([f"{xc}_end_{number}", xc, str(number), kind]))
        rated_u, base_u = _voltages(config, wiring, slot, kind)
        out.add("TransformerWinding", columns, Row([f"{xc}_wdg_{number}", xc, cell(rated_u), cell(base_u),
                                                    cell(total), cell(total / n), f"{xc}_end_{number}"]))


def _lugged_windings(xc: str, windings: list[tuple[float, float, float, float]], lugs: tuple, columns,
                     out: _Statements) -> None:
    for number, ((rated_u, base_u, rated_s, base_s), (start, end)) in enumerate(zip(windings, lugs), start=1):
        out.add("TransformerWinding", columns, Row([f"{xc}_wdg_{number}", xc, cell(rated_u), cell(base_u),
                                                    cell(rated_s), cell(base_s), f"{xc}_lug_{start}",
                                                    f"{xc}_lug_{end}"]))


_LUG_COLUMNS = [Column("mRID"), Column("TankConfiguration"), Column("designation"), Column("sequenceNumber")]


def _bank(model: GlmModel, config, wiring: Wiring, out: _Statements, comment: str | None) -> None:
    xb = mrid(BANK_PREFIX, config.name)
    total = total_kva(config)
    out.add("TransformerBankConfiguration", [Column("mRID"), Column("name")], Row([xb, str(config.name)],
                                                                                   comment=comment))
    numbers = bank_numbers(wiring.letters)
    columns = _winding_columns(model, config, [Column("FromTransformerLug"), Column("ToTransformerLug")])
    for letter in wiring.letters:
        xc = tank_name(config, letter)
        can = phase_kva(config, letter)
        out.add(_CONFIGURATION, [Column("mRID"), Column("name"), *_NAMEPLATE, Column("BankConfiguration")],
                Row([xc, f"{config.name}_{letter}", *_nameplate(model, config, _Tank(can, _k(wiring, can, total))), xb]))
        for designation, (end, phase) in (("H1", (1, letter)), ("H2", (1, "N")), ("X1", (2, letter)),
                                          ("X2", (2, "N"))):
            out.add("TransformerLug", _LUG_COLUMNS, Row([f"{xc}_lug_{designation.lower()}", xc, designation,
                                                         str(numbers[(end, phase)])]))
        windings = [(*_voltages(config, wiring, slot, "Y"), can, can) for slot in ("primary_voltage", "secondary_voltage")]
        _lugged_windings(xc, windings, (("h1", "h2"), ("x1", "x2")), columns, out)


def _center_tap(model: GlmModel, config, wiring: Wiring, out: _Statements, comment: str | None) -> None:
    """Lugs H1 H2 X1 X3 X2 and windings H1->H2, X1->X2, X2->X3; the %Z fields the full winding's. A 240 V service's
    one coil is that full winding: its kVA is the unit's, each half is half its secondary_voltage, and GridLAB-D's
    R + jX on secondary_voltage^2 / power_rating is already the full winding's (k = 1)."""
    xc = tank_name(config)
    service = str(config.connect_type) != CENTER_TAP
    s = total_kva(config) if service else phase_kva(config, wiring.letters)
    if s <= 0:
        raise ValueError(f"{label(config)}: power{wiring.letters}_rating unset or 0 on a center tap wired on phase "
                         f"{wiring.letters} (transformer.cpp:772)")
    out.add(_CONFIGURATION, [Column("mRID"), Column("name"), *_NAMEPLATE],
            Row([xc, str(config.name), *_nameplate(model, config, _Tank(s, 1.0))], comment=comment))
    for designation, sequence in CENTER_TAP_LUGS:
        out.add("TransformerLug", _LUG_COLUMNS, Row([f"{xc}_lug_{designation.lower()}", xc, designation,
                                                     str(sequence)]))
    v1, v2 = float(config.primary_voltage), float(config.secondary_voltage)
    if service:
        v2 = v2 / 2
    primary = None if wiring.primary is None else line_voltage(v1, wiring.primary)
    half = (line_voltage(v2, System.SPLIT_PHASE), v2, s / 2, s)
    columns = _winding_columns(model, config, [Column("FromTransformerLug"), Column("ToTransformerLug")])
    _lugged_windings(xc, [(primary, v1, s, s), half, half], CENTER_TAP_WINDINGS, columns, out)


def _listed_phase_ratings(config, wiring: Wiring) -> str | None:
    """A one-tank wye's phase ratings when they are not S / n on its wired phases (S3b-9)."""
    if str(config.connect_type) not in WYE_CONNECTIONS or not any(getattr(config, f"power{p}_rating") for p in "ABC"):
        return None
    share = total_kva(config) / len(wiring.letters)
    fits = all(getattr(config, f"power{p}_rating") == (share if p in wiring.letters else None) or
               (p not in wiring.letters and not getattr(config, f"power{p}_rating")) for p in "ABC")
    if fits:
        return None
    written = ", ".join(f"power{p}_rating={getattr(config, f'power{p}_rating')}" for p in "ABC"
                        if getattr(config, f"power{p}_rating") is not None)
    return f"untranscribed (one tank of power_rating on {wiring.letters}, S3b-9): {written}"


def map_transformer_configuration(model: GlmModel, wirings: dict[str, Wiring]) -> Document:
    """Every configuration as a template, wired as ``wirings`` (by configuration name) says, else by its own
    ratings."""
    configs = model.list_by_class(NATIVE_CLASS)
    out = _Statements()
    unused = []
    for config in configs:
        check(config)
        wiring = wirings.get(str(config.name))
        if wiring is None:
            unused.append(str(config.name))
            wiring = default_wiring(config)
        notes = [untranscribed_values(FIELDS, config)]
        if wiring.primary is None and str(config.connect_type) == CENTER_TAP:
            notes.append("not filled: winding 1 ratedU (no instance says its primary system)")
        if str(config.name) in unused and str(config.connect_type) in WYE_CONNECTIONS:
            notes.append("voltages read line to line (S3b-3): no instance says whether they rate the coil (S6)")
        if not is_bank(config, wiring):
            notes.append(_listed_phase_ratings(config, wiring))
        comment = "\n".join(note for note in notes if note) or None
        if center_tapped(config, wiring):
            _center_tap(model, config, wiring, out, comment)
        elif is_bank(config, wiring):
            _bank(model, config, wiring, out, comment)
        else:
            _tank_ends(model, config, wiring, out, comment)
    if not configs:
        return Document(name=NATIVE_CLASS.class_name, statements=[], profile=CIM_PROFILE)
    comment = (f"GridLAB-D transformer_configuration -> TransformerTankConfiguration (catalog; %Z on the tank's own "
               f"nameplate).\nSource table: transformer_configuration (records: {len(configs)})\n"
               "Mapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s3b-transformers")
    if unused:
        comment += "\nno instance (built from its own ratings): " + ", ".join(unused)
    return Document(name=NATIVE_CLASS.class_name, statements=out.tables(), profile=CIM_PROFILE, comment=comment)


def wiring_of(model: GlmModel, xf, config, roots: dict[str, str], buses: dict[str, BusSystem]) -> Wiring:
    """How ``xf`` wires its configuration: its letters (a one-tank wye's template depends only on how many, S6); a
    center tap's primary system; a coil-rated wye's systems."""
    letters = "".join(letter for letter in "ABC" if letter in str(xf.phases or ""))
    connect = str(config.connect_type)
    primary, secondary = buses[roots[xf.from_node]].system, buses[roots[xf.to]].system
    if connect == CENTER_TAP:
        return Wiring(letters, primary)
    if connect not in WYE_CONNECTIONS:
        return Wiring(letters, None)
    if not any(getattr(config, f"power{p}_rating") for p in "ABC"):
        letters = "ABC"[:len(letters)]
    if coil_rated(model, xf, config, roots):
        return Wiring(letters, primary, secondary, coil_rated=True, service=service_phases(model, xf, config, roots))
    return Wiring(letters, None)


def wirings(model: GlmModel, roots: dict[str, str], buses: dict[str, BusSystem]) -> dict[str, Wiring]:
    """``{configuration name: Wiring}`` from every transformer; two that wire one configuration differently raise."""
    found: dict[str, tuple[str, Wiring]] = {}
    for xf in model.list_by_class(schema.Transformer):
        config = configuration_of(model, xf)
        wiring = wiring_of(model, xf, config, roots, buses)
        first = found.setdefault(str(config.name), (str(xf.name), wiring))
        if first[1] != wiring:
            raise ValueError(f"{label(config)}: transformers {first[0]} ({_described(first[1])}) and {xf.name} "
                             f"({_described(wiring)}) wire it differently; one template per configuration")
    return {name: wiring for name, (_, wiring) in found.items()}


def _described(wiring: Wiring) -> str:
    if wiring.coil_rated:
        service = f", a {wiring.service} service" if wiring.service else ""
        return f"on {wiring.letters}, coil-rated, {wiring.primary.name} to {wiring.secondary.name}{service}"
    primary = f", primary on a {wiring.primary.name} system" if wiring.primary else ""
    return f"on {wiring.letters}{primary}"


def configuration_of(model: GlmModel, xf):
    if xf.configuration is None:
        raise ValueError(f"{label(xf)}: configuration unset (transformer.cpp throws)")
    return referenced(model, xf, "configuration", (NATIVE_CLASS,))

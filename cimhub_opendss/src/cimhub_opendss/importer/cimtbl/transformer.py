"""OpenDSS ``Transformer`` -> ``transformer.cimtbl``.

Every DSS Transformer becomes a ``PowerTransformer`` with one ``PowerTransformerEnd`` per bus.
The end's terminal carries the phases (``ABCN``, ``AN``, ``AB``, ``s1s2N``). A Transformer a RegControl names
with equal winding kV is a ``VoltageRegulator`` instead (DSS-13): two ``AutoTransformerEnd``s with the nameplate
(``baseU``, ``ratedS``, a PhaseCode ``phase``) and the engine's stand-in mesh impedance. A step-down one (an LTC)
stays a PowerTransformer. An instance by ``XfmrCode`` waits for the template (S3b) unless it is regulated; then it
takes its code's values, as the engine copies them (CIM has no AutoTransformer template).

- 3-phase, by balanced ends: ``ratedU`` (the DSS kV, phase-to-phase), ``ratedS`` and ``r``
  (percent on the end's own rating) on each end; ``x`` on the mesh between ends, in percent on
  winding 1's kVA, so the From end must carry that kVA; the magnetizing branch on end 1 (``b``,
  ``g`` in percent).
- 1-phase, by phase ends: one ``TransformerTank``; one ``TransformerPhaseEnd`` per phase
  conductor on each bus (``sequenceNumber`` unique in the transformer, end 1 first); one
  ``TransformerWinding`` per DSS winding, between the phase ends of its two conductors; ``x``
  on the mesh between windings.

Winding ratings follow the nameplate rule (the `cimtbl-shapes` skill, transformer ratings):
``baseU`` = the DSS winding kV (the coil voltage), ``ratedU`` phase-to-phase, ``baseS`` =
winding 1's kVA on every coil, split-phase halves rated kVA / 2.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#transformer``.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_names
from cimtopology.core import BusSystem
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Transformer
PREFIX = "xf_"

_SCALAR = "the active-winding form; the reader folds wdg= blocks into the arrays, and a bare value raises"
_THERMAL = "thermal model; no home in the network profile parts"
_RATING = "instance OperationalLimitSet or untranscribed (plan D9)"
_TAP_CHANGER = "the RatioTapChanger range of a regulated transformer (regcontrol.cimtbl); else untranscribed"
_RELIABILITY = "reliability data; no home in the network profile parts"

FIELDS = {
    "name": Field("copied", (("PowerTransformer", "name", None),), "mRID = xf_ + name, lowercased"),
    "phases": Field("structural", note="1 = by phase ends, 3 = by balanced ends; default 3"),
    "windings": Field("structural", note="2 or 3; must match the buses"),
    "wdg": Field("structural", note="the winding Rneut/Xneut belong to (the reader's tag); none = the last"),
    "bus": Field("structural", note=_SCALAR),
    "conn": Field("structural", note=_SCALAR),
    "kV": Field("structural", note=_SCALAR),
    "kVA": Field("structural", note=_SCALAR),
    "tap": Field("structural", note=_SCALAR),
    "pct_R": Field("structural", note=_SCALAR),
    "Rneut": Field("structural", note="rground (ohm) of its winding's end when >= 0; negative = no impedance"),
    "Xneut": Field("structural", note="xground (ohm) of its winding's end, with Rneut >= 0"),
    "buses": Field("structural", note="end node and terminal phases; one end per distinct bus"),
    "conns": Field("structural", note="connectionKind, grounded, default nodes; default wye"),
    "kVs": Field("structural", note="3-phase: end ratedU; 1-phase: winding baseU, ratedU derived (x sqrt 3, x 2)"),
    "kVAs": Field("structural", note="end ratedS / winding ratedS (halves / 2); winding 1's kVA is every baseS"),
    "taps": Field("structural", note="the regulated winding's tap is RatioTapChanger.step (regcontrol.cimtbl); "
                                     "any other tap other than 1 raises"),
    "XHL": Field("structural", note="mesh 1-2 x (percent on winding 1's kVA); default 7"),
    "XHT": Field("structural", note="mesh 1-3 x; default 35"),
    "XLT": Field("structural", note="mesh 2-3 x; default 30"),
    "X12": Field("structural", note="alias of XHL"),
    "X13": Field("structural", note="alias of XHT"),
    "X23": Field("structural", note="alias of XLT"),
    "Xscarray": Field("untranscribed", note="for more than 3 windings, which raise"),
    "pct_Rs": Field("structural", note="3-phase: end r (percent); 1-phase: winding r (percent); default 0.2"),
    "pct_loadloss": Field("derived", note="when pct_Rs is unset, r = loadloss / 2 on windings 1 and 2; "
                                          "set with pct_Rs, the two must agree"),
    "pct_noloadloss": Field("derived", note="3-phase: end 1 g (percent); 1-phase: tank noLoadLoss = % x kVA; a "
                                            "regulator has no home for it (row comment)"),
    "pct_imag": Field("structural", note="3-phase: end 1 b (percent); 1-phase: tank percentMagnetizingCurrent; a "
                                         "regulator has no home for it (row comment)"),
    "thermal": Field("untranscribed", note=_THERMAL),
    "n": Field("untranscribed", note=_THERMAL),
    "m": Field("untranscribed", note=_THERMAL),
    "flrise": Field("untranscribed", note=_THERMAL),
    "hsrise": Field("untranscribed", note=_THERMAL),
    "normhkVA": Field("untranscribed", note=_RATING),
    "emerghkVA": Field("untranscribed", note=_RATING),
    "Seasons": Field("untranscribed", note=_RATING),
    "Ratings": Field("untranscribed", note=_RATING),
    "normamps": Field("untranscribed", note=_RATING),
    "emergamps": Field("untranscribed", note=_RATING),
    "sub": Field("untranscribed", note="DSS report flag"),
    "subname": Field("untranscribed", note="DSS report label"),
    "MaxTap": Field("structural", note=_TAP_CHANGER + "; default 1.1"),
    "MinTap": Field("structural", note=_TAP_CHANGER + "; default 0.9"),
    "NumTaps": Field("structural", note=_TAP_CHANGER + "; default 32"),
    "ppm_antifloat": Field("untranscribed", note="numerical aid of the DSS solver"),
    "bank": Field("untranscribed", note="each DSS Transformer is its own PowerTransformer"),
    "XfmrCode": Field("structural", note="a regulated instance takes the code's values (with_code); any other "
                                         "waits for the template (S3b) and is counted on the master"),
    "XRConst": Field("untranscribed", note="harmonics option"),
    "LeadLag": Field("untranscribed", note="PowerTransformer.vectorGroup clock; vectorGroup not mapped yet"),
    "Core": Field("untranscribed", note="core type; no home in the network profile parts"),
    "RdcOhms": Field("untranscribed", note="home TransformerWinding.rDC; not mapped until a deck sets it"),
    "faultrate": Field("untranscribed", note=_RELIABILITY),
    "pct_perm": Field("untranscribed", note=_RELIABILITY),
    "repair": Field("untranscribed", note=_RELIABILITY),
    "basefreq": Field("untranscribed", note="no home on a transformer"),
    "enabled": Field("copied", (("PowerTransformer", "normallyInService", None),)),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

#: DSS defaults used when the deck leaves a slot unset; each use is listed in the row comment.
DEFAULT_R_PERCENT = 0.2
DEFAULT_X_PERCENT = {(1, 2): 7.0, (1, 3): 35.0, (2, 3): 30.0}
_X_SLOTS = {(1, 2): ("XHL", "X12"), (1, 3): ("XHT", "X13"), (2, 3): ("XLT", "X23")}
_SCALAR_SLOTS = ("bus", "conn", "kV", "kVA", "tap", "pct_R")

_NODE_PHASE = {1: "A", 2: "B", 3: "C", 0: "N"}
_SPLIT_PHASE = {1: "s1", 2: "s2", 0: "N"}
_PHASE_ORDER = ("A", "B", "C", "s1", "s2", "N")
_SQRT3 = math.sqrt(3)

_PROVENANCE = """OpenDSS Transformer -> PowerTransformer + PowerTransformerEnd per bus;
1-phase: TransformerTank + TransformerPhaseEnd + TransformerWinding; 3-phase: balanced ends.
Source table: Transformer (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#transformer"""


class Winding(NamedTuple):
    """One DSS winding after defaults: its bus, one node per conductor, and its ratings."""

    number: int
    bus: str
    nodes: tuple[int, ...]
    wye: bool
    kv: float
    kva: float
    r_percent: float


class End(NamedTuple):
    """One PowerTransformerEnd: a bus and the phase of each node on it."""

    number: int
    bus: str
    phase_of_node: dict[int, str]
    windings: tuple[Winding, ...]
    split_phase: bool

    @property
    def phases(self) -> list[str]:
        return sorted(self.phase_of_node.values(), key=_PHASE_ORDER.index)


def parse_bus(spec: str) -> tuple[str, tuple[int, ...]]:
    """``'650.1.2.3.4'`` -> ``('650', (1, 2, 3, 4))``; the name lowercased (DSS names are case-insensitive)."""
    name, *nodes = str(spec).split(".")
    return name.lower(), tuple(int(node) for node in nodes)


def winding_nodes(given: tuple[int, ...], phases: int, wye: bool, *, name: str) -> tuple[int, ...]:
    """One node per conductor: the bus spec's nodes, then the DSS defaults (conductor k on node k, the
    extra neutral conductor on 0). A 3-phase delta winding uses its first three conductors."""
    defaults = (*range(1, phases + 1), 0)
    if len(given) > len(defaults):
        raise ValueError(f"Transformer {name}: bus nodes {given} exceed the {len(defaults)} conductors")
    nodes = given + defaults[len(given):]
    return nodes if (wye or phases == 1) else nodes[:phases]


def is_split_phase(on_bus) -> bool:
    """Windings 2 and 3 of a 1-phase transformer, on one bus, both on node 0, with nodes 1 and 2: a
    split-phase secondary (s1, s2, N). ``on_bus`` holds the windings on that bus (``.number``, ``.nodes``)."""
    nodes = {node for winding in on_bus for node in winding.nodes}
    return ([winding.number for winding in on_bus] == [2, 3]
            and all(0 in winding.nodes for winding in on_bus) and nodes == {0, 1, 2})


def with_code(xf, codes: Mapping[str, object]):
    """``(Transformer, comment)``: an instance by XfmrCode with every slot it leaves unset taken from its code, as
    the engine copies them; an unknown code raises."""
    code = codes.get(str(xf.XfmrCode).lower())
    if code is None:
        raise ValueError(f"Transformer {xf.name}: XfmrCode={xf.XfmrCode} is not defined")
    own = {field.name.lower(): field.name for field in dataclasses.fields(xf)}
    filled = {}
    for field in (f.name for f in dataclasses.fields(code)):
        if field in ("name", "like"):
            continue
        value, target = getattr(code, field), own.get(field.lower())
        if target is None:
            raise ValueError(f"XfmrCode {code.name}: {field} has no Transformer slot")
        if value in (None, []):
            continue
        if getattr(xf, target) not in (None, []):
            if FIELDS[target].kind != "untranscribed":
                raise ValueError(f"Transformer {xf.name}: sets {target}, which its XfmrCode {code.name} also sets; "
                                 "the template is the one source (DSS keeps the last, which the reader does not "
                                 "record)")
            continue
        filled[target] = value
    return dataclasses.replace(xf, **filled), f"values from XfmrCode {code.name}"


def regulated_transformers(native) -> dict[str, object]:
    """``{lowered transformer name: RegControl}``; a transformer two RegControls name raises."""
    regulated: dict[str, object] = {}
    for control in native.list_by_class(schema.Regcontrol):
        key = str(control.transformer).lower()
        if key in regulated:
            raise ValueError(f"Transformer {control.transformer}: named by RegControls {regulated[key].name} and "
                             f"{control.name}; one is mapped")
        regulated[key] = control
    return regulated


def is_center_tap(phases: int, windings: list[Winding], ends: list[End]) -> bool:
    """A 1-phase, 3-winding transformer whose windings 2 and 3 are a split-phase secondary (its template has lugs)."""
    return phases == 1 and len(windings) == 3 and ends[-1].split_phase


def is_regulator(windings: list[Winding]) -> bool:
    """A regulated transformer with equal winding kV is a regulator; a step-down one is an LTC (DSS-13)."""
    return len({winding.kv for winding in windings}) == 1


def _defaulted(slot: str, value, notes: list[str]):
    notes.append(f"{slot}={cell(value)}")
    return value


def windings_of(xf, phases: int, notes: list[str], *, regulated: bool = False) -> list[Winding]:
    """The windings of one transformer, with DSS defaults filled and listed in ``notes``. Only a regulated
    transformer may have a tap other than 1 (its RatioTapChanger.step)."""
    name = xf.name
    for slot in _SCALAR_SLOTS:
        if getattr(xf, slot) is not None:
            raise ValueError(f"Transformer {name}: {slot} is set without wdg= or an array; "
                             "the winding it belongs to is not recorded")
    buses = list(xf.buses or [])
    count = xf.windings if xf.windings is not None else len(buses)
    if count not in (2, 3) or len(buses) != count:
        raise ValueError(f"Transformer {name}: windings={xf.windings} with buses {buses}; 2 or 3 windings, one bus each")
    for slot in ("kVs", "kVAs"):
        if len(getattr(xf, slot) or []) != count:
            raise ValueError(f"Transformer {name}: {slot}={getattr(xf, slot)} needs {count} values")
    if not regulated and any(float(tap) != 1.0 for tap in xf.taps or []):
        raise ValueError(f"Transformer {name}: taps={xf.taps} with no RegControl; a fixed tap is not mapped yet")

    conns = [cell(conn) for conn in xf.conns or []] or [_defaulted("conns", "wye", notes)] * count
    if len(conns) != count:
        raise ValueError(f"Transformer {name}: conns={conns} needs {count} values")
    r_percent = _r_percent(xf, count, notes)
    windings = []
    for index, (spec, conn, kv, kva, r) in enumerate(zip(buses, conns, xf.kVs, xf.kVAs, r_percent), start=1):
        bus, given = parse_bus(spec)
        wye = conn.lower() == "wye"
        windings.append(Winding(index, bus, winding_nodes(given, phases, wye, name=name), wye,
                                float(kv), float(kva), r))
    return windings


def _r_percent(xf, count: int, notes: list[str]) -> list[float]:
    """Per-winding %R: ``pct_Rs``, else ``pct_loadloss`` split over windings 1 and 2 (DSS), else 0.2 each."""
    if xf.pct_Rs:
        r = [float(value) for value in xf.pct_Rs]
        if len(r) != count:
            raise ValueError(f"Transformer {xf.name}: pct_Rs={xf.pct_Rs} needs {count} values")
        if xf.pct_loadloss is not None and not math.isclose(r[0] + r[1], float(xf.pct_loadloss), rel_tol=1e-9):
            raise ValueError(f"Transformer {xf.name}: pct_Rs={xf.pct_Rs} and pct_loadloss={xf.pct_loadloss} "
                             "disagree; DSS keeps whichever was set last, which the reader does not record")
        return r
    if xf.pct_loadloss is not None:
        half = float(xf.pct_loadloss) / 2
        if count == 2:
            return [half, half]
        return [half, half, _defaulted("pct_Rs[3]", DEFAULT_R_PERCENT, notes)]
    return [_defaulted("pct_Rs", DEFAULT_R_PERCENT, notes)] + [DEFAULT_R_PERCENT] * (count - 1)


def _x_percent(xf, pair: tuple[int, int], notes: list[str]) -> float:
    dss_name, alias = _X_SLOTS[pair]
    values = {float(v) for v in (getattr(xf, dss_name), getattr(xf, alias)) if v is not None}
    if len(values) > 1:
        raise ValueError(f"Transformer {xf.name}: {dss_name} and {alias} disagree ({sorted(values)})")
    if not values:
        return _defaulted(dss_name, DEFAULT_X_PERCENT[pair], notes)
    return values.pop()


def ends_of(windings: list[Winding], phases: int, *, name: str) -> list[End]:
    """One end per distinct bus, numbered in winding order. On a 1-phase transformer, windings 2 and 3
    on one bus, both using node 0, with nodes 1 and 2, are a split-phase secondary (s1, s2, N)."""
    by_bus: dict[str, list[Winding]] = {}
    for winding in windings:
        by_bus.setdefault(winding.bus, []).append(winding)
    ends = []
    for number, (bus, on_bus) in enumerate(by_bus.items(), start=1):
        nodes = {node for winding in on_bus for node in winding.nodes}
        split = phases == 1 and is_split_phase(on_bus)
        if len(on_bus) > 1 and not split:
            raise ValueError(f"Transformer {name}: windings {[w.number for w in on_bus]} share bus {bus} "
                             "but are not a split-phase secondary")
        if phases == 3:
            [winding] = on_bus
            if winding.nodes[:3] != (1, 2, 3):
                raise ValueError(f"Transformer {name}: bus {bus} phase nodes {winding.nodes[:3]}; "
                                 "only 1.2.3 is mapped")
            phase_of_node = dict(zip(winding.nodes, ("A", "B", "C", "N")))  # the neutral may sit on any node
        else:
            names = _SPLIT_PHASE if split else _NODE_PHASE
            unknown = nodes - names.keys()
            if unknown:
                raise ValueError(f"Transformer {name}: bus {bus} uses nodes {sorted(unknown)}, which have no phase")
            phase_of_node = {node: names[node] for node in nodes}
        ends.append(End(number, bus, phase_of_node, tuple(on_bus), split))
    return ends


def _neutral(xf, winding: Winding, count: int) -> tuple[bool, float | None, float | None]:
    """(grounded, rground, xground) of a wye winding. Rneut/Xneut belong to winding ``wdg``, else the last."""
    neutral_winding = int(xf.wdg) if xf.wdg is not None else count
    impedance = (xf.Rneut is not None and float(xf.Rneut) >= 0) and winding.number == neutral_winding
    if impedance:
        return True, float(xf.Rneut), float(xf.Xneut or 0.0)
    return winding.nodes[-1] == 0, None, None


def _row_comment(notes: list[str]) -> str | None:
    return f"defaulted: {', '.join(notes)}" if notes else None


class _Tables:
    """The rows of one document, gathered per table so each table is written once."""

    def __init__(self):
        self.transformers: list[Row] = []
        self.balanced_ends: list[Row] = []
        self.balanced_mesh: list[Row] = []
        self.phase_end_ends: list[Row] = []
        self.tanks: list[Row] = []
        self.phase_ends: list[Row] = []
        self.coils: list[Row] = []
        self.coil_mesh: list[Row] = []
        self.template_tanks: list[Row] = []
        self.template_phase_ends: list[Row] = []
        self.regulators: list[Row] = []
        self.auto_ends: list[Row] = []
        self.auto_mesh: list[Row] = []


def _map_three_phase(xf, xf_id: str, windings: list[Winding], ends: list[End],
                     buses: Mapping[str, BusSystem], rows: _Tables, notes: list[str]) -> None:
    for end in ends:
        [winding] = end.windings
        if winding.wye:
            grounded, rground, xground = _neutral(xf, winding, len(windings))
            kind = "Yn" if grounded else "Y"
        else:
            grounded, rground, xground, kind = False, None, None, "D"
        phases = "".join(end.phases)
        magnetizing = (xf.pct_imag, xf.pct_noloadloss) if end.number == 1 else (None, None)
        rows.balanced_ends.append(Row([
            f"{xf_id}_{end.number}", xf_id, end.bus, phases, str(end.number), kind, cell(grounded),
            cell(rground), cell(xground), cell(winding.kv), cell(winding.kva), cell(winding.r_percent),
            cell(magnetizing[0]), cell(magnetizing[1]), buses[end.bus].base_voltage,
        ]))
    for i, j in [(1, 2), (1, 3), (2, 3)][: 1 if len(ends) == 2 else 3]:
        if windings[i - 1].kva != windings[0].kva:
            raise ValueError(f"Transformer {xf.name}: mesh {i}-{j} x is on winding 1's kVA "
                             f"({windings[0].kva}), but end {i} is rated {windings[i - 1].kva}")
        rows.balanced_mesh.append(Row([f"{xf_id}_mesh_{i}{j}", f"{xf_id}_{i}", f"{xf_id}_{j}",
                                       cell(_x_percent(xf, (i, j), notes))]))


def coil_rated_u(winding: Winding, phase_from: str, phase_to: str, system: BusSystem) -> float:
    """Phase-to-phase rating of one coil: a split-phase half is half of s1-s2, a phase-to-neutral
    coil on a 3-phase system is x sqrt(3), a phase-to-phase coil is its own voltage."""
    phases = {phase_from, phase_to}
    if phases & {"s1", "s2"}:
        return 2 * winding.kv
    if "N" in phases and system.three_phase:
        return _SQRT3 * winding.kv
    return winding.kv


def phase_end_numbers(ends: list[End]) -> dict[tuple[int, int], tuple[int, str]]:
    """``{(end number, node): (sequenceNumber, phase)}``: one TransformerPhaseEnd per phase of each end's terminal,
    numbered across the transformer, end 1 first, in terminal phase order (neutral last)."""
    numbers, sequence = {}, 0
    for end in ends:
        node_of_phase = {phase: node for node, phase in end.phase_of_node.items()}
        for phase in end.phases:
            sequence += 1
            numbers[(end.number, node_of_phase[phase])] = (sequence, phase)
    return numbers


def end_kind(end: End, phases: int, xf=None, winding_count: int = 0) -> tuple[str, bool]:
    """``(connectionKind, grounded)`` of a PowerTransformerEnd: 1-phase I (split-phase), Y (a coil on node 0) or D;
    3-phase Yn/Y/D, a wye grounded through node 0 or Rneut (``_neutral``)."""
    coil = end.windings[0]
    if phases == 1:
        return ("I" if end.split_phase else ("Y" if 0 in coil.nodes else "D")), 0 in end.phase_of_node
    if not coil.wye:
        return "D", False
    grounded = _neutral(xf, coil, winding_count)[0]
    return ("Yn" if grounded else "Y"), grounded


def _map_single_phase(xf, xf_id: str, windings: list[Winding], ends: list[End],
                      buses: Mapping[str, BusSystem], rows: _Tables, notes: list[str]) -> None:
    base_kva = windings[0].kva
    if any(winding.kva != base_kva for winding in windings):
        raise ValueError(f"Transformer {xf.name}: kVAs={[w.kva for w in windings]}; each coil's %R is on its own "
                         "kVA but the percent base (baseS) is winding 1's, so they must be equal")
    tank = f"{xf_id}_tank"
    no_load_kw = float(xf.pct_noloadloss) / 100 * base_kva if xf.pct_noloadloss is not None else None
    rows.tanks.append(Row([tank, xf_id, cell(xf.pct_imag), cell(no_load_kw)]))

    for end in ends:
        kind, grounded = end_kind(end, 1)
        rows.phase_end_ends.append(Row([f"{xf_id}_{end.number}", xf_id, end.bus, "".join(end.phases),
                                        str(end.number), kind, cell(grounded), buses[end.bus].base_voltage]))
    phase_end_id: dict[tuple[int, int], str] = {}  # (end number, node) -> TransformerPhaseEnd mRID
    for (number, node), (sequence, phase) in phase_end_numbers(ends).items():
        phase_end_id[(number, node)] = f"{xf_id}_{number}_{phase}"
        rows.phase_ends.append(Row([phase_end_id[(number, node)], str(number), str(sequence), phase]))

    end_of_winding = {winding.number: end for end in ends for winding in end.windings}
    for winding in windings:
        end = end_of_winding[winding.number]
        from_node, to_node = winding.nodes
        rated_u = coil_rated_u(winding, end.phase_of_node[from_node], end.phase_of_node[to_node], buses[end.bus])
        rated_s = winding.kva / 2 if end.split_phase else winding.kva
        rows.coils.append(Row([
            f"{xf_id}_wdg_{winding.number}", tank, cell(rated_u), cell(winding.kv), cell(rated_s), cell(base_kva),
            cell(winding.r_percent), phase_end_id[(end.number, from_node)], phase_end_id[(end.number, to_node)],
        ]))
    for i, j in [(1, 2), (1, 3), (2, 3)][: 1 if len(windings) == 2 else 3]:
        rows.coil_mesh.append(Row([f"{xf_id}_mesh_{i}{j}", f"{xf_id}_wdg_{i}", f"{xf_id}_wdg_{j}",
                                   cell(_x_percent(xf, (i, j), notes))]))


def regulator_phase(winding: Winding, phases: int, *, name: str) -> str:
    """An AutoTransformerEnd's PhaseCode: ``AN`` (line to neutral), ``AB`` (line to line), ``ABCN`` (3-phase wye)."""
    if phases == 3:
        if not winding.wye or winding.nodes[:3] != (1, 2, 3):
            raise ValueError(f"Transformer {name}: a 3-phase regulator is mapped as wye on nodes 1.2.3")
        return "ABCN"
    unknown = [node for node in winding.nodes if node not in _NODE_PHASE]
    if unknown or len(set(winding.nodes)) != 2:
        raise ValueError(f"Transformer {name}: regulator winding {winding.number} on nodes {winding.nodes}")
    return "".join(sorted((_NODE_PHASE[node] for node in winding.nodes), key=_PHASE_ORDER.index))


def _map_regulator(xf, xf_id: str, windings: list[Winding], phases: int, buses: Mapping[str, BusSystem],
                   rows: _Tables, notes: list[str], container: str, source: str | None) -> None:
    """A VoltageRegulator with two AutoTransformerEnds and the engine's stand-in mesh (DSS-13)."""
    if len(windings) != 2 or windings[0].bus == windings[1].bus:
        raise ValueError(f"Transformer {xf.name}: a regulator is mapped with 2 windings on 2 buses")
    if windings[0].kva != windings[1].kva:
        raise ValueError(f"Transformer {xf.name}: regulator kVAs {[w.kva for w in windings]} differ")
    if xf.Rneut is not None and float(xf.Rneut) >= 0:
        raise ValueError(f"Transformer {xf.name}: a regulator neutral impedance is not mapped yet")
    unused = [f"{slot}={cell(getattr(xf, slot))}" for slot in ("pct_imag", "pct_noloadloss")
              if getattr(xf, slot) is not None]
    comment = "\n".join(part for part in (
        source, _row_comment(notes),
        f"no home on a VoltageRegulator: {', '.join(unused)}" if unused else None) if part) or None
    rows.regulators.append(Row([xf_id, str(xf.name), container, cell(xf.enabled)], comment=comment))
    for winding in windings:
        phase = regulator_phase(winding, phases, name=xf.name)
        rows.auto_ends.append(Row([f"{xf_id}_{winding.number}", xf_id, winding.bus, phase, str(winding.number),
                                   cell(winding.wye and winding.nodes[-1] == 0 if phases == 1 else winding.wye),
                                   cell(winding.kv), cell(winding.kva), buses[winding.bus].base_voltage]))
    r = windings[0].r_percent + windings[1].r_percent
    rows.auto_mesh.append(Row([f"{xf_id}_mesh_12", f"{xf_id}_1", f"{xf_id}_2", cell(r),
                               cell(_x_percent(xf, (1, 2), notes))]))


def _map_by_template(xf, xf_id: str, windings: list[Winding], ends: list[End], phases: int,
                     buses: Mapping[str, BusSystem], rows: _Tables) -> None:
    """An instance by XfmrCode: a tank on the code's template and one PowerTransformerEnd per bus. A 1-phase
    instance (a lug template) also gets one TransformerPhaseEnd per phase of each terminal, on the end's Terminal,
    numbered as its code's lugs: a center tap's in terminal order (S3b), any other's in each coil's node order, which
    is the coil's direction (S6c T3: a PhaseCode has none, so ``tert.3.1`` would come back ``tert.1.3``)."""
    rows.template_tanks.append(Row([f"{xf_id}_tank", xf_id, mrid("xc_", xf.XfmrCode, lowercase=True)]))
    for end in ends:
        kind, grounded = end_kind(end, phases, xf, len(windings))
        rows.phase_end_ends.append(Row([f"{xf_id}_{end.number}", xf_id, end.bus, "".join(end.phases),
                                        str(end.number), kind, cell(grounded), buses[end.bus].base_voltage]))
    if phases != 1:
        return
    numbers = phase_end_numbers(ends) if is_center_tap(phases, windings, ends) else coil_phase_end_numbers(ends)
    for (number, _), (sequence, phase) in numbers.items():
        rows.template_phase_ends.append(Row([f"{xf_id}_{number}_{phase}", str(number), str(sequence), phase,
                                             f"{xf_id}_T{number}"]))


def coil_phase_end_numbers(ends: list[End]) -> dict[tuple[int, int], tuple[int, str]]:
    """``{(end number, node): (sequenceNumber, phase)}`` of a 1-phase instance whose ends each hold one coil: numbered
    across the transformer, end 1 first, in the coil's node order (From -> To)."""
    numbers, sequence = {}, 0
    for end in ends:
        [coil] = end.windings
        for node in coil.nodes:
            sequence += 1
            numbers[(end.number, node)] = (sequence, end.phase_of_node[node])
    return numbers


def map_transformer(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every inline ``Transformer`` of a DSS model as one ``transformer`` document.

    ``buses`` is the topology walk's result for every bus (lowercased name); ``container`` is the
    EquipmentContainer mRID of every PowerTransformer and tank.
    """
    transformers = native.list_by_class(NATIVE_CLASS)
    codes = {str(code.name).lower(): code for code in native.list_by_class(schema.Xfmrcode)}
    regulated = regulated_transformers(native)
    rows = _Tables()
    for xf in transformers:
        is_regulated = str(xf.name).lower() in regulated
        source = None
        by_template = bool(xf.XfmrCode) and not is_regulated
        if xf.XfmrCode:
            xf, source = with_code(xf, codes)
            if by_template:
                source = f"by XfmrCode {xf.XfmrCode} (xfmrcode.cimtbl)"
        phases = xf.phases if xf.phases is not None else 3
        if phases not in (1, 3):
            raise ValueError(f"Transformer {xf.name}: phases={phases}; only 1 and 3 are mapped")
        notes = [] if xf.phases is not None else ["phases=3"]
        windings = windings_of(xf, phases, notes, regulated=is_regulated)
        xf_id = mrid(PREFIX, xf.name, lowercase=True)
        missing = [winding.bus for winding in windings if winding.bus not in buses]
        if missing:
            raise ValueError(f"Transformer {xf.name}: no bus voltage for {missing}")
        if is_regulated and is_regulator(windings):
            _map_regulator(xf, xf_id, windings, phases, buses, rows, notes, container, source)
            continue
        ends = ends_of(windings, phases, name=xf.name)
        first_row = len(rows.transformers)
        rows.transformers.append(Row([xf_id, str(xf.name), container, cell(xf.enabled)]))
        if by_template:
            _map_by_template(xf, xf_id, windings, ends, phases, buses, rows)
            notes = []  # the template's defaults are listed on the template
        elif phases == 3:
            _map_three_phase(xf, xf_id, windings, ends, buses, rows, notes)
        else:
            _map_single_phase(xf, xf_id, windings, ends, buses, rows, notes)
        comment = "\n".join(part for part in (source, _row_comment(notes)) if part) or None
        rows.transformers[first_row] = rows.transformers[first_row]._replace(comment=comment)
    return Document(name="transformer", statements=_statements(rows), profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(transformers)) if transformers else None)


def _statements(rows: _Tables) -> list[Table]:
    """The tables in reference order; empty ones are left out."""
    layout = [
        ("PowerTransformer", ["mRID", "name", "EquipmentContainer", "normallyInService"], rows.transformers,
         untranscribed_names(FIELDS)),
        ("PowerTransformerEnd", ["mRID", "PowerTransformer", "node", "phases", "endNumber", "connectionKind",
                                 "grounded", ("rground", "ohm"), ("xground", "ohm"), ("ratedU", "kV"),
                                 ("ratedS", "kVA"), ("r", "percent"), ("b", "percent"), ("g", "percent"),
                                 "BaseVoltage"], rows.balanced_ends, "3-phase: by balanced ends"),
        ("TransformerMeshImpedance", ["mRID", "FromTransformerEnd", "ToTransformerEnd", ("x", "percent")],
         rows.balanced_mesh, "x in percent on winding 1's kVA at the From end's voltage"),
        ("PowerTransformerEnd", ["mRID", "PowerTransformer", "node", "phases", "endNumber", "connectionKind",
                                 "grounded", "BaseVoltage"], rows.phase_end_ends,
         "1-phase by phase ends, and every instance by template (end n is the template's end n)"),
        ("TransformerTank", ["mRID", "PowerTransformer", "TankConfiguration"], rows.template_tanks,
         "by template: the XfmrCode's TransformerTankConfiguration (xfmrcode.cimtbl)"),
        ("TransformerPhaseEnd", ["mRID", "endNumber", "sequenceNumber", "phase", "Terminal"],
         rows.template_phase_ends,
         "1-phase by template: one per phase of each terminal; a template lug's sequenceNumber names the one it "
         "lands on, and by tank ends their order is the coil's"),
        ("TransformerTank", ["mRID", "PowerTransformer", ("percentMagnetizingCurrent", "percent"),
                             ("noLoadLoss", "kW")], rows.tanks,
         "derived: noLoadLoss = pct_noloadloss / 100 x winding 1 kVA"),
        ("TransformerPhaseEnd", ["mRID", "endNumber", "sequenceNumber", "phase"], rows.phase_ends,
         "sequenceNumber is unique in the transformer, end 1 first, in terminal phase order"),
        ("TransformerWinding", ["mRID", "TransformerTank", ("ratedU", "kV"), ("baseU", "kV"), ("ratedS", "kVA"),
                                ("baseS", "kVA"), ("r", "percent"), "FromTransformerEnd", "ToTransformerEnd"],
         rows.coils, "baseU = DSS kV (the coil); derived: ratedU phase-to-phase (x sqrt 3 for a phase-to-neutral "
                     "coil on a 3-phase system, x 2 for a split-phase half), ratedS of a half = kVA / 2"),
        ("TransformerMeshImpedance", ["mRID", "FromWinding", "ToWinding", ("x", "percent")], rows.coil_mesh,
         "x in percent on winding 1's kVA (every coil's baseS) at the From winding's baseU"),
        ("VoltageRegulator", ["mRID", "name", "EquipmentContainer", "normallyInService"], rows.regulators,
         "regulators (DSS-13): a Transformer a RegControl names, with equal winding kV"),
        ("AutoTransformerEnd", ["mRID", "AutoTransformer", "node", "phase", "endNumber", "grounded", ("baseU", "kV"),
                                ("ratedS", "kVA"), "BaseVoltage"], rows.auto_ends,
         "the nameplate: baseU = the coil kV, ratedS = the kVA; phase is a PhaseCode on the end's Terminal"),
        ("TransformerMeshImpedance", ["mRID", "FromTransformerEnd", "ToTransformerEnd", ("r", "percent"),
                                      ("x", "percent")], rows.auto_mesh,
         "the engine's stand-in impedance (a regulator nameplate has no %Z): r = %R1 + %R2, x = XHL, in percent "
         "on end 1's baseU and ratedS"),
    ]
    statements = []
    for class_name, columns, table_rows, comment in layout:
        if table_rows:
            statements.append(Table(class_name, [Column(*c) if isinstance(c, tuple) else Column(c) for c in columns],
                                    table_rows, comment=comment))
    return statements

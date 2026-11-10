"""OpenDSS ``XfmrCode`` -> ``xfmrcode.cimtbl``: one ``TransformerTankConfiguration`` template per code.

Two template forms (the user's model, 2026-11-08):

- A center-tap code (1-phase, 3 windings, its instances' windings 2 and 3 a split-phase secondary) is a
  3-winding tank with ``TransformerLug``s H1, H2, X1, X3, X2 (sequenceNumber in terminal order) and windings
  lug to lug, from the polarity end: H1->H2, X1->X2 (s1->N), X2->X3 (N->s2). The instance has one
  ``TransformerPhaseEnd`` per phase of each end's terminal (not per lug); each lug's sequenceNumber names the
  phase end it lands on.
- Any other code is a ``TransformerTankEnd`` per winding (connection, grounding impedance) with one
  ``TransformerWinding`` each; the instance's ``PowerTransformerEnd`` n is template end n.

A code's ``ratedU`` is the nameplate, phase to phase, which the coil voltage alone does not fix (7.2 kV is
7200/12470Y on a 3-phase system), so the template is built from each instance that uses it: every instance must
give the same template, else it raises. A code no unregulated instance uses is not written (a regulator takes its
code's values, S3a).

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#xfmrcode``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_values
from cimhub_opendss.importer.cimtbl import transformer as transformer_mapper
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Xfmrcode
PREFIX = "xc_"

_CONFIGURATION = "TransformerTankConfiguration"
_SCALAR = "the active-winding form; the reader folds wdg= blocks and bare values into the arrays"
_THERMAL = "thermal model; no home in the network profile parts"
_RATING = "a tank rating; instance OperationalLimitSet or untranscribed (plan D9)"
_TAP_CHANGER = "tap changer range; a regulated instance takes it (S3a); else untranscribed"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"

FIELDS = {
    "name": Field("copied", ((_CONFIGURATION, "name", None),), "mRID = xc_ + name, lowercased"),
    "phases": Field("structural", note="3: TankEnd template; 1 with 3 windings whose instances are center taps: lug "
                                       "template; other 1-phase codes: TankEnd template"),
    "windings": Field("structural", note="one TransformerWinding each; 2 or 3"),
    "wdg": Field("structural", note="the winding Rneut/Xneut belong to (the reader's tag); none = the last"),
    "conn": Field("structural", note=_SCALAR),
    "kV": Field("structural", note=_SCALAR),
    "kVA": Field("structural", note=_SCALAR),
    "tap": Field("structural", note=_SCALAR),
    "pct_R": Field("structural", note=_SCALAR),
    "Rneut": Field("structural", note="TankEnd rground (ohm) of its winding when >= 0; on a lug template raises"),
    "Xneut": Field("structural", note="TankEnd xground (ohm) of its winding, with Rneut >= 0"),
    "conns": Field("structural", note="TankEnd connectionKind (D, Y; grounding is the instance's); a center tap's "
                                      "secondary halves are I; default wye"),
    "kVs": Field("structural", note="winding baseU (the coil); ratedU phase-to-phase from the instances' common "
                                    "bus system (x sqrt 3 on a 3-phase system, x 2 for a split-phase half), and "
                                    "instances that disagree raise"),
    "kVAs": Field("structural", note="winding ratedS (a split-phase half: kVA / 2); baseS = winding 1's kVA on "
                                     "every coil (per phase on a 3-phase code)"),
    "taps": Field("structural", note="a tap other than 1 raises (a fixed tap is not mapped yet)"),
    "Xhl": Field("structural", note="mesh 1-2 x (percent on the From winding's baseU and baseS); default 7"),
    "Xht": Field("structural", note="mesh 1-3 x; default 35"),
    "Xlt": Field("structural", note="mesh 2-3 x; default 30"),
    "X12": Field("structural", note="alias of Xhl"),
    "X13": Field("structural", note="alias of Xht"),
    "X23": Field("structural", note="alias of Xlt"),
    "Xscarray": Field("untranscribed", note="for more than 3 windings, which raise"),
    "pct_Rs": Field("structural", note="winding r (percent on its own baseS); default 0.2"),
    "pct_loadloss": Field("derived", note="when pct_Rs is unset, r = loadloss / 2 on windings 1 and 2; set with "
                                          "pct_Rs, the two must agree"),
    "pct_noloadloss": Field("derived", note="TransformerTankConfiguration.noLoadLoss (kW) = % x winding 1 kVA"),
    "pct_imag": Field("copied", ((_CONFIGURATION, "percentMagnetizingCurrent", "percent"),)),
    "ppm_antifloat": Field("untranscribed", note="numerical aid of the DSS solver"),
    "thermal": Field("untranscribed", note=_THERMAL),
    "n": Field("untranscribed", note=_THERMAL),
    "m": Field("untranscribed", note=_THERMAL),
    "flrise": Field("untranscribed", note=_THERMAL),
    "hsrise": Field("untranscribed", note=_THERMAL),
    "normhkVA": Field("untranscribed", note=_RATING),
    "emerghkVA": Field("untranscribed", note=_RATING),
    "MaxTap": Field("untranscribed", note=_TAP_CHANGER),
    "MinTap": Field("untranscribed", note=_TAP_CHANGER),
    "NumTaps": Field("untranscribed", note=_TAP_CHANGER),
    "RdcOhms": Field("structural", note=_NOT_MAPPED + " (home TransformerWinding.rDC)"),
    "Seasons": Field("structural", note=_NOT_MAPPED),
    "Ratings": Field("structural", note=_NOT_MAPPED),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}


#: The lugs of a center-tap tank, IEEE C57.12.70: (designation, winding, its from (0) or to (1) conductor).
_CENTER_TAP_LUGS = (("H1", 1, 0), ("H2", 1, 1), ("X1", 2, 0), ("X2", 2, 1), ("X3", 3, 1))
#: Windings lug to lug, from the polarity end: H1->H2, X1->X2 (s1->N), X2->X3 (N->s2).
_CENTER_TAP_WINDINGS = {1: ("h1", "h2"), 2: ("x1", "x2"), 3: ("x2", "x3")}
#: The center-tap secondary the lugs assume: winding 2 on bus2.1.0, winding 3 on bus2.0.2.
_CENTER_TAP_NODES = {2: (1, 0), 3: (0, 2)}

_PROVENANCE = """OpenDSS XfmrCode -> TransformerTankConfiguration (catalog). A center-tap code is a tank with lugs and
windings lug to lug; any other a TransformerTankEnd per winding. Built from the instances that use it.
Source table: XfmrCode (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#xfmrcode"""


class Template(NamedTuple):
    """The rows one instance's view of its code gives (cells as text, so two views compare exactly)."""
    lugs: bool
    configuration: tuple
    ends: tuple       # TankEnd: (endNumber, connectionKind, rground, xground); lug: (designation, sequenceNumber)
    windings: tuple   # (number, ratedU, baseU, ratedS, baseS, r, from, to)
    mesh: tuple       # (i, j, x)
    notes: tuple


def _neutral_impedance(xf, winding, count: int) -> tuple[str | None, str | None]:
    """rground, xground (ohm) of the winding Rneut/Xneut belong to (``wdg``, else the last), when Rneut >= 0."""
    if xf.Rneut is None or float(xf.Rneut) < 0:
        return None, None
    neutral_winding = int(xf.wdg) if xf.wdg is not None else count
    if winding.number != neutral_winding:
        return None, None
    return cell(float(xf.Rneut)), cell(float(xf.Xneut or 0.0))


def instance_template(xf, buses: Mapping[str, BusSystem]) -> Template:
    """The template of ``xf`` (an instance with its code's values, ``with_code``) on its buses."""
    notes: list[str] = [] if xf.phases is not None else ["phases=3"]
    phases = xf.phases if xf.phases is not None else 3
    windings = transformer_mapper.windings_of(xf, phases, notes)
    ends = transformer_mapper.ends_of(windings, phases, name=xf.name)
    lugs = transformer_mapper.is_center_tap(phases, windings, ends)
    base_kva = windings[0].kva
    pairs = [(1, 2), (1, 3), (2, 3)][: 1 if len(windings) == 2 else 3]
    for i, _ in pairs:
        if windings[i - 1].kva != base_kva:
            raise ValueError(f"Transformer {xf.name}: kVAs={[w.kva for w in windings]}; DSS gives every x on winding "
                             f"1's kVA, so a mesh's From winding ({i}) must carry it")
    if lugs and any(winding.kva != base_kva for winding in windings):
        raise ValueError(f"Transformer {xf.name}: kVAs={[w.kva for w in windings]}; a center tap's coils share "
                         "winding 1's kVA as their percent base (baseS)")
    no_load_kw = float(xf.pct_noloadloss) / 100 * base_kva if xf.pct_noloadloss is not None else None
    configuration = (cell(xf.pct_imag), cell(no_load_kw))
    end_of = {winding.number: end for end in ends for winding in end.windings}
    rows, template_ends = [], []
    if lugs:
        if xf.Rneut is not None and float(xf.Rneut) >= 0:
            raise ValueError(f"Transformer {xf.name}: a neutral impedance on a center-tap code is not mapped yet")
        for winding in windings[1:]:
            if winding.nodes != _CENTER_TAP_NODES[winding.number]:
                raise ValueError(f"Transformer {xf.name}: winding {winding.number} on nodes {winding.nodes}; a "
                                 "center-tap code's lugs are mapped for bus2.1.0 + bus2.0.2")
        numbers = transformer_mapper.phase_end_numbers(ends)
        for designation, number, side in _CENTER_TAP_LUGS:
            winding = windings[number - 1]
            template_ends.append((designation, str(numbers[(end_of[number].number, winding.nodes[side])][0])))
    for winding in windings:
        end = end_of[winding.number]
        if phases == 3:
            rated_u, base_u = winding.kv, winding.kv / math.sqrt(3) if winding.wye else winding.kv
            rated_s, base_s = winding.kva, winding.kva / 3
        else:
            from_node, to_node = winding.nodes
            rated_u = transformer_mapper.coil_rated_u(winding, end.phase_of_node[from_node],
                                                      end.phase_of_node[to_node], buses[end.bus])
            base_u, base_s = winding.kv, base_kva if lugs else winding.kva
            rated_s = winding.kva / 2 if end.split_phase else winding.kva
        if lugs:
            from_end, to_end = _CENTER_TAP_WINDINGS[winding.number]
        else:
            from_end, to_end = str(winding.number), None
            template_ends.append((str(winding.number), "Y" if winding.wye else "D",
                                  *_neutral_impedance(xf, winding, len(windings))))
        rows.append((str(winding.number), cell(rated_u), cell(base_u), cell(rated_s), cell(base_s),
                     cell(winding.r_percent), from_end, to_end))
    mesh = tuple((str(i), str(j), cell(transformer_mapper._x_percent(xf, (i, j), notes))) for i, j in pairs)
    return Template(lugs, configuration, tuple(template_ends), tuple(rows), mesh, tuple(notes))


class _Tables:
    def __init__(self):
        self.configurations: list[Row] = []
        self.tank_ends: list[Row] = []
        self.lugs: list[Row] = []
        self.end_windings: list[Row] = []
        self.lug_windings: list[Row] = []
        self.mesh: list[Row] = []


def _template_rows(code, template: Template, users: list[str], rows: _Tables) -> None:
    xc = mrid(PREFIX, code.name, lowercase=True)
    notes = [f"defaulted: {', '.join(template.notes)}" if template.notes else None,
             untranscribed_values(FIELDS, code),
             f"built from {len(users)} instance" + ("s" if len(users) > 1 else "") + f" ({users[0]}, ...)"]
    rows.configurations.append(Row([xc, str(code.name), *template.configuration],
                                   comment="\n".join(note for note in notes if note)))
    if template.lugs:
        rows.lugs += [Row([f"{xc}_lug_{designation.lower()}", xc, designation, sequence])
                      for designation, sequence in template.ends]
    else:
        rows.tank_ends += [Row([f"{xc}_end_{number}", xc, number, kind, rground, xground])
                           for number, kind, rground, xground in template.ends]
    for number, rated_u, base_u, rated_s, base_s, r, from_end, to_end in template.windings:
        cells = [f"{xc}_wdg_{number}", xc, rated_u, base_u, rated_s, base_s, r]
        if template.lugs:
            rows.lug_windings.append(Row(cells + [f"{xc}_lug_{from_end}", f"{xc}_lug_{to_end}"]))
        else:
            rows.end_windings.append(Row(cells + [f"{xc}_end_{from_end}"]))
    rows.mesh += [Row([f"{xc}_mesh_{i}{j}", f"{xc}_wdg_{i}", f"{xc}_wdg_{j}", x]) for i, j, x in template.mesh]


def map_xfmrcode(native, buses: Mapping[str, BusSystem]) -> Document:
    """Every ``XfmrCode`` an unregulated Transformer uses, as one ``xfmrcode`` document of templates."""
    codes = native.list_by_class(NATIVE_CLASS)
    if not codes:
        return Document(name="xfmrcode", statements=[], profile=CIM_PROFILE)
    by_name = {str(code.name).lower(): code for code in codes}
    regulated = transformer_mapper.regulated_transformers(native)
    views: dict[str, list[tuple[str, Template]]] = {}
    for xf in native.list_by_class(schema.Transformer):
        if not xf.XfmrCode or str(xf.name).lower() in regulated:
            continue
        merged, _ = transformer_mapper.with_code(xf, by_name)
        views.setdefault(str(xf.XfmrCode).lower(), []).append((str(xf.name), instance_template(merged, buses)))
    rows, unused = _Tables(), []
    for code in codes:
        code_views = views.get(str(code.name).lower())
        if not code_views:
            unused.append(str(code.name))
            continue
        first_name, template = code_views[0]
        for name, other in code_views[1:]:
            if other != template:
                field = next(f for f in Template._fields if getattr(other, f) != getattr(template, f))
                raise ValueError(f"XfmrCode {code.name}: Transformers {first_name} and {name} give it different "
                                 f"templates ({field}: {getattr(template, field)} vs {getattr(other, field)}), "
                                 "e.g. on different bus systems")
        _template_rows(code, template, [name for name, _ in code_views], rows)
    comment = _PROVENANCE.format(count=len(codes))
    if unused:
        comment += ("\nnot written (no unregulated Transformer uses them; a regulator takes its code's values): "
                    + ", ".join(unused))
    return Document(name="xfmrcode", statements=_statements(rows), profile=CIM_PROFILE, comment=comment)


def _statements(rows: _Tables) -> list[Table]:
    winding = ["mRID", "TankConfiguration", ("ratedU", "kV"), ("baseU", "kV"), ("ratedS", "kVA"), ("baseS", "kVA"),
               ("r", "percent")]
    layout = [
        ("TransformerTankConfiguration", ["mRID", "name", ("percentMagnetizingCurrent", "percent"),
                                          ("noLoadLoss", "kW")], rows.configurations,
         "derived: noLoadLoss = pct_noloadloss / 100 x winding 1 kVA"),
        ("TransformerTankEnd", ["mRID", "TankConfiguration", "endNumber", "connectionKind", ("rground", "ohm"),
                                ("xground", "ohm")], rows.tank_ends,
         "a TankEnd per winding; no phases (the instance's PowerTransformerEnd n carries them)"),
        ("TransformerLug", ["mRID", "TankConfiguration", "designation", "sequenceNumber"], rows.lugs,
         "IEEE C57.12.70 designations; sequenceNumber = the instance phase end the lug lands on"),
        ("TransformerWinding", winding + ["FromTransformerEnd"], rows.end_windings,
         "baseU = the coil kV; ratedU phase-to-phase (derived from the instances' bus system); baseS = the "
         "winding's kVA (r is on it), per phase on a 3-phase code"),
        ("TransformerWinding", winding + ["FromTransformerLug", "ToTransformerLug"], rows.lug_windings,
         "from the polarity end: H1->H2, X1->X2 (s1->N), X2->X3 (N->s2); a half's ratedS = kVA / 2"),
        ("TransformerMeshImpedance", ["mRID", "FromWinding", "ToWinding", ("x", "percent")], rows.mesh,
         "x in percent on the From winding's baseU and baseS"),
    ]
    return [Table(name, [Column(*c) if isinstance(c, tuple) else Column(c) for c in columns], table_rows,
                  comment=comment) for name, columns, table_rows, comment in layout if table_rows]

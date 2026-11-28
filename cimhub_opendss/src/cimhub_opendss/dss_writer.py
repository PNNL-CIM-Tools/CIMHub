"""OpenDSS writer: a ``DssModel`` (the shape ``DssReader.read_all()`` returns) as one deck.

``serialize`` gives one ``new`` command; ``write`` gives the whole deck the engine compiles and the reader reads
back (``DSS_REWRITE_PLAN.md`` section 8.2).
"""
from __future__ import annotations

import math
import re
from dataclasses import fields, is_dataclass
from enum import IntEnum
from pathlib import Path

from cimhub_core import GraphModel
from cimhub_core.base import FormatWriter
from cimhub_core.serialization import get_schema_annotations
from cimhub_opendss.schema import opendss_schema as schema


# Regex to extract trailing integer from a meaning URI like
# "https://gridappsd.github.io/dss-graph/LoadModel.4"
_MEANING_INT_RE = re.compile(r'\.(\d+)$')

# Characters OpenDSS cannot carry inside an object name or a reference to one.
# A space ends the token, so "Cable_2P_1C_2GA_CU BSD" is parsed as a name plus a
# stray property and raises "Invalid inline math entry"; the bracket, quote, and
# brace characters are array/expression delimiters; "!" and "//" start a comment, so
# the engine reads "New Load.a!b bus1=x" as "New Load.a".  Names converted from other
# formats do contain these (a cable catalog entry such as "3P_1C_500KCM_CU-<NULL>"),
# so sanitizing is not optional.
#
# Applied in the writer rather than in the ~20 converter modules because a name
# is written in three places (the "new Class.NAME" prefix, a nested-dataclass
# reference, and strings the converters build such as bus1= and
# SwitchedObj=f"Line.{name}").  One rule here keeps a definition and every
# reference to it spelled the same way; sanitizing per-converter would not.
_DSS_UNSAFE_RE = re.compile(r'[\s"\'<>\[\]{}(),=~|!]+|//')


#: significant digits of a written float: enough for every deck value, and it clips the binary tails a unit
#: conversion leaves (0.0018000000000000002 -> 0.0018), which are 1e-16 relative
FLOAT_DIGITS = 15


def format_float(value: float) -> str:
    """``value`` to ``FLOAT_DIGITS`` significant digits, the shortest form (``60``, ``0.0018``, ``1e-05``). NaN
    and infinity raise: the engine has no such value."""
    if not math.isfinite(value):
        raise ValueError(f"DssWriter: {value!r} is not a finite number")
    return f"{value:.{FLOAT_DIGITS}g}"


def dss_safe_name(name: str) -> str:
    """Return *name* with characters OpenDSS cannot parse replaced by "_".

    Idempotent, and collision-free for the names seen in practice because the
    replacement is one-for-one on each run of unsafe characters rather than a
    truncation.  Names differing only in an unsafe character would collide; that
    is a data defect, so ``DssWriter.write`` raises on it (``check_safe_names``)
    rather than renaming around it.
    """
    return _DSS_UNSAFE_RE.sub('_', name)


def check_safe_names(records) -> None:
    """Raise when two records of one class are one DSS name once sanitized, compared lowercased as DSS compares
    names: DSS would apply the second as an edit of the first."""
    seen: dict[str, str] = {}
    for record in records:
        name = str(record.name)
        safe = dss_safe_name(name)
        if safe.lower() in seen:
            raise ValueError(f"DssWriter: {type(record).__name__} {seen[safe.lower()]!r} and {name!r} are both named "
                             f"{safe!r} in DSS")
        seen[safe.lower()] = name


#: The deck's classes in definition order: each after everything it references (catalogs before their users, a
#: Line before the Fuse/Recloser/SwtControl that switches it, a Transformer before its RegControl, a Capacitor
#: before its CapControl). A class in the model and not here raises.
WRITE_ORDER = (
    schema.Loadshape, schema.Wiredata, schema.Cndata, schema.Tsdata, schema.Linespacing, schema.Linegeometry, schema.Linecode,
    schema.Xfmrcode, schema.Vsource, schema.Line, schema.Relay, schema.Fuse, schema.Recloser, schema.Swtcontrol,
    schema.Transformer, schema.Regcontrol, schema.Load, schema.Capacitor, schema.Capcontrol, schema.Pvsystem,
    schema.Storage, schema.Generator, schema.Reactor,
)

#: Records that are not ``New`` commands; ``write`` places them (``Options`` as ``Set``/``Open``, ``Buscoords`` as a
#: coordinates file).
_DECK_RECORDS = (schema.Options, schema.Buscoords)

#: ``New Circuit.<name>`` is DSS's ``Vsource.source`` (the reader's rule).
CIRCUIT_SOURCE = "source"

#: Slots written before all others, in this order. Each sets other properties when assigned: a template
#: (XfmrCode, LineCode, geometry, spacing) copies its values, and an XfmrCode re-sizes the windings (resetting their
#: buses); ``Switch=y`` sets r1=1, x1=1, ... So they go first and the record's own values after them. ``phases``
#: sizes the arrays that follow, and goes before ``Switch`` as decks write it: the engine's later recalculation of
#: a switch line depends on that order (IEEE13_CDPSM ``Sect1``, engine-checked).
#: Per-winding slots DSS has no array form for: written last, one ``wdg=n <slot>=value`` block per winding, so no
#: other per-winding slot follows a ``wdg=`` they move.
_PER_WINDING_SLOTS = ("RdcOhms",)
_LEADING_SLOTS = ("XfmrCode", "linecode", "geometry", "spacing", "phases", "Switch")

#: A LineGeometry's active-conductor slots: the reader leaves the last cond= block in them and folds every block
#: into the arrays, so the writer writes blocks from the arrays (``DssWriter._geometry``).
_GEOMETRY_CURSOR = ("cond", "wire", "cncable", "tscable", "x", "h")
_NAME_ARRAYS = ("wires", "cncables", "tscables")
_CATALOG_KINDS = ((schema.Wiredata, "wire"), (schema.Cndata, "cncable"), (schema.Tsdata, "tscable"))


def _has_positions(obj) -> bool:
    return isinstance(obj, schema.Linegeometry) and bool(obj.xs or obj.hs)


def _conductor_kinds(model: GraphModel) -> dict[str, str]:
    """``{lowered catalog name: cond= keyword}`` over the three wire catalogs; a name in two raises."""
    kinds: dict[str, str] = {}
    for catalog, kind in _CATALOG_KINDS:
        for record in model.list_by_class(catalog):
            name = str(record.name).lower()
            if name in kinds:
                raise ValueError(f"DssWriter: conductor {record.name!r} is in two wire catalogs")
            kinds[name] = kind
    return kinds


class DssWriter(FormatWriter):
    """Serialize a ``DssModel`` to one deck the engine compiles and ``DssReader`` reads back.

    Produces strings like::

        new Load.myload bus1=bus123.1.2.3 kV=12.47 kW=100.0

    Field ordering and DSS property names are driven entirely by the YAML
    schema annotations (``order`` and ``dss_name``).  No hardcoded name maps.
    """

    # ------------------------------------------------------------------
    # FormatWriter interface
    # ------------------------------------------------------------------

    def write(self, model: GraphModel, destination: str, *, per_class: bool = False) -> None:
        """Write *model* to the deck *destination* (a ``.dss`` path), in this order: ``Clear``; ``Set
        defaultbasefreq``; ``New Circuit``; ``Set earthmodel``; the records in ``WRITE_ORDER``; ``Set voltagebases`` and
        ``CalcVoltageBases``; one ``Open`` per open terminal; ``Buscoords``/``LatLongCoords`` naming the coordinates
        files written beside the deck (``<stem>_buscoords.csv``, ``<stem>_latlongcoords.csv``).

        ``per_class`` writes each class's records to its own file beside the deck (``linecode.dss``, ``line.dss``,
        ...), which *destination* (the master) ``Redirect``s in ``WRITE_ORDER``.

        Every file is formatted before any is written, so a record that fails leaves nothing behind."""
        destination = Path(destination)
        options = self._options(model)
        unknown = [cls.__name__ for cls in model.graph if cls not in WRITE_ORDER and cls not in _DECK_RECORDS]
        if unknown:
            raise ValueError(f"DssWriter: no write order for {sorted(unknown)}")
        lines = ["Clear"]
        if getattr(options, "defaultbasefreq", None) is not None:
            lines.append(self._set(options, "defaultbasefreq"))  # before the circuit, which takes it
        lines += self._circuit(model, options)
        if getattr(options, "earthmodel", None) is not None:
            lines.append(self._set(options, "earthmodel"))  # the engine needs a circuit first
        kinds = _conductor_kinds(model)
        files: dict[Path, str] = {}  # every file but the master, formatted
        for cls in WRITE_ORDER:
            check_safe_names(model.list_by_class(cls))
            commands = [self._geometry(obj, kinds) if _has_positions(obj) else self.serialize(obj)
                        for obj in model.list_by_class(cls)
                        if not (cls is schema.Vsource and str(obj.name).lower() == CIRCUIT_SOURCE)]
            if not commands:
                continue
            if not per_class:
                lines += commands
                continue
            class_file = destination.with_name(f"{cls.__name__.lower()}.dss")
            if class_file.name == destination.name.lower():
                raise ValueError(f"DssWriter: the master {destination.name} would be overwritten by the "
                                 f"{cls.__name__} file; name it otherwise")
            files[class_file] = "\n".join(commands) + "\n"
            lines.append(f"Redirect {class_file.name}")
        if options is not None and options.voltagebases:
            lines += [self._set(options, "voltagebases"), "CalcVoltageBases"]
        for terminal in (options.open_terminals if options is not None else None) or []:
            target, number = str(terminal).rsplit(" ", 1)  # "Class.name terminal", the reader's form
            lines.append(f"Open {dss_safe_name(target)} {number}")
        coordinates, commands = self._coordinates(model, destination)
        files.update(coordinates)
        lines += commands
        destination.parent.mkdir(parents=True, exist_ok=True)
        for path, text in files.items():
            path.write_text(text, encoding="utf-8")
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def serialize(self, obj) -> str:
        """Serialize a single LinkML dataclass to a DSS ``new`` command."""
        if isinstance(obj, _DECK_RECORDS):
            raise ValueError(f"DssWriter: {type(obj).__name__} is not a New command; write() places it")
        if _has_positions(obj):
            raise ValueError(f"DssWriter: LineGeometry {obj.name} has positions; its cond= blocks need the "
                             "model's wire catalogs, so write() places it")
        return " ".join([f"new {obj.__class__.__name__}.{dss_safe_name(str(obj.name))}", *self._properties(obj)])

    def _properties(self, obj, skip: tuple[str, ...] = ()) -> list[str]:
        """``dss_name=value`` for each set slot, ``_LEADING_SLOTS`` first, then the schema's ``order``, except ``skip``.
        ``like`` is never written: the reader has copied its values into the slots already, and ``like=`` written
        after them would copy the other object over them."""
        schema_annots = get_schema_annotations(type(obj))
        ordered = sorted(
            (f for f in fields(obj) if f.name not in ('name', 'like', *skip)),
            key=lambda f: _LEADING_SLOTS.index(f.name) - len(_LEADING_SLOTS) if f.name in _LEADING_SLOTS
            else schema_annots.get(f.name, {}).get('order', 9999),
        )
        parts, per_winding = [], []
        for f in ordered:
            value = getattr(obj, f.name)
            if value is None:
                continue
            field_annots = schema_annots.get(f.name, {})
            if f.name in _PER_WINDING_SLOTS and value:
                per_winding += [f"wdg={number} {f.name}={format_float(float(item))}"
                                for number, item in enumerate(value, start=1)]
                continue
            formatted = self._format_value(value, field_annots)
            if formatted is not None:
                parts.append(f"{field_annots.get('dss_name', f.name)}={formatted}")
        return parts + per_winding

    def _geometry(self, geometry, kinds: dict[str, str]) -> str:
        """A LineGeometry with positions: its other slots, then one ``cond=`` block per conductor naming its kind
        (``wire``, ``cncable``, ``tscable``: the catalog that defines the name), as only blocks can mix kinds. With
        heights and no ``xs``, each conductor is at x=0, the engine's default (LineGeometry.pas:1075)."""
        arrays = [getattr(geometry, slot) for slot in _NAME_ARRAYS if getattr(geometry, slot)]
        xs = geometry.xs or [0.0] * len(geometry.hs or [])
        if len(arrays) != 1 or not len(arrays[0]) == len(xs) == len(geometry.hs):
            counts = ", ".join(f"{len(getattr(geometry, slot) or [])} {slot}" for slot in (*_NAME_ARRAYS, "xs", "hs")
                               if getattr(geometry, slot) or slot in ("xs", "hs"))
            raise ValueError(f"DssWriter: LineGeometry {geometry.name}: {counts}; needs one wire, x and h per "
                             f"conductor, all in one of {list(_NAME_ARRAYS)}")
        parts = [f"new {type(geometry).__name__}.{dss_safe_name(str(geometry.name))}",
                 *self._properties(geometry, skip=(*_GEOMETRY_CURSOR, *_NAME_ARRAYS, "xs", "hs", "units"))]
        for number, (name, x, h) in enumerate(zip(arrays[0], xs, geometry.hs), start=1):
            kind = kinds.get(str(name).lower())
            if kind is None:
                raise ValueError(f"DssWriter: LineGeometry {geometry.name}: conductor {name!r} is in no wire catalog")
            block = f"cond={number} {kind}={dss_safe_name(str(name))} x={format_float(x)} h={format_float(h)}"
            parts.append(block + (f" units={geometry.units}" if geometry.units else ""))
        return " ".join(parts)

    @staticmethod
    def _options(model: GraphModel):
        """The model's one ``Options`` record, or None."""
        records = model.list_by_class(schema.Options)
        if len(records) > 1:
            raise ValueError(f"DssWriter: {len(records)} Options records; a deck has one")
        return records[0] if records else None

    def _set(self, options, slot: str) -> str:
        return f"Set {slot}={self._format_value(getattr(options, slot))}"

    def _circuit(self, model: GraphModel, options) -> list[str]:
        """``New Circuit.<Options.circuit>`` with the slots of ``Vsource.source``, or nothing for a fragment (a
        catalog deck the reader also reads without a circuit); one without the other raises."""
        sources = [obj for obj in model.list_by_class(schema.Vsource) if str(obj.name).lower() == CIRCUIT_SOURCE]
        circuit = options.circuit if options is not None else None
        if not sources and circuit is None:
            return []
        if not sources or circuit is None:
            raise ValueError("DssWriter: Options.circuit and Vsource.source (New Circuit) come together; "
                             f"the model has {'only Options.circuit' if circuit is not None else 'only Vsource.source'}")
        return [" ".join([f"New Circuit.{dss_safe_name(str(circuit))}", *self._properties(sources[0])])]

    @staticmethod
    def _coordinates(model: GraphModel, destination: Path) -> tuple[dict[Path, str], list[str]]:
        """The ``Buscoords`` rows as files beside the deck, one per kind (``{path: text}``), and the commands that
        read them. A bus is named as the deck names it (sanitized), and a file name the engine would split (``my
        deck_buscoords.csv``) is quoted."""
        files, commands = {}, []
        for geographic, command, suffix in ((False, "Buscoords", "buscoords"), (True, "LatLongCoords", "latlongcoords")):
            rows = [row for row in model.list_by_class(schema.Buscoords) if bool(row.geographic) == geographic]
            if not rows:
                continue
            text = ""
            for row in rows:
                if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (row.x, row.y)):
                    raise ValueError(f"DssWriter: Buscoords {row.name!r}: coordinates ({row.x!r}, {row.y!r}) are not "
                                     "two finite numbers")
                # LatLongCoords files are lat, long: y first (the reader swaps them back)
                first, second = (row.y, row.x) if geographic else (row.x, row.y)
                text += f"{dss_safe_name(str(row.name))}, {first!r}, {second!r}\n"
            path = destination.with_name(f"{destination.stem}_{suffix}.csv")
            files[path] = text
            commands.append(f'{command} "{path.name}"' if _DSS_UNSAFE_RE.search(path.name) else f"{command} {path.name}")
        return files, commands

    # ------------------------------------------------------------------
    # DSS-specific value formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_value(value, field_annots: dict | None = None) -> str | None:
        """Format a Python value into DSS syntax.

        Returns None if the value should be skipped (empty list, etc.).
        """
        field_annots = field_annots or {}

        # Boolean: must come before int since bool subclasses int
        if isinstance(value, bool):
            return 'Yes' if value else 'No'

        # IntEnum (e.g. old-style LoadModel)
        if isinstance(value, IntEnum):
            return str(value.value)

        # LinkML EnumDefinitionImpl — has .code (PermissibleValue) and .meaning
        if hasattr(value, 'code') and hasattr(value, 'meaning'):
            pv = value.code
            meaning = getattr(pv, 'meaning', None)
            if meaning:
                m = _MEANING_INT_RE.search(str(meaning))
                if m:
                    return m.group(1)
            return str(pv.text)

        # LinkML PermissibleValue used directly
        if hasattr(value, 'text') and hasattr(value, 'meaning'):
            meaning = getattr(value, 'meaning', None)
            if meaning:
                m = _MEANING_INT_RE.search(str(meaning))
                if m:
                    return m.group(1)
            return str(value.text)

        # List / multivalued
        if isinstance(value, (list, tuple)):
            if not value:
                return None
            if field_annots.get('dss_format') == 'matrix':
                return DssWriter._format_matrix(list(value))
            # Members are often object names (wires=[...], conns=[...]), so
            # they need the same sanitizing a bare name reference gets.
            return '[' + ' '.join(
                dss_safe_name(v) if isinstance(v, str) else DssWriter._format_value(v) for v in value
            ) + ']'

        # Nested dataclass -> reference by name
        if is_dataclass(value) and not isinstance(value, type):
            return dss_safe_name(str(getattr(value, 'name', value)))

        # Strings reach here as bus references, wire/spacing names, and
        # "Line.<name>" control targets, so they need the same sanitizing the
        # definitions got -- otherwise a reference stops matching its object.
        #
        # Matrix fields are excluded by annotation, not by type: some converters
        # (per_length_impedance) hand back an already-formatted "[a |b c]" string
        # rather than a list, and sanitizing that ate the brackets and row
        # separators -- silently zeroing every line impedance in the model.
        if isinstance(value, str) and field_annots.get('dss_format') != 'matrix':
            return dss_safe_name(value)

        if isinstance(value, float):
            return format_float(value)
        return str(value)

    @staticmethod
    def _format_matrix(values: list) -> str:
        """Format a lower-triangle list as DSS matrix syntax.

        Input: flat lower-triangle [l11, l21, l22, l31, l32, l33]
        Output: [l11 |l21 l22 |l31 l32 l33]
        """
        n = int((-1 + math.sqrt(1 + 8 * len(values))) / 2)
        parts = []
        idx = 0
        for row in range(1, n + 1):
            row_vals = [format_float(float(values[idx + col])) for col in range(row)]
            parts.append(' '.join(row_vals))
            idx += row
        return '[' + ' |'.join(parts) + ']'

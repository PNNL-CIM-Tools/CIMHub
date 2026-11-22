"""GridLAB-D ``.glm`` text -> the native LinkML dataclasses (``cimhub_gridlabd.schema.gridlabd``).

``GlmReader(path).read_all()`` returns a ``GlmModel``: every object whose class the schema knows, plus what the
mappers need beyond the records (written units, expressions, the ``clock``/``module``/``#set`` settings, the
schedules, and the count of each object type the schema does not know).

Rules (GLM_REWRITE_PLAN.md section 3.4). What the reader cannot read raises ``GlmParseError`` with the file and
line; nothing is dropped silently:

- A value keeps the unit it is written in (``30 in``, ``12MVA``): the number is stored and the unit goes to
  ``GlmModel.written_units`` (GLM-2). There is no unit conversion here.
- A numeric or complex property whose text is not a literal (``LIGHTS*1.2``, ``random.normal(1750,400)``) is kept
  verbatim in ``GlmModel.expressions`` and leaves the slot unset. The orchestrator raises when an expression sits
  on a record a mapper reads, so a mapper never sees an unset slot that the deck did set (GLM-8).
- ``${NAME}`` expands from the file's ``#define``/``#set`` (as written so far), then the caller's ``defines``
  (``gridlabd -D``); an unknown name raises (GLM-15).
- An object type the schema does not know is counted in ``GlmModel.not_read`` (GLM-14) and its properties are not
  read. A property a known class does not have raises. Keywords are case-sensitive, as in GridLAB-D's parser.
- ``#include`` is followed relative to the including file. ``#if*`` and other directives raise, as does a
  ``class`` block other than the GridAPPS-D run file's ``class player { double value; }`` (``GlmModel.classes``).
- A ``player``'s ``file`` is read beside the file that declares the player, into ``GlmModel.tapes``: its
  ``time,value`` rows as written, comment and blank lines dropped, the value ending at a ``;`` (GridLAB-D's
  ``player.cpp:345``). A missing file or a row with no comma raises.
- ``object x { object y { ... }; }``: the nested object's ``parent`` is the enclosing object.
- ``object house:..20 { ... }`` makes 20 objects, nested objects included.
- A property set twice keeps the last value, as GridLAB-D does, with a warning.
- Names are unique across the model (GridLAB-D's rule). An unnamed object is called ``<class>:<id>``: its header
  id, else its position among the file's objects (GridLAB-D's object id, counted from 0). A reference written as
  ``<class>:<id>`` resolves to the object's name.
- Complex values: ``a+bj`` / ``a+bi`` (rectangular), ``m+ad`` (polar, degrees) and ``m+ar`` (radians), or a
  plain real number. A polar value is stored rectangular and listed in ``GlmModel.polar``.
"""

from __future__ import annotations

import cmath
import dataclasses
import functools
import logging
import math
import re
import typing
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, NamedTuple

from linkml_runtime.utils.enumerations import EnumDefinitionImpl

from cimhub_core import GraphModel
from cimhub_core.base import FormatReader
from cimhub_gridlabd import glm_schema
from cimhub_gridlabd.schema import gridlabd

_log = logging.getLogger(__name__)


class GlmParseError(Exception):
    """A ``.glm`` the reader cannot read, with the file and line."""

    def __init__(self, message: str, path: Path | str, line: int):
        super().__init__(f"{path}:{line}: {message}")
        self.path = str(path)
        self.line = line


@dataclass
class GlmModel(GraphModel):
    """The records of a ``.glm``, keyed by name, and what the mappers need beyond them."""

    written_units: dict[tuple[str, str], str] = field(default_factory=dict, repr=False)
    """``(object name, slot) -> unit`` for every value written with a unit (``distance_AN 30 in``)."""
    expressions: dict[tuple[str, str], str] = field(default_factory=dict, repr=False)
    """``(object name, slot) -> text`` for every numeric value that is not a literal (``LIGHTS*1.2``)."""
    polar: dict[tuple[str, str], tuple[float, float]] = field(default_factory=dict, repr=False)
    """``(object name, slot) -> (magnitude, angle in degrees)`` as written, for every complex value written in polar
    form: its rectangular value went through sin and cos, which differ in the last bit between C libraries."""
    not_read: Counter = field(default_factory=Counter)
    """Object type -> count, for the types the schema does not know (``recorder``)."""
    clock: dict[str, str] = field(default_factory=dict)
    modules: dict[str, dict[str, str]] = field(default_factory=dict)
    globals: dict[str, str] = field(default_factory=dict)
    """``#set name=value``."""
    defines: dict[str, str] = field(default_factory=dict)
    """``#define name=value``, and the caller's ``defines``."""
    schedules: dict[str, list[str]] = field(default_factory=dict)
    """Schedule name -> its statements, as written."""
    classes: dict[str, dict[str, str]] = field(default_factory=dict)
    """``class`` blocks: class name -> ``{property: type}`` (only ``player`` -> ``{"value": "double"}`` is read)."""
    tapes: dict[str, list[tuple[str, str]]] = field(default_factory=dict, repr=False)
    """Player name -> its file's ``(time, value)`` rows, as written."""
    origins: dict[str, tuple[str, int]] = field(default_factory=dict, repr=False)
    """Object name -> ``(file, line)`` of its ``object`` header, for error messages."""

    def by_name(self, name: str):
        """The record called ``name``, whatever its class (GLM names are unique across the model)."""
        for bucket in self.graph.values():
            if name in bucket:
                return bucket[name]
        raise KeyError(f"no object named {name!r}")

    def unit(self, record, slot: str) -> str | None:
        """The unit ``slot`` of ``record`` is written in: as written, else the schema's declared unit."""
        written = self.written_units.get((str(record.name), slot))
        return written if written is not None else glm_schema.slots(type(record))[slot].unit


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

class _Token(NamedTuple):
    kind: str
    """``open`` (text before ``{``), ``close`` (text before ``}``), ``end`` (text before ``;``), ``directive``."""
    text: str
    path: Path
    line: int


def _tokens(path: Path) -> Iterator[_Token]:
    """The statements of one file, in order. ``//`` comments are dropped; quoted text and ``${NAME}`` are kept
    whole; a line starting with ``#`` is a directive."""
    text = path.read_text(encoding="utf-8")
    buffer: list[str] = []
    line = start = 1
    at_line_start = True
    index = 0
    while index < len(text):
        char = text[index]
        whole = None
        if char == '"':
            whole = text.find('"', index + 1)
            if whole < 0 or "\n" in text[index:whole]:
                raise GlmParseError("unterminated quoted text", path, line)
        elif text.startswith("${", index):
            whole = text.find("}", index)
            if whole < 0 or "\n" in text[index:whole]:
                raise GlmParseError("unterminated ${...}", path, line)
        if whole is not None:
            if not buffer:
                start = line
            buffer.append(text[index:whole + 1])
            index = whole + 1
            at_line_start = False
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline
            continue
        if char == "#" and at_line_start:
            newline = text.find("\n", index)
            end = len(text) if newline < 0 else newline
            if buffer:
                raise GlmParseError("a directive inside an unfinished statement", path, line)
            yield _Token("directive", text[index:end].strip(), path, line)
            index = end
            continue
        if char in "{};":
            yield _Token({"{": "open", "}": "close", ";": "end"}[char], "".join(buffer).strip(), path,
                         start if buffer else line)
            buffer = []
        elif buffer or not char.isspace():
            if not buffer:
                start = line
            buffer.append(char)
        if char == "\n":
            line += 1
            at_line_start = True
        elif not char.isspace():
            at_line_start = False
        index += 1
    if buffer:
        raise GlmParseError(f"statement {''.join(buffer).strip()!r} has no closing ';'", path, start)


# ---------------------------------------------------------------------------
# Raw objects (pass 1)
# ---------------------------------------------------------------------------

@dataclass
class _RawObject:
    type_name: str
    header_id: str | None
    path: Path
    line: int
    properties: dict[str, tuple[str, Path, int]] = field(default_factory=dict)
    children: list["_RawObject"] = field(default_factory=list)
    copies: int = 1
    """``object house:..20`` makes 20."""

    @property
    def alias(self) -> str | None:
        return f"{self.type_name}:{self.header_id}" if self.header_id is not None else None


#: The one ``class`` block read: the GridAPPS-D run file's player value.
PLAYER_CLASS = {"value": "double"}

_OBJECT_HEADER = re.compile(r"^object\s+([A-Za-z_]\w*)(?::(\S*))?$")
_RANGE = re.compile(r"^\.\.(\d+)$")
_MACRO = re.compile(r"\$\{([A-Za-z_]\w*)\}")
_ASSIGNMENT = re.compile(r"^([A-Za-z_][\w.:]*)\s*=\s*(.*)$")  # module globals: powerflow::nominal_frequency


class _Parser:
    def __init__(self, model: GlmModel, caller_defines: dict[str, str]):
        self.model = model
        self.caller_defines = dict(caller_defines)
        self.objects: list[_RawObject] = []
        """Top-level objects, in file order."""
        self.repeated: dict[tuple[str, str], list] = {}
        """``(type, property) -> [count, path, line]`` of properties set twice on one object."""

    def parse_file(self, path: Path) -> None:
        tokens = _tokens(path)
        for token in tokens:
            self._top(token, tokens)

    def _top(self, token: _Token, tokens: Iterator[_Token]) -> None:
        if token.kind == "directive":
            self._directive(token)
        elif token.kind == "open":
            keyword, _, rest = token.text.partition(" ")
            rest = rest.strip()
            if keyword == "object":
                self.objects.append(self._object(token, tokens))
            elif keyword == "clock" and not rest:
                self.model.clock.update(self._settings(tokens, token))
            elif keyword == "module" and rest:
                self.model.modules[rest] = self._settings(tokens, token)
            elif keyword == "schedule" and rest:
                self.model.schedules[rest] = self._block_text(tokens, token)
            elif keyword == "class" and rest:
                self._class(rest, tokens, token)
            else:
                raise GlmParseError(f"unknown block {token.text!r}", token.path, token.line)
        elif token.kind == "end":
            keyword, _, rest = token.text.partition(" ")
            if not token.text:
                return  # the ';' after a block's '}'
            if keyword == "module" and rest.strip():
                self.model.modules.setdefault(rest.strip(), {})
            else:
                raise GlmParseError(f"unknown statement {token.text!r}", token.path, token.line)
        else:
            raise GlmParseError("'}' with no open block", token.path, token.line)

    def _directive(self, token: _Token) -> None:
        word, _, rest = token.text.partition(" ")
        rest = rest.strip()
        if word in ("#set", "#define"):
            match = _ASSIGNMENT.match(rest)
            if match is None:
                raise GlmParseError(f"{word} needs name=value, got {rest!r}", token.path, token.line)
            target = self.model.globals if word == "#set" else self.model.defines
            target[match.group(1)] = self._expand(_unquote(match.group(2).strip()), token)
        elif word == "#include":
            included = token.path.parent / _unquote(rest.strip("<>"))
            if not included.is_file():
                raise GlmParseError(f"#include file {included} does not exist", token.path, token.line)
            self.parse_file(included)
        else:
            raise GlmParseError(f"directive {word!r} is not read", token.path, token.line)

    def _settings(self, tokens: Iterator[_Token], header: _Token) -> dict[str, str]:
        settings: dict[str, str] = {}
        for token in tokens:
            if token.kind in ("end", "close") and token.text:
                key, _, value = token.text.partition(" ")
                settings[key] = self._expand(_unquote(value.strip()), token)
            if token.kind == "close":
                return settings
            if token.kind in ("open", "directive"):
                raise GlmParseError(f"{token.text!r} inside {header.text}", token.path, token.line)
        raise GlmParseError(f"{header.text} block is not closed", header.path, header.line)

    def _class(self, name: str, tokens: Iterator[_Token], header: _Token) -> None:
        """Only ``class player { double value; }``: the run file's player value (``GLM_REWRITE_PLAN.md`` 8.9)."""
        declared = {prop: kind for kind, prop in self._settings(tokens, header).items()}
        if (name, declared) != ("player", PLAYER_CLASS):
            raise GlmParseError(f"class {name} {{{declared}}}: only class player {{ double value; }} is read",
                                header.path, header.line)
        self.model.classes[name] = declared

    @staticmethod
    def _block_text(tokens: Iterator[_Token], header: _Token) -> list[str]:
        """A schedule's statements as written (nested blocks flattened to their text), until its '}'."""
        statements: list[str] = []
        depth = 1
        for token in tokens:
            if token.kind == "open":
                depth += 1
                statements.append(f"{token.text} {{")
            elif token.kind == "close":
                if token.text:
                    statements.append(token.text)
                depth -= 1
                if depth == 0:
                    return statements
                statements.append("}")
            elif token.text:
                statements.append(token.text)
        raise GlmParseError(f"{header.text} block is not closed", header.path, header.line)

    def _object(self, header: _Token, tokens: Iterator[_Token]) -> _RawObject:
        match = _OBJECT_HEADER.match(header.text)
        if match is None:
            raise GlmParseError(f"cannot read object header {header.text!r}", header.path, header.line)
        header_id = match.group(2) or None
        copies = 1
        if header_id is not None and header_id.startswith(".."):
            ranged = _RANGE.match(header_id)
            if ranged is None:
                raise GlmParseError(f"cannot read object range {header.text!r}", header.path, header.line)
            header_id, copies = None, int(ranged.group(1))
        raw = _RawObject(match.group(1), header_id, header.path, header.line, copies=copies)
        for token in tokens:
            if token.kind == "directive":
                self._directive(token)
            elif token.kind == "open":
                if not token.text.startswith("object "):
                    raise GlmParseError(f"block {token.text!r} inside an object", token.path, token.line)
                raw.children.append(self._object(token, tokens))
            elif token.text:
                self._property(raw, token)
            if token.kind == "close":
                return raw
        raise GlmParseError(f"object {header.text!r} is not closed", header.path, header.line)

    def _property(self, raw: _RawObject, token: _Token) -> None:
        key, _, value = token.text.partition(" ")
        value = value.strip()
        if not value:
            raise GlmParseError(f"property {key!r} has no value", token.path, token.line)
        if key in raw.properties:
            self.repeated.setdefault((raw.type_name, key), [0, token.path, token.line])[0] += 1
        raw.properties[key] = (self._expand(_unquote(value), token), token.path, token.line)

    def _expand(self, value: str, token: _Token) -> str:
        def replace(match: re.Match) -> str:
            name = match.group(1)
            for source in (self.model.defines, self.model.globals, self.caller_defines):
                if name in source:
                    return source[name]
            raise GlmParseError(f"macro ${{{name}}} is not defined (pass it in defines=)", token.path, token.line)

        return _MACRO.sub(replace, value)


def _unquote(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return text[1:-1]
    return text


class _Object(NamedTuple):
    """One object to build: its raw text, its name and its parent's name (a nested object's enclosing one)."""

    raw: _RawObject
    name: str
    parent: str | None


def _expand_objects(top_level: list[_RawObject]) -> list[_Object]:
    """Every object in GridLAB-D's creation order: a parent before its nested objects, a range's copies one after
    another."""
    ordered: list[tuple[_RawObject, int | None]] = []  # (raw object, its parent's position)

    def visit(raw: _RawObject, parent: int | None) -> None:
        for _ in range(raw.copies):
            position = len(ordered)
            ordered.append((raw, parent))
            for child in raw.children:
                visit(child, position)

    for raw in top_level:
        visit(raw, None)
    names = [_object_name(raw, position) for position, (raw, _) in enumerate(ordered)]
    return [_Object(raw, names[position], None if parent is None else names[parent])
            for position, (raw, parent) in enumerate(ordered)]


def _object_name(raw: _RawObject, position: int) -> str:
    """``name``, else ``<class>:<header id>``, else ``<class>:<position>`` (GridLAB-D's object id)."""
    if "name" in raw.properties:
        if raw.copies > 1:
            raise GlmParseError("a ranged object cannot give all its copies one name", raw.path, raw.line)
        return raw.properties["name"][0]
    return raw.alias if raw.alias is not None else f"{raw.type_name}:{position}"


# ---------------------------------------------------------------------------
# Values (pass 2)
# ---------------------------------------------------------------------------

_UNSIGNED = r"(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
_NUMBER = rf"[+-]?{_UNSIGNED}"
_UNIT = r"[A-Za-z%][\w/^*.%]*"
_REAL_WITH_UNIT = re.compile(rf"^({_NUMBER})\s*({_UNIT})?$")
_COMPLEX_WITH_UNIT = re.compile(rf"^({_NUMBER})(?:([+-]{_UNSIGNED})([ijdr]))?(?:\s*({_UNIT}))?$")
_BOOLEAN = {"true": True, "false": False}


@functools.cache
def _slot_kinds(native_cls: type) -> dict[str, str]:
    """``{slot: kind}``: ``complex``, ``float``, ``int``, ``bool``, ``enum`` or ``text``."""
    hints = typing.get_type_hints(native_cls)
    kinds = {}
    for slot in (f.name for f in dataclasses.fields(native_cls)):
        args = _flatten(hints[slot])
        if gridlabd.Complex in args:
            kinds[slot] = "complex"
        elif float in args:
            kinds[slot] = "float"
        elif bool in args:
            kinds[slot] = "bool"
        elif int in args:
            kinds[slot] = "int"
        elif any(isinstance(arg, type) and issubclass(arg, EnumDefinitionImpl) for arg in args):
            kinds[slot] = "enum"
        else:
            kinds[slot] = "text"
    return kinds


def _flatten(hint) -> set:
    args = typing.get_args(hint)
    if not args:
        return {hint}
    flat = set()
    for arg in args:
        flat |= _flatten(arg)
    return flat


class _Value(NamedTuple):
    value: Any
    """``None`` for an expression."""
    unit: str | None = None
    polar: tuple[float, float] | None = None
    """(magnitude, angle in degrees) as written, for a polar complex."""


def _convert(kind: str, text: str) -> _Value:
    """The typed value of one property's text. A numeric text that is not a literal is an expression
    (``_Value(None)``); a boolean or integer that is not one raises ``ValueError``."""
    if kind in ("text", "enum"):
        return _Value(text)
    if kind == "bool":
        if text.lower() not in _BOOLEAN:
            raise ValueError(f"{text!r} is not a boolean")
        return _Value(_BOOLEAN[text.lower()])
    if kind == "complex":
        match = _COMPLEX_WITH_UNIT.match(text)
        if match is None:
            return _Value(None)
        first, second, notation, unit = match.groups()
        if second is None:
            return _Value(gridlabd.Complex(real=float(first), imag=0.0), unit)
        if notation in "ij":
            return _Value(gridlabd.Complex(real=float(first), imag=float(second)), unit)
        radians = math.radians(float(second)) if notation == "d" else float(second)
        degrees = float(second) if notation == "d" else math.degrees(radians)
        value = cmath.rect(float(first), radians)
        return _Value(gridlabd.Complex(real=value.real, imag=value.imag), unit, polar=(float(first), degrees))
    match = _REAL_WITH_UNIT.match(text)
    if match is None:
        return _Value(None)
    number, unit = float(match.group(1)), match.group(2)
    if kind == "int":
        if not number.is_integer():
            raise ValueError(f"{text!r} is not an integer")
        return _Value(int(number), unit)
    return _Value(number, unit)


# ---------------------------------------------------------------------------
# The reader
# ---------------------------------------------------------------------------

class GlmReader(FormatReader):
    """Read a ``.glm`` (and the files it ``#include``s) into a ``GlmModel``.

    ``defines`` are the macros the model expects from the command line (``gridlabd -D VSOURCE=66395.28``).
    """

    def __init__(self, source: str | Path, *, defines: dict[str, str] | None = None) -> None:
        self.source = Path(source)
        self.defines = dict(defines or {})

    def read_all(self) -> GlmModel:
        if not self.source.is_file():
            raise FileNotFoundError(f"GLM file not found: {self.source}")
        model = GlmModel()
        parser = _Parser(model, self.defines)
        parser.parse_file(self.source)
        for (type_name, key), (count, path, line) in parser.repeated.items():
            _log.warning("%s.%s is set twice on %d object(s), first at %s:%d; the last value is kept", type_name,
                         key, count, path, line)
        for name, value in self.defines.items():
            model.defines.setdefault(name, value)
        _build(model, _expand_objects(parser.objects))
        for player in model.list_by_class(gridlabd.Player):
            if player.file is not None:
                model.tapes[str(player.name)] = read_tape(Path(model.origins[str(player.name)][0]).parent / player.file)
        return model


def read_tape(path: Path) -> list[tuple[str, str]]:
    """A player file's ``(time, value)`` rows as written: ``#`` and blank lines dropped, each value ending at a ``;``
    (``player.cpp:339-345``)."""
    if not path.is_file():
        raise FileNotFoundError(f"player file not found: {path}")
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.startswith("#"):
            continue
        time, comma, value = line.partition(",")
        value = value.split(";", 1)[0].strip()
        if not comma or not time.strip() or not value:
            raise GlmParseError(f"player row {line!r} is not time,value", path, number)
        rows.append((time.strip(), value))
    return rows


def _build(model: GlmModel, objects: list[_Object]) -> None:
    """Resolve ``<class>:<id>`` references, type the values and add the records."""
    seen: dict[str, _RawObject] = {}
    aliases: dict[str, str] = {}
    for obj in objects:
        if obj.name in seen:
            first = seen[obj.name]
            raise GlmParseError(f"name {obj.name!r} is already used by the object at {first.path}:{first.line}",
                                obj.raw.path, obj.raw.line)
        seen[obj.name] = obj.raw
        if obj.raw.alias is not None:
            aliases[obj.raw.alias] = obj.name

    registry = glm_schema.class_registry()
    for obj in objects:
        native_cls = registry.get(obj.raw.type_name)
        if native_cls is None:
            model.not_read[obj.raw.type_name] += 1
            continue
        properties = dict(obj.raw.properties)
        if obj.parent is not None:
            if "parent" in properties:
                raise GlmParseError("a nested object sets its own parent", obj.raw.path, obj.raw.line)
            properties["parent"] = (obj.parent, obj.raw.path, obj.raw.line)
        model.add_to_graph(_record(model, native_cls, obj, properties, aliases))
        model.origins[obj.name] = (str(obj.raw.path), obj.raw.line)


def _record(model: GlmModel, native_cls: type, obj: _Object, properties: dict, aliases: dict[str, str]):
    slot_of = glm_schema.slot_for_property(native_cls)
    kinds = _slot_kinds(native_cls)
    values: dict[str, Any] = {"name": obj.name}
    for key, (text, path, line) in properties.items():
        if key == "name":
            continue
        slot = slot_of.get(key)
        if slot is None:
            raise GlmParseError(f"{obj.raw.type_name} has no property {key!r}", path, line)
        if kinds[slot] == "text":
            text = aliases.get(text, text)
        try:
            converted = _convert(kinds[slot], text)
        except ValueError as error:
            raise GlmParseError(f"{obj.raw.type_name}.{key}: {error}", path, line) from None
        if converted.value is None:
            model.expressions[(obj.name, slot)] = text
            continue
        values[slot] = converted.value
        if converted.unit is not None:
            model.written_units[(obj.name, slot)] = converted.unit
        if converted.polar is not None:
            model.polar[(obj.name, slot)] = converted.polar
    try:
        return native_cls(**values)
    except (ValueError, TypeError) as error:
        raise GlmParseError(f"{obj.raw.type_name} {obj.name!r}: {error}", obj.raw.path, obj.raw.line) from None

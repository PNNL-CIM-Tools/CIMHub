"""FormatReader for OpenDSS ``.dss`` files.

Parses a Master.dss (including all ``Redirect`` targets) into LinkML-generated
dataclass instances from ``opendss_schema``.

Usage::

    from cimhub_opendss.dss_reader import DssReader
    from cimhub_opendss.schema.opendss_schema import Load, Line

    model = DssReader("path/to/Master.dss").read_all()
    loads = model.list_by_class(Load)
    lines = model.list_by_class(Line)

The source is bound at construction and the whole file tree is parsed once, on
the first ``read_all()`` call; the result is cached, so repeated calls are free.
"""
from __future__ import annotations

import functools
import logging
import re
from dataclasses import dataclass, fields as dc_fields, is_dataclass, replace
from pathlib import Path
from typing import Any, Iterator, Union, get_args, get_origin

import cimhub_opendss.schema.opendss_schema as dss_schema
from cimhub_core import GraphModel
from cimhub_core.base import FormatReader
from cimhub_core.cimtbl import schema_defaults
from cimhub_opendss.dss_name_map import (
    DssClassMap,
    build_type_registry,
    get_class_map,
)

_log = logging.getLogger(__name__)

__all__ = ["DssReader", "DssParseError", "KEPT_OPTIONS", "dss_defaults"]

#: ``Set`` options that describe the circuit, kept on the model as ``Options`` (DSS_REWRITE_PLAN.md section 3.4).
KEPT_OPTIONS = frozenset({"voltagebases", "defaultbasefreq", "earthmodel"})


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------

class DssParseError(Exception):
    """Error parsing a DSS file."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        line_number: int | None = None,
    ):
        parts = [message]
        if file_path:
            parts.append(f"in {file_path}")
        if line_number:
            parts.append(f"at line {line_number}")
        super().__init__(" ".join(parts))
        self.file_path = file_path
        self.line_number = line_number


# ---------------------------------------------------------------------------
# Parsed command
# ---------------------------------------------------------------------------

@dataclass
class DssCommand:
    """A single parsed DSS command."""

    cmd: str  # "new", "edit", "batchedit", "set", "clear"
    element_type: str | None  # "Load", "Transformer" (original case)
    element_name: str | None  # "671", "sub3"
    params: dict[str, str]  # raw key=value (original-case keys)
    source_file: str  # for error reporting
    line_number: int
    raw_text: str = ""  # full merged text of the command (for per-winding parsing)


def _resolve_file_case_insensitive(path: Path) -> Path:
    """Resolve file path case-insensitively on case-sensitive filesystems."""
    if path.exists():
        return path
    parent = path.parent
    if not parent.is_dir():
        return path
    name_lower = path.name.lower()
    for child in parent.iterdir():
        if child.name.lower() == name_lower:
            return child
    return path


class DssReader(FormatReader):
    """Parse OpenDSS files into LinkML dataclass instances.

    Handles Master file with Redirect commands, ``New``/``Edit``/``Set``
    commands, case-insensitive property names, YAML-driven ``dss_name``
    mapping, array values, continuation lines (``~``), and comments
    (``!`` and ``//``).
    """

    def __init__(self, source: str | Path) -> None:
        """Bind *source* (a Master.dss path) without parsing it."""
        self.source = source
        self._commands: list[DssCommand] | None = None
        self._model: GraphModel | None = None
        # BusCoords CSV paths encountered during file traversal (in encounter order).
        self._buscoords_paths: list[Path] = []
        # LatLongCoords CSV paths — same format but (lat, long) → stored as (x=long, y=lat).
        self._latlongcoords_paths: list[Path] = []

    # -----------------------------------------------------------------------
    # Public API  (FormatReader interface)
    # -----------------------------------------------------------------------

    def read_all(self) -> GraphModel:
        """Parse the bound source and return every object found.

        Includes ``Buscoords`` rows from any ``BusCoords`` / ``LatLongCoords``
        CSV the file tree references — those have no ``New`` command, so they are
        parsed from their own files rather than from the command list.

        Parsing happens once; the resulting graph is cached and returned as-is on
        later calls.
        """
        if self._model is None:
            self._parse_master(self.source)
            self._model = self._build_graph()
        return self._model

    # -----------------------------------------------------------------------
    # Bus coordinates
    # -----------------------------------------------------------------------

    def _read_buscoords(self) -> list:
        """Parse every referenced BusCoords/LatLongCoords CSV into Buscoords objects.

        Both directives use a headerless ``BusName, c1, c2`` CSV, but the column
        order differs: ``BusCoords`` is already ``x, y`` while ``LatLongCoords``
        is ``lat, long`` and must be swapped so x is always the horizontal axis.
        The directive decides, not the filename — IEEE13_Assets points a
        ``BusCoords`` directive at a file called ``..._latlon.csv``.

        Rows whose coordinate columns are not numeric are skipped: these files
        are sometimes shipped with a header row or ``!`` comment banner. A
        referenced file that does not exist raises.
        """
        objects: list = []
        for csv_path, geographic in [(path, False) for path in self._buscoords_paths] + \
                [(path, True) for path in self._latlongcoords_paths]:
            with open(csv_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("!") or line.startswith("//"):
                        continue
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) < 3:
                        continue
                    try:
                        c1, c2 = float(parts[1]), float(parts[2])
                    except ValueError:
                        continue  # header row
                    x, y = (c2, c1) if geographic else (c1, c2)  # lat,long -> x=long, y=lat
                    objects.append(dss_schema.Buscoords(name=parts[0].lower(), x=x, y=y, geographic=geographic))
        return objects

    # -----------------------------------------------------------------------
    # File traversal
    # -----------------------------------------------------------------------

    def _parse_master(self, master_path: str | Path) -> None:
        """Parse Master.dss and all redirected files into a command list."""
        self._commands = []
        self._buscoords_paths = []
        self._latlongcoords_paths = []
        raw_lines = list(self._read_with_redirects(Path(master_path)))
        joined = self._join_continuation_lines(raw_lines)

        for line, file_path, line_number in joined:
            try:
                cmd = self._parse_command_line(line, str(file_path), line_number)
            except ValueError as e:
                raise DssParseError(f"{e}: {line}", str(file_path), line_number) from e
            if cmd is not None:
                self._commands.append(cmd)

    def _build_graph(self) -> GraphModel:
        """Apply the commands in deck order, as DSS does.

        - ``New`` creates the object. ``like=`` first copies every slot the command leaves unset from the
          named object of the same class, which must already exist.
        - A second ``New`` of an existing object redefines it: DSS applies it as an edit, and so does the
          reader, with one warning per object.
        - ``Edit`` (and ``Class.name.property=value``) changes an object that must already exist.
        - ``BatchEdit Class.<regex>`` changes every object of the class whose name the regular expression
          matches (case-insensitive search, as DSS does); it must match at least one.
        - ``Set`` keeps the circuit options in ``KEPT_OPTIONS`` on one ``Options`` object. The other options
          are solution settings (``mode``, ``controlmode``, ...) and are not part of the model.
        - ``Clear`` discards everything defined before it, as in DSS (a deck may build, solve and rebuild).
        - ``New Circuit.<name>`` is ``New Vsource.source``, as in DSS; ``Options.circuit`` keeps the name.
          A second ``New Circuit`` raises: a deck is one circuit.

        Names are case-insensitive, as in DSS; an object keeps the spelling of its first ``New``.
        """
        types = build_type_registry()
        graph: dict[type, dict[str, Any]] = {}
        spelled: dict[tuple[type, str], str] = {}  # (class, lowered name) -> name as first written
        redefined: set[tuple[type, str]] = set()
        options: dict[str, Any] = {}
        for cmd in self._commands:
            if cmd.cmd == "clear":
                graph, spelled, redefined, options = {}, {}, set(), {}
                continue
            try:
                if cmd.cmd == "set":
                    options.update(self._options(cmd))
                    continue
                if cmd.element_type.lower() == "circuit":
                    cmd = self._circuit(cmd, options)
                schema_class = types.get(cmd.element_type.lower())
                if schema_class is None:
                    raise ValueError(f"unknown DSS class {cmd.element_type!r}")
                bucket = graph.setdefault(schema_class, {})
                values = self._values(cmd, schema_class)
                if cmd.cmd == "batchedit":
                    _batch_edit(bucket, cmd.element_name, values)
                    continue
                key = (schema_class, cmd.element_name.lower())
                if cmd.cmd == "new" and key not in spelled:
                    obj = schema_class(name=cmd.element_name, **values)
                    if getattr(obj, "like", None):
                        _inherit(obj, bucket.get(spelled.get((schema_class, str(obj.like).lower()), "")))
                    bucket[cmd.element_name] = obj
                    spelled[key] = cmd.element_name
                    continue
                if key not in spelled:
                    raise ValueError("Edit of an object no New defines")
                if cmd.cmd == "new" and key not in redefined:
                    redefined.add(key)
                    _log.warning("%s:%d: New %s.%s again; applied as an edit, as DSS does",
                                 cmd.source_file, cmd.line_number, cmd.element_type, cmd.element_name)
                obj = bucket[spelled[key]]
                for field_name, value in values.items():
                    setattr(obj, field_name, value)
            except (ValueError, TypeError) as e:
                raise DssParseError(f"{cmd.element_type}.{cmd.element_name}: {e}",
                                    cmd.source_file, cmd.line_number) from e

        if options:
            graph[dss_schema.Options] = {"options": dss_schema.Options(name="options", **options)}
        for bc in self._read_buscoords():
            graph.setdefault(dss_schema.Buscoords, {})[str(bc.name)] = bc
        return GraphModel(graph=graph)

    @staticmethod
    def _circuit(cmd: DssCommand, options: dict[str, Any]) -> DssCommand:
        """``New Circuit.<name>`` as ``New Vsource.source``; the name goes on ``options``."""
        if cmd.cmd != "new":
            raise ValueError(f"{cmd.cmd} Circuit: only New Circuit is read; edit the circuit as Vsource.source")
        if "circuit" in options:
            raise ValueError(f"a second New Circuit (the first is {options['circuit']!r}); a deck is one circuit")
        options["circuit"] = cmd.element_name
        return replace(cmd, element_type="Vsource", element_name="source")

    def _options(self, cmd: DssCommand) -> dict[str, Any]:
        """The kept circuit options a ``Set`` command gives, converted like any property."""
        class_map = get_class_map(dss_schema.Options)
        return {class_map.field_for(name): self._convert_value(raw, class_map.field_for(name), dss_schema.Options,
                                                                class_map)
                for name, raw in cmd.params.items() if name.lower() in KEPT_OPTIONS}

    def _read_with_redirects(
        self, master_path: Path
    ) -> Iterator[tuple[str, Path, int]]:
        """Recursively read DSS files, following ``Redirect`` commands.

        Yields ``(stripped_line, file_path, line_number)`` tuples.
        """
        base_dir = master_path.parent

        def _process_file(
            file_path: Path,
        ) -> Iterator[tuple[str, Path, int]]:
            try:
                resolved_file = _resolve_file_case_insensitive(file_path)
                with open(resolved_file, "r", encoding="utf-8") as fh:
                    for line_num, raw_line in enumerate(fh, start=1):
                        line = _strip_comment(raw_line).strip()
                        if not line:
                            continue

                        lower = line.lower()
                        if lower.startswith("redirect") or lower.startswith("compile"):
                            # Extract target file name
                            rest = line.split(None, 1)
                            if len(rest) > 1:
                                target_name = rest[1].strip().strip("\"'")
                                target_path = _resolve_file_case_insensitive(base_dir / target_name)
                                if not target_path.exists():
                                    raise DssParseError(f"Redirect target not found: {target_path}",
                                                        str(file_path), line_num)
                                yield from _process_file(target_path)
                            continue

                        # BusCoords / LatLongCoords: CSV format bus,c1,c2.
                        # BusCoords: c1=x, c2=y. LatLongCoords: c1=lat, c2=long → swap to x=long, y=lat.
                        if lower.startswith("buscoords") or lower.startswith("latlongcoords"):
                            rest = line.split(None, 1)
                            if len(rest) > 1:
                                csv_name = rest[1].strip().strip("\"'")
                                csv_path = _resolve_file_case_insensitive(base_dir / csv_name)
                                if lower.startswith("latlongcoords"):
                                    self._latlongcoords_paths.append(csv_path)
                                else:
                                    self._buscoords_paths.append(csv_path)
                            continue

                        yield line, file_path, line_num

            except FileNotFoundError:
                raise FileNotFoundError(f"DSS file not found: {file_path}")

        yield from _process_file(master_path)

    # -----------------------------------------------------------------------
    # Continuation-line joining
    # -----------------------------------------------------------------------

    @staticmethod
    def _join_continuation_lines(
        raw_lines: list[tuple[str, Path, int]],
    ) -> list[tuple[str, Path, int]]:
        """Merge ``~`` continuation lines with the element they extend.

        In OpenDSS a ``~`` continues the most recent ``New``/``Edit`` element
        command, even when ``set`` commands, comments, or blank lines appear in
        between (comments/blanks are already stripped upstream). Appending to the
        immediate predecessor would misattach ``~`` params to an intervening
        ``set`` command — e.g. a ``New Circuit`` whose ``~ pu=1.05`` line follows
        a couple of ``set`` commands.
        """
        result: list[tuple[str, Path, int]] = []
        last_element_idx: int | None = None

        for line, file_path, line_num in raw_lines:
            if line.startswith("~"):
                if last_element_idx is not None:
                    prev_line, prev_file, prev_num = result[last_element_idx]
                    result[last_element_idx] = (
                        prev_line + " " + line[1:].strip(),
                        prev_file,
                        prev_num,
                    )
                else:
                    # Orphan continuation; treat as standalone
                    result.append((line[1:].strip(), file_path, line_num))
                    last_element_idx = len(result) - 1
            else:
                result.append((line, file_path, line_num))
                first_word = line.split(None, 1)[0].lower() if line.split() else ""
                if first_word in ("new", "edit"):
                    last_element_idx = len(result) - 1

        return result

    # -----------------------------------------------------------------------
    # Command parsing
    # -----------------------------------------------------------------------

    def _parse_command_line(
        self, line: str, file_path: str, line_number: int
    ) -> DssCommand | None:
        """Route a command line to the appropriate parser."""
        parts = line.split(None, 1)
        if not parts:
            return None

        cmd_word = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if cmd_word == "new":
            return self._parse_new_or_edit("new", rest, file_path, line_number)
        elif cmd_word == "edit":
            return self._parse_new_or_edit("edit", rest, file_path, line_number)
        elif cmd_word == "set":
            return self._parse_set_command(rest, file_path, line_number)
        elif cmd_word == "batchedit":
            return self._parse_new_or_edit("batchedit", rest, file_path, line_number)
        elif cmd_word in ("clear", "clearall"):
            return DssCommand("clear", None, None, {}, file_path, line_number)
        else:
            # Check for implicit edit: Type.Name.Property=Value (no keyword)
            # e.g. "Transformer.Reg1.Taps=[1.0 1.0625]"
            # Use original line (not lowercased cmd_word) to preserve case
            dot_count = line.split("=", 1)[0].count(".")
            if dot_count >= 2 and "=" in line:
                return self._parse_dotted_edit(line.strip(), file_path, line_number)
            # Skip simulation commands: solve, calcvoltagebases, etc.
            return None

    def _parse_new_or_edit(
        self, cmd: str, rest: str, file_path: str, line_number: int
    ) -> DssCommand | None:
        """Parse ``New Type.Name params...`` or ``Edit Type.Name params...``."""
        if not rest.strip():
            return None

        # Split off the Type.Name token (may be quoted)
        rest = rest.strip()
        if rest.startswith('"'):
            end_quote = rest.index('"', 1)
            type_name_token = rest[1:end_quote]
            param_text = rest[end_quote + 1 :].strip()
        elif rest.startswith("'"):
            end_quote = rest.index("'", 1)
            type_name_token = rest[1:end_quote]
            param_text = rest[end_quote + 1 :].strip()
        else:
            parts = rest.split(None, 1)
            type_name_token = parts[0]
            param_text = parts[1] if len(parts) > 1 else ""

        # Strip optional "object=" or "element=" prefix in DSS commands (e.g. New object=circuit.ieee123)
        if type_name_token.lower().startswith(("object=", "element=")):
            type_name_token = type_name_token.split("=", 1)[1]

        # Split Type.Name
        if "." not in type_name_token:
            raise ValueError(f"expected Class.name, got {type_name_token!r}")

        element_type, element_name = type_name_token.split(".", 1)
        if element_type.lower().startswith("object="):
            element_type = element_type.split("=", 1)[1]
        elif element_type.lower().startswith("element="):
            element_type = element_type.split("=", 1)[1]

        # Pre-process transformer wdg=N per-winding syntax before parsing
        if element_type.lower() in ("transformer", "xfmrcode"):
            param_text = self._preprocess_winding_text(param_text)
        params = self._parse_params(param_text)

        return DssCommand(
            cmd=cmd,
            element_type=element_type,
            element_name=element_name,
            params=params,
            source_file=file_path,
            line_number=line_number,
            raw_text=param_text,
        )

    def _parse_dotted_edit(
        self, line: str, file_path: str, line_number: int
    ) -> DssCommand | None:
        """Parse ``Type.Name.Property=Value`` implicit edit syntax.

        Example: ``Transformer.Reg1.Taps=[1.0 1.0625]``
        """
        # Split at first '=' to get the dotted path and value
        lhs, rhs = line.split("=", 1)
        parts = lhs.strip().split(".")
        if len(parts) < 3:
            return None
        element_type = parts[0]
        element_name = parts[1]
        prop_name = ".".join(parts[2:])  # Handle unlikely multi-dot props
        param_text = f"{prop_name}={rhs}"

        if element_type.lower() in ("transformer", "xfmrcode"):
            param_text = self._preprocess_winding_text(param_text)
        params = self._parse_params(param_text)

        return DssCommand(
            cmd="edit",
            element_type=element_type,
            element_name=element_name,
            params=params,
            source_file=file_path,
            line_number=line_number,
        )

    def _parse_set_command(
        self, rest: str, file_path: str, line_number: int
    ) -> DssCommand | None:
        """Parse ``Set Key=Value ...``."""
        params = self._parse_params(rest)
        if not params:
            return None
        return DssCommand(
            cmd="set",
            element_type=None,
            element_name=None,
            params=params,
            source_file=file_path,
            line_number=line_number,
        )

    # -----------------------------------------------------------------------
    # Parameter tokenization
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_params(text: str) -> dict[str, str]:
        """Parse ``Key1=Value1 Key2=Value2 ...`` into a dict.

        Handles bracketed arrays like ``kVs=[115, 4.16, 13.2]`` and
        ``XSCArray=[ 0.00979 0.02491]``.
        """
        params: dict[str, str] = {}
        if not text or not text.strip():
            return params

        current_key: str | None = None
        current_value_parts: list[str] = []
        bracket_depth = 0

        # Tokenize respecting quotes but splitting on whitespace otherwise
        raw_tokens = _tokenize_dss(text)

        # Pre-merge spaced assignments: "key = value" or "key= value" or "key =value"
        tokens: list[str] = []
        i = 0
        while i < len(raw_tokens):
            tok = raw_tokens[i]
            # Case: "key" "=" "value" or "key" "="
            if (
                i + 1 < len(raw_tokens)
                and raw_tokens[i + 1] == "="
                and "=" not in tok
                and not tok.startswith("[")
                and not tok.startswith("(")
            ):
                # Merge key=value
                merged = tok + "="
                if i + 2 < len(raw_tokens) and "=" not in raw_tokens[i + 2]:
                    merged += raw_tokens[i + 2]
                    i += 3
                else:
                    i += 2
                tokens.append(merged)
            elif tok == "=" and tokens:
                # Bare "=" — merge with previous token as key
                prev = tokens.pop()
                merged = prev + "="
                if i + 1 < len(raw_tokens) and "=" not in raw_tokens[i + 1]:
                    merged += raw_tokens[i + 1]
                    i += 2
                else:
                    i += 1
                tokens.append(merged)
            else:
                tokens.append(tok)
                i += 1

        for token in tokens:
            # Inside brackets — accumulate everything
            if bracket_depth > 0:
                current_value_parts.append(token)
                bracket_depth += token.count("[") + token.count("(")
                bracket_depth -= token.count("]") + token.count(")")
                if bracket_depth <= 0:
                    bracket_depth = 0
                    if current_key is not None:
                        params[current_key] = " ".join(current_value_parts)
                        current_key = None
                        current_value_parts = []
                continue

            # Check for Key=Value
            if "=" in token and not token.startswith("[") and not token.startswith("("):
                key, _, value = token.partition("=")
                key = key.strip()

                # Handle "key =" (space-separated equals): the key arrived as
                # a standalone token in current_value_parts
                if not key and current_value_parts:
                    key = current_value_parts.pop()

                # Save the previously-accumulating param (if any)
                if current_key is not None:
                    params[current_key] = " ".join(current_value_parts)
                    current_value_parts = []

                current_key = key

                if not value:
                    current_value_parts = []
                    continue

                # Check if value opens a bracket
                opens = value.count("[") + value.count("(")
                closes = value.count("]") + value.count(")")
                if opens > closes:
                    bracket_depth = opens - closes
                    current_value_parts = [value]
                else:
                    params[current_key] = value
                    current_key = None
                    current_value_parts = []
            else:
                # Continuation of previous value (e.g. space-separated items
                # outside brackets, which can happen in some DSS variants)
                current_value_parts.append(token)

        # Flush last param
        if current_key is not None:
            params[current_key] = " ".join(current_value_parts)

        return params

    # -----------------------------------------------------------------------
    # Instance construction
    # -----------------------------------------------------------------------

    def _values(self, cmd: DssCommand, schema_class: type) -> dict[str, Any]:
        """``{field: value}`` for the properties a ``New`` or ``Edit`` command sets.

        Transformer and XfmrCode ``wdg=N`` blocks become the per-winding arrays (``buses``, ``kVs``, ...),
        so they are only accepted on a ``New``: an ``Edit`` with ``wdg=`` would replace whole arrays.
        """
        class_map = get_class_map(schema_class)
        params = dict(cmd.params)
        lowered = {k.lower() for k in params}
        element_type = cmd.element_type.lower()
        if element_type in ("transformer", "xfmrcode") and "wdg" in lowered:
            if cmd.cmd != "new":
                raise ValueError("per-winding properties (wdg=) on an Edit are not supported")
            params.update(_extract_winding_arrays(cmd.raw_text))
        if element_type == "linegeometry" and "cond" in lowered:
            params.update(_extract_linegeometry_arrays(cmd.raw_text))

        values: dict[str, Any] = {}
        for param_name, raw_value in params.items():
            field_name = class_map.field_for(param_name)
            if field_name == "name":
                continue
            file_ref = _FILE_ARRAY.match(raw_value.strip())
            if file_ref:
                raw_value = _read_array_file(Path(cmd.source_file).parent / file_ref.group(1).strip("\"' "))
            try:
                values[field_name] = self._convert_value(raw_value, field_name, schema_class, class_map)
            except ValueError as e:
                raise ValueError(f"{param_name}={raw_value!r}: {e}") from e
        return values

    @staticmethod
    def _preprocess_winding_text(param_text: str) -> str:
        """Rewrite per-winding DSS transformer params into array form.

        Transforms the raw parameter text before ``_parse_params`` sees it,
        so duplicate keys (``wdg=1 bus=X wdg=2 bus=Y``) become array keys
        (``buses=[X,Y]``).

        Works on the token stream to avoid dict key-collision issues.
        """
        _WDG_ARRAY_MAP = {
            "bus": "buses",
            "kv": "kVs",
            "kva": "kVAs",
            "conn": "conns",
            "tap": "taps",
            "%r": "pct_Rs",
        }
        _WDG_SCALAR_KEYS = {"rneut", "xneut"}

        tokens = _tokenize_dss(param_text)

        # Pre-merge spaced equals: "key" "=" "value" -> "key=value"
        merged: list[str] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if i + 1 < len(tokens) and tokens[i + 1] == "=" and "=" not in tok:
                m = tok + "="
                if i + 2 < len(tokens) and "=" not in tokens[i + 2]:
                    m += tokens[i + 2]
                    i += 3
                else:
                    i += 2
                merged.append(m)
            elif tok == "=" and merged:
                prev = merged.pop()
                m = prev + "="
                if i + 1 < len(tokens) and "=" not in tokens[i + 1]:
                    m += tokens[i + 1]
                    i += 2
                else:
                    i += 1
                merged.append(m)
            else:
                merged.append(tok)
                i += 1

        # Now walk tokens, collecting per-winding values
        winding_data: dict[str, list[str]] = {v: [] for v in _WDG_ARRAY_MAP.values()}
        non_winding_tokens: list[str] = []
        scalar_overrides: dict[str, str] = {}
        scalar_neutral_wdg: int | None = None
        current_wdg = 0
        in_winding = False

        for tok in merged:
            if "=" not in tok:
                if not in_winding:
                    non_winding_tokens.append(tok)
                continue

            key, _, value = tok.partition("=")
            key_lower = key.strip().lower()

            if key_lower == "wdg":
                current_wdg = int(value)
                in_winding = True
                continue

            # Evaluate RPN before storing
            resolved = _try_eval_rpn(value)

            if in_winding and key_lower in _WDG_ARRAY_MAP:
                target = _WDG_ARRAY_MAP[key_lower]
                while len(winding_data[target]) < current_wdg - 1:
                    winding_data[target].append("")
                if len(winding_data[target]) < current_wdg:
                    winding_data[target].append(resolved)
                else:
                    winding_data[target][current_wdg - 1] = resolved
            elif in_winding and key_lower in _WDG_SCALAR_KEYS:
                # Rneut/Xneut belong to the winding that was active when DSS parsed
                # them. Flattening them to a bare scalar would lose that, and the
                # importer would fall back to the last winding — leaving the
                # intended one ungrounded. Keep the first winding that sets either
                # and emit "wdg=N" alongside so the binding survives.
                if scalar_neutral_wdg is None:
                    scalar_neutral_wdg = current_wdg
                if current_wdg == scalar_neutral_wdg:
                    scalar_overrides[key.strip()] = resolved
            else:
                non_winding_tokens.append(f"{key.strip()}={resolved}")

        # Append array params
        for array_key, values in winding_data.items():
            if values and any(v for v in values):
                non_winding_tokens.append(f"{array_key}=[{','.join(values)}]")
        # Append scalar overrides, tagged with the winding they belong to
        if scalar_overrides and scalar_neutral_wdg is not None:
            non_winding_tokens.append(f"wdg={scalar_neutral_wdg}")
        for k, v in scalar_overrides.items():
            non_winding_tokens.append(f"{k}={v}")

        return " ".join(non_winding_tokens)

    # -----------------------------------------------------------------------
    # Type conversion
    # -----------------------------------------------------------------------

    @staticmethod
    def _convert_value(
        raw_value: str,
        field_name: str,
        schema_class: type,
        class_map: DssClassMap,
    ) -> Any:
        """Convert a raw DSS string value to the correct Python type."""
        val = raw_value.strip()

        # Multivalued fields: pass raw to _parse_array which handles RPN per-element.
        # Do NOT call _try_eval_rpn here — it would collapse the whole array to one value.
        if field_name in class_map.multivalued:
            return DssReader._parse_array(val, field_name, schema_class, class_map)

        # Scalar: evaluate RPN expressions first
        val = _try_eval_rpn(val)

        # Strip surrounding quotes (for plain quoted strings / already-evaluated values)
        if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
            val = val[1:-1]
        val = val.rstrip(",")  # DSS delimits with commas too: npts='1,' is 1

        # Check for enum (scalar enum)
        if field_name in class_map.enum_value_maps:
            return DssReader._convert_enum(val, field_name, class_map)

        # Get the Python field type from the dataclass
        fld_type = _get_field_type(schema_class, field_name)

        return DssReader._convert_scalar(val, fld_type)

    @staticmethod
    def _convert_scalar(val: str, fld_type: Any) -> Any:
        """Convert a scalar string to the target type."""
        # Unwrap Optional[X] / Union[X, None]
        actual_type = _unwrap_optional(fld_type)

        if actual_type is None:
            return val

        # Check for bool/Bool first (before int, since bool is subclass of int)
        type_name = getattr(actual_type, "__name__", str(actual_type))
        if type_name in ("bool", "Bool"):
            return _parse_bool(val)

        if actual_type is int or type_name == "int":
            return int(float(_try_eval_rpn(val)))

        if actual_type is float or type_name == "float":
            return float(_try_eval_rpn(val))

        if actual_type is str or type_name in ("str", "string"):
            return val

        # Fallback: return as string
        return val

    @staticmethod
    def _convert_enum(
        val: str, field_name: str, class_map: DssClassMap
    ) -> Any:
        """Resolve a DSS enum value to a Python enum member."""
        enum_map = class_map.enum_value_maps[field_name]
        member = enum_map.get(val.lower())
        if member is None:
            raise ValueError(f"{val!r} is not one of {sorted(enum_map)}")
        return member

    @staticmethod
    def _parse_array(
        raw_value: str,
        field_name: str,
        schema_class: type,
        class_map: DssClassMap,
    ) -> list:
        """Parse ``[val1, val2, ...]`` or ``[ val1 val2 ...]`` into a list.

        Handles nested RPN expressions enclosed in quotes or parens, e.g.:
          kvs=("24.9 3 sqrt /" "10 2 *")
          kvar=[(14.4 13.8 / sqr 300 *), (14.4 13.8 / sqr 300 *)]
        """
        # Check if it's an array of enums
        if field_name in class_map.enum_value_maps:
            return DssReader._parse_enum_array(raw_value, field_name, class_map)

        inner = raw_value.strip()

        # Strip the outermost array delimiter (but NOT inner ones — they may be RPN).
        # DSS takes quotes as array delimiters too: kvs="4.8 4.8".
        if len(inner) >= 2 and (inner[0] in "([" and inner[-1] in ")]" or inner[0] in "'\"" and inner[-1] == inner[0]):
            inner = inner[1:-1].strip()

        # Extract elements: quoted strings and paren-groups are kept intact for RPN eval
        elements: list[str] = []
        i = 0
        current: list[str] = []
        depth = 0
        in_quote: str | None = None
        while i < len(inner):
            ch = inner[i]
            if in_quote:
                current.append(ch)
                if ch == in_quote:
                    in_quote = None
                    elements.append("".join(current))
                    current = []
            elif ch in ('"', "'"):
                if current:
                    # flush any pending plain token
                    tok = "".join(current).strip().replace("|", " ")
                    if tok:
                        for p in re.split(r"[,\s]+", tok):
                            if p:
                                elements.append(p)
                    current = []
                in_quote = ch
                current = [ch]
            elif ch in "([":
                depth += 1
                current.append(ch)
            elif ch in ")]":
                depth = max(0, depth - 1)
                current.append(ch)
                if depth == 0:
                    elements.append("".join(current))
                    current = []
            elif ch in ", \t|" and depth == 0:
                if current:
                    tok = "".join(current).strip()
                    if tok:
                        elements.append(tok)
                    current = []
            else:
                current.append(ch)
            i += 1
        if current:
            tok = "".join(current).strip()
            if tok:
                elements.append(tok)

        if not elements:
            return []

        # Names (buses, wires, cables) stay text: "634" is a bus, not 634.0
        if list[str] in get_args(_get_field_type(schema_class, field_name)):
            return [_strip_quotes(elem) for elem in elements]

        # Evaluate each element (RPN or plain)
        results: list[Any] = []
        for elem in elements:
            evaluated = _try_eval_rpn(elem)
            # Strip quotes from plain string results
            if len(evaluated) >= 2 and evaluated[0] in ('"', "'") and evaluated[-1] == evaluated[0]:
                evaluated = evaluated[1:-1]
            results.append(float(evaluated))  # a numeric array; name arrays (list[str]) returned above

        return results

    @staticmethod
    def _parse_enum_array(
        raw_value: str, field_name: str, class_map: DssClassMap
    ) -> list:
        """Parse an array of enum values."""
        inner = raw_value.strip()
        for ch in "[]()'\"":  # brackets, parens and quotes all delimit DSS arrays
            inner = inner.replace(ch, "")

        parts = re.split(r"[,\s]+", inner.strip())
        parts = [p.strip() for p in parts if p.strip()]

        enum_map = class_map.enum_value_maps[field_name]
        result = []
        for p in parts:
            member = enum_map.get(p.lower())
            if member is None:
                raise ValueError(f"{p!r} is not one of {sorted(enum_map)}")
            result.append(member)
        return result


# ---------------------------------------------------------------------------
# Helpers (module-level)
# ---------------------------------------------------------------------------

_UNSET = (None, [], "")


@functools.cache
def dss_defaults(schema_class: type) -> dict[str, Any]:
    """The schema's ``dss_default`` values, typed as the reader types deck text (``int(1)`` on an enum slot
    is that enum's DSS code 1). Mappers pass this to ``cimhub_core.cimtbl.fill_defaults`` (DSS-6)."""
    class_map = get_class_map(schema_class)
    return {slot: DssReader._convert_value(str(value).lower() if isinstance(value, bool) else str(value),
                                           slot, schema_class, class_map)
            for slot, value in schema_defaults(schema_class, "dss_default").items()}

#: ``mult=(file=shape.csv)``: an array read from a text file, one value per line (the first column).
_FILE_ARRAY = re.compile(r"^[(\[]\s*file\s*=\s*([^)\]]+)[)\]]$", re.IGNORECASE)


def _read_array_file(path: Path) -> str:
    """The values of a ``file=`` array as DSS array text, ``[v1 v2 ...]``."""
    path = _resolve_file_case_insensitive(path)
    values = [line.replace(",", " ").split()[0] for line in path.read_text(encoding="utf-8").splitlines()
              if line.strip()]
    return "[" + " ".join(values) + "]"


def _inherit(obj: Any, source: Any) -> None:
    """``like=``: copy every slot ``obj`` leaves unset from ``source``, defined earlier in the deck."""
    if source is None:
        raise ValueError(f"like={obj.like!r}: no object of that name is defined before it")
    for field in dc_fields(obj):
        if field.name not in ("name", "like") and getattr(obj, field.name) in _UNSET:
            setattr(obj, field.name, getattr(source, field.name))


def _batch_edit(bucket: dict[str, Any], pattern: str, values: dict[str, Any]) -> None:
    """``BatchEdit``: set ``values`` on every object whose name ``pattern`` matches."""
    regex = re.compile(pattern, re.IGNORECASE)
    matched = [obj for name, obj in bucket.items() if regex.search(name)]
    if not matched:
        raise ValueError(f"BatchEdit pattern {pattern!r} matches no object")
    for obj in matched:
        for field_name, value in values.items():
            setattr(obj, field_name, value)

def _eval_rpn(expr: str) -> float:
    """Evaluate an OpenDSS RPN expression string and return a float.

    Operators: + - * / ^
    Functions: sqrt sqr inv ln exp log10 sin cos tan asin acos atan atan2
               rollup rolldn swap
    Constants: pi
    Stack is unlimited; X = top, Y = second from top.

    Raises ValueError if the expression cannot be evaluated.
    """
    import math as _math

    tokens = expr.replace(",", " ").split()
    stack: list[float] = []

    for tok in tokens:
        tl = tok.lower()
        # Constants
        if tl == "pi":
            stack.append(_math.pi)
            continue
        # Operators (binary)
        if tl in ("+", "-", "*", "/", "^"):
            if len(stack) < 2:
                raise ValueError(f"RPN stack underflow on '{tok}'")
            x = stack.pop()
            y = stack.pop()
            if tl == "+":
                stack.append(y + x)
            elif tl == "-":
                stack.append(y - x)
            elif tl == "*":
                stack.append(y * x)
            elif tl == "/":
                if x == 0:
                    raise ValueError("RPN division by zero")
                stack.append(y / x)
            elif tl == "^":
                stack.append(y ** x)
            continue
        # Unary functions
        if tl in ("sqrt", "sqr", "inv", "ln", "exp", "log10",
                  "sin", "cos", "tan", "asin", "acos", "atan"):
            if not stack:
                raise ValueError(f"RPN stack underflow on '{tok}'")
            x = stack.pop()
            if tl == "sqrt":
                stack.append(_math.sqrt(x))
            elif tl == "sqr":
                stack.append(x * x)
            elif tl == "inv":
                if x == 0:
                    raise ValueError("RPN inv of zero")
                stack.append(1.0 / x)
            elif tl == "ln":
                stack.append(_math.log(x))
            elif tl == "exp":
                stack.append(_math.exp(x))
            elif tl == "log10":
                stack.append(_math.log10(x))
            elif tl == "sin":
                stack.append(_math.sin(_math.radians(x)))
            elif tl == "cos":
                stack.append(_math.cos(_math.radians(x)))
            elif tl == "tan":
                stack.append(_math.tan(_math.radians(x)))
            elif tl == "asin":
                stack.append(_math.degrees(_math.asin(x)))
            elif tl == "acos":
                stack.append(_math.degrees(_math.acos(x)))
            elif tl == "atan":
                stack.append(_math.degrees(_math.atan(x)))
            continue
        # atan2 needs two args
        if tl == "atan2":
            if len(stack) < 2:
                raise ValueError("RPN stack underflow on 'atan2'")
            x = stack.pop()
            y = stack.pop()
            stack.append(_math.degrees(_math.atan2(y, x)))
            continue
        # Stack manipulation
        if tl == "rollup":
            if stack:
                stack.insert(0, stack.pop())
            continue
        if tl == "rolldn":
            if stack:
                stack.append(stack.pop(0))
            continue
        if tl == "swap":
            if len(stack) >= 2:
                stack[-1], stack[-2] = stack[-2], stack[-1]
            continue
        # Otherwise must be a number
        stack.append(float(tok))

    if not stack:
        raise ValueError("RPN expression produced empty stack")
    return stack[-1]


_RPN_OPERATORS = frozenset({
    "+", "-", "*", "/", "^",
    "sqrt", "sqr", "inv", "ln", "exp", "log10",
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "rollup", "rolldn", "swap", "pi",
})


def _try_eval_rpn(val: str) -> str:
    """If *val* looks like an RPN expression (enclosed in parens/quotes),
    evaluate it and return the result as a string.  Otherwise return *val*
    unchanged.

    Handles:
      - ``(.5 1000 /)``         → ``"0.0005"``
      - ``"24.9 3 sqrt /"``     → ``"14.375..."``
      - plain numbers / strings → returned as-is

    DSS array literals like ``(115, 69)`` or ``(wye delta)`` are NOT
    evaluated — they are returned unchanged so downstream array parsers
    can split them correctly.
    """
    s = val.strip()
    # Detect delimiters that signal RPN (parens and quotes only — NOT square
    # brackets, which are DSS array delimiters)
    pairs = {'"': '"', "'": "'", "(": ")"}
    if not s:
        return val
    opener = s[0]
    closer = pairs.get(opener)
    if closer is None or not s.endswith(closer):
        return val
    inner = s[1:-1].strip()
    # If it looks like a plain number (possibly with sign/decimal/exponent),
    # don't try RPN — fall through to normal parsing
    try:
        float(inner)
        return inner if opener == "(" else val  # (122) is 122; a quoted number keeps its quotes for stripping
    except ValueError:
        pass
    # Require at least one RPN operator/function token.  If the expression
    # contains only numbers (and commas/whitespace), it is a DSS array literal
    # like ``kvs=(115, 69)`` — NOT an RPN expression.  Evaluating it as RPN
    # would push all numbers onto the stack and return only the last one.
    inner_tokens = inner.replace(",", " ").split()
    if not any(t.lower() in _RPN_OPERATORS for t in inner_tokens):
        return val  # No operators → DSS array literal, return unchanged
    # Try RPN evaluation
    try:
        result = _eval_rpn(inner)
        return str(result)
    except (ValueError, IndexError):
        return val  # not valid RPN; return original


def _extract_winding_arrays(raw_text: str) -> dict[str, str]:
    """Parse per-winding transformer params into array-form params.

    OpenDSS supports specifying transformer windings as repeated ``wdg=N bus=X
    kv=Y kva=Z ...`` blocks (typically via ``~`` continuation lines merged into
    one text string).  This function scans the merged text, splits it on
    ``wdg=`` boundaries, and returns array-form params like
    ``{"buses": "[bus1 bus2]", "kVs": "[kv1 kv2]", ...}`` suitable for the
    standard param-to-field mapping.
    """
    import re as _re

    # Split on wdg= boundaries (case-insensitive)
    blocks = _re.split(r'(?i)\bwdg\s*=', raw_text)
    if len(blocks) < 2:
        return {}

    # Each block after the split starts with the winding number followed by
    # the winding's key=value params.  Parse each block independently.
    winding_data: dict[int, dict[str, str]] = {}
    for block in blocks[1:]:
        # First token is the winding number
        parts = block.strip().split(None, 1)
        if not parts:
            continue
        try:
            wdg_num = int(parts[0])
        except ValueError:
            continue
        wdg_text = parts[1] if len(parts) > 1 else ""

        # Parse key=value pairs in this block (stop at next wdg= if any)
        wdg_params: dict[str, str] = {}
        # Simple scan: tokenise by whitespace, handle brackets
        depth = 0
        tokens: list[str] = []
        cur: list[str] = []
        for ch in wdg_text:
            if ch in '([':
                depth += 1
                cur.append(ch)
            elif ch in ')]':
                depth = max(0, depth - 1)
                cur.append(ch)
            elif ch in ' \t' and depth == 0:
                if cur:
                    tokens.append(''.join(cur))
                    cur = []
            else:
                cur.append(ch)
        if cur:
            tokens.append(''.join(cur))

        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if '=' in tok:
                key, _, val = tok.partition('=')
                key = key.strip()
                if not key and i > 0:
                    key = tokens[i - 1]
                if val:
                    wdg_params[key.lower()] = val
                else:
                    # value is next token
                    if i + 1 < len(tokens):
                        wdg_params[key.lower()] = tokens[i + 1]
                        i += 1
            elif tok == '=':
                # key was previous token, value is next
                if i > 0 and i + 1 < len(tokens):
                    wdg_params[tokens[i - 1].lower()] = tokens[i + 1]
                    i += 1
            i += 1

        winding_data[wdg_num] = wdg_params

    if not winding_data:
        return {}

    # Sort by winding number and assemble arrays
    sorted_wnds = sorted(winding_data.keys())
    buses = [winding_data[w].get('bus', '') for w in sorted_wnds]
    kvs = [winding_data[w].get('kv', '') for w in sorted_wnds]
    kvas = [winding_data[w].get('kva', '') for w in sorted_wnds]
    conns = [winding_data[w].get('conn', '') for w in sorted_wnds]
    taps = [winding_data[w].get('tap', '') for w in sorted_wnds]
    pct_rs = [winding_data[w].get('%r', '') for w in sorted_wnds]

    result: dict[str, str] = {}

    # Rneut/Xneut are per-winding but the schema holds one scalar pair plus the
    # "wdg" selector, so carry the first winding that sets either and record which
    # winding it came from. Without "wdg" the importer would fall back to the last
    # winding (what OpenDSS does for the array form), which is the wrong one here.
    for wdg_num in sorted_wnds:
        wdg_params = winding_data[wdg_num]
        if not (wdg_params.get('rneut') or wdg_params.get('xneut')):
            continue
        result['wdg'] = str(wdg_num)
        if wdg_params.get('rneut'):
            result['Rneut'] = wdg_params['rneut']
        if wdg_params.get('xneut'):
            result['Xneut'] = wdg_params['xneut']
        break

    if any(buses):
        result['buses'] = '[' + ' '.join(buses) + ']'
    if any(kvs):
        result['kVs'] = '[' + ' '.join(kvs) + ']'
    if any(kvas):
        result['kVAs'] = '[' + ' '.join(kvas) + ']'
    if any(c for c in conns):
        result['conns'] = '[' + ' '.join(conns) + ']'
    if any(t for t in taps if t):
        result['taps'] = '[' + ' '.join(t if t else '1.0' for t in taps) + ']'
    if any(pct_rs):
        result['pct_Rs'] = '[' + ' '.join(pct_rs) + ']'
    return result


def _extract_linegeometry_arrays(raw_text: str) -> dict[str, str]:
    """Parse per-conductor LineGeometry params into array-form params.

    OpenDSS per-conductor syntax uses ``cond=N wire=X x=... h=... units=...``
    blocks (via ``~`` continuation lines merged into one text string).
    This function splits on ``cond=`` boundaries, accumulates positions
    and cable references into arrays, and returns them as array-form params
    suitable for the standard field mapping::

        {"xs": "[x1 x2 x3]", "hs": "[h1 h2 h3]",
         "cncables": "[cn1 cn2 cn3]", "wires": "[w1 w2]", ...}

    These correspond to the ``xs``, ``hs``, ``cncables``, ``tscables``, and
    ``wires`` multivalued fields on the Linegeometry schema.
    """
    import re as _re

    # Split on cond= boundaries (case-insensitive)
    blocks = _re.split(r'(?i)\bcond\s*=', raw_text)
    if len(blocks) < 2:
        return {}

    cond_data: dict[int, dict[str, str]] = {}
    units_val = ''
    for block in blocks[1:]:
        parts = block.strip().split(None, 1)
        if not parts:
            continue
        try:
            cond_num = int(parts[0])
        except ValueError:
            continue
        cond_text = parts[1] if len(parts) > 1 else ""

        # Simple key=value extraction for this conductor block
        cond_params: dict[str, str] = {}
        depth = 0
        tokens: list[str] = []
        cur: list[str] = []
        for ch in cond_text:
            if ch in '([':
                depth += 1
                cur.append(ch)
            elif ch in ')]':
                depth = max(0, depth - 1)
                cur.append(ch)
            elif ch in ' \t' and depth == 0:
                if cur:
                    tokens.append(''.join(cur))
                    cur = []
            else:
                cur.append(ch)
        if cur:
            tokens.append(''.join(cur))

        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if '=' in tok:
                key, _, val = tok.partition('=')
                key = key.strip().lower()
                if not key and i > 0:
                    key = tokens[i - 1].lower()
                if val:
                    cond_params[key] = val
                elif i + 1 < len(tokens):
                    cond_params[key] = tokens[i + 1]
                    i += 1
            i += 1

        cond_data[cond_num] = cond_params
        if 'units' in cond_params:
            units_val = cond_params['units']

    if not cond_data:
        return {}

    sorted_conds = sorted(cond_data.keys())
    xs = [cond_data[c].get('x', '') for c in sorted_conds]
    hs = [cond_data[c].get('h', '') for c in sorted_conds]
    wires = [cond_data[c].get('wire', '') for c in sorted_conds]
    cncables = [cond_data[c].get('cncable', '') for c in sorted_conds]
    tscables = [cond_data[c].get('tscable', '') for c in sorted_conds]

    # NOTE: a geometry may mix conductor kinds -- IEEE13's LineGeometry.607 is
    # `cond=1 tscable=TS_1/0` then `cond=2 wire=CU_1/0`. OpenDSS array syntax has no
    # empty element, so each of the three name arrays below is compacted and the
    # cond-order interleaving between them is not recoverable from the schema
    # object alone. `conductors` is a scalar slot, so there is nowhere to put it.
    # The importer therefore resolves mixed geometries from `conductor_names`,
    # which keeps every conductor in cond order in a single list.
    result: dict[str, str] = {}
    if any(xs):
        result['xs'] = '[' + ' '.join(xs) + ']'
    if any(hs):
        result['hs'] = '[' + ' '.join(hs) + ']'
    # Names in cond order, whichever kind each slot used.
    ordered_names = [
        w or cn or ts for w, cn, ts in zip(wires, cncables, tscables)
    ]
    kinds_used = sum(
        1 for group in (wires, cncables, tscables) if any(group)
    )

    if kinds_used > 1:
        # Mixed assembly: one cond-ordered list, so conductor 1 stays conductor 1.
        # `get_wire_info` resolves each name across all three CIM WireInfo classes,
        # so the DSS array a name arrived in carries no information the importer needs.
        result['wires'] = '[' + ' '.join(n for n in ordered_names if n) + ']'
    else:
        if any(w for w in wires if w):
            result['wires'] = '[' + ' '.join(w for w in wires if w) + ']'
        if any(cn for cn in cncables if cn):
            result['cncables'] = '[' + ' '.join(cn for cn in cncables if cn) + ']'
        if any(ts for ts in tscables if ts):
            result['tscables'] = '[' + ' '.join(ts for ts in tscables if ts) + ']'
    if units_val:
        result['units'] = units_val
    return result


def _strip_quotes(text: str) -> str:
    """``"wire 1"`` -> ``wire 1``; unquoted text is returned unchanged."""
    if len(text) >= 2 and text[0] in ('"', "'") and text[-1] == text[0]:
        return text[1:-1]
    return text


def _strip_comment(line: str) -> str:
    """Remove inline comments (``!`` and ``//``), respecting quoted strings."""
    in_quote = False
    quote_char: str | None = None
    i = 0
    while i < len(line):
        ch = line[i]
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
        elif in_quote and ch == quote_char:
            in_quote = False
        elif not in_quote:
            if ch == "!":
                return line[:i]
            if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                return line[:i]
        i += 1
    return line


def _tokenize_dss(text: str) -> list[str]:
    """Split DSS parameter text on whitespace, respecting quotes and brackets."""
    tokens: list[str] = []
    current: list[str] = []
    in_quote = False
    quote_char: str | None = None
    bracket_depth = 0

    for ch in text:
        if in_quote:
            current.append(ch)
            if ch == quote_char:
                in_quote = False
            continue

        if ch in ('"', "'"):
            in_quote = True
            quote_char = ch
            current.append(ch)
            continue

        if ch in ("[", "("):
            bracket_depth += 1
            current.append(ch)
            continue

        if ch in ("]", ")"):
            bracket_depth = max(0, bracket_depth - 1)
            current.append(ch)
            continue

        if ch in (" ", "\t") and bracket_depth == 0:
            if current:
                tokens.append("".join(current))
                current = []
            continue

        current.append(ch)

    if current:
        tokens.append("".join(current))

    return _join_equals(tokens)


def _join_equals(tokens: list[str]) -> list[str]:
    """DSS allows blanks around ``=``: ``kv= 7.2``, ``kv =7.2`` and ``kv = 7.2`` are ``kv=7.2``."""
    joined: list[str] = []
    for token in tokens:
        if joined and (joined[-1].endswith("=") or token.startswith("=")):
            joined[-1] += token
        else:
            joined.append(token)
    return joined


def _parse_bool(val: str) -> bool:
    """Parse a DSS boolean value."""
    lower = val.strip().lower()
    if lower in ("yes", "true", "y", "t", "1"):
        return True
    if lower in ("no", "false", "n", "f", "0"):
        return False
    raise ValueError(f"Cannot parse '{val}' as boolean")


def _get_field_type(schema_class: type, field_name: str) -> Any:
    """Get the type annotation for a dataclass field."""
    if not is_dataclass(schema_class):
        return str
    for fld in dc_fields(schema_class):
        if fld.name == field_name:
            return fld.type
    return str


def _unwrap_optional(tp: Any) -> Any:
    """Unwrap Optional[X] to X.  Returns None if type is not inspectable."""
    origin = get_origin(tp)
    if origin is Union:
        args = get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
        # Union of multiple types — try to find a concrete scalar
        for a in non_none:
            if a in (int, float, str, bool):
                return a
            name = getattr(a, "__name__", "")
            if name in ("Bool",):
                return a
        return non_none[0] if non_none else None

    # Handle string-form type annotations (from __future__ annotations)
    if isinstance(tp, str):
        tp_lower = tp.lower()
        if "bool" in tp_lower:
            return bool
        if "int" in tp_lower:
            return int
        if "float" in tp_lower:
            return float
        return str

    return tp

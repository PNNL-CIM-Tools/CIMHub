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
from dataclasses import dataclass, field, fields as dc_fields, is_dataclass, replace
from pathlib import Path
from typing import Any, Iterator, Union, get_args, get_origin

import cimhub_opendss.schema.opendss_schema as dss_schema
from cimhub_core import GraphModel
from cimhub_core.base import FormatReader
from cimhub_core.cimtbl import schema_defaults
from cimhub_core.serialization import get_schema_annotations
from cimhub_opendss.dss_name_map import (
    DssClassMap,
    build_type_registry,
    get_class_map,
)

_log = logging.getLogger(__name__)

__all__ = ["DssReader", "DssParseError", "KEPT_OPTIONS", "dss_defaults"]

#: Every OpenDSS ``Set`` option, lowercased, in the engine's order (``test_dss_options_match_the_engine``).
DSS_OPTIONS = (
    "type", "element", "hour", "sec", "year", "frequency", "stepsize", "mode", "random", "number", "time", "class",
    "object", "circuit", "editor", "tolerance", "maxiterations", "h", "loadmodel", "loadmult", "normvminpu",
    "normvmaxpu", "emergvminpu", "emergvmaxpu", "%mean", "%stddev", "ldcurve", "%growth", "genkw", "genpf",
    "capkvar", "addtype", "allowduplicates", "zonelock", "ueweight", "lossweight", "ueregs", "lossregs",
    "voltagebases", "algorithm", "trapezoidal", "autobuslist", "controlmode", "tracecontrol", "genmult",
    "defaultdaily", "defaultyearly", "allocationfactors", "cktmodel", "pricesignal", "pricecurve", "terminal",
    "basefrequency", "harmonics", "maxcontroliter", "bus", "datapath", "keeplist", "reduceoption", "demandinterval",
    "%normal", "diverbose", "casename", "markercode", "nodewidth", "log", "recorder", "overloadreport",
    "voltexceptionreport", "cfactors", "showexport", "numallociterations", "defaultbasefrequency", "markswitches",
    "switchmarkercode", "daisysize", "marktransformers", "transmarkercode", "transmarkersize", "loadshapeclass",
    "earthmodel", "querylog", "markcapacitors", "markregulators", "markpvsystems", "markstorage", "capmarkercode",
    "regmarkercode", "pvmarkercode", "storemarkercode", "capmarkersize", "regmarkersize", "pvmarkersize",
    "storemarkersize", "neglectloady", "markfuses", "fusemarkercode", "fusemarkersize", "markreclosers",
    "reclosermarkercode", "reclosermarkersize", "registryupdate", "markrelays", "relaymarkercode",
    "relaymarkersize", "processtime", "totaltime", "steptime", "sampleenergymeters", "miniterations",
    "dssvisualizationtool", "keepload", "zmag", "seasonrating", "seasonsignal", "linetypes", "eventlogdefault",
    "longlinecorrection", "showreports", "numcpus", "numcores", "numactors", "activeactor", "cpu", "actorprogress",
    "parallel", "concatenatereports", "numanodes",
)

#: ``Set`` options that describe the circuit, kept on the model as ``Options`` (DSS_REWRITE_PLAN.md section 3.4):
#: the engine's option -> its ``Options`` slot.
KEPT_OPTIONS = {"voltagebases": "voltagebases", "defaultbasefrequency": "defaultbasefreq", "earthmodel": "earthmodel"}

#: Every OpenDSS executive command, lowercased, in the engine's order (``test_dss_commands_match_the_engine``).
DSS_COMMANDS = (
    "new", "edit", "more", "m", "~", "select", "save", "show", "solve", "enable", "disable", "plot", "reset",
    "compile", "set", "dump", "open", "close", "//", "redirect", "help", "quit", "?", "next", "panel", "sample",
    "clear", "about", "calcvoltagebases", "setkvbase", "buildy", "get", "init", "export", "fileedit", "voltages",
    "currents", "powers", "seqvoltages", "seqcurrents", "seqpowers", "losses", "phaselosses", "cktlosses",
    "allocateloads", "formedit", "totals", "capacity", "classes", "userclasses", "zsc", "zsc10", "zscrefresh",
    "ysc", "puvoltages", "varvalues", "varnames", "buscoords", "makebuslist", "makeposseq", "reduce", "interpolate",
    "alignfile", "top", "rotate", "vdiff", "summary", "distribute", "di_plot", "comparecases", "yearlycurves", "cd",
    "visualize", "closedi", "doscmd", "estimate", "reconductor", "_initsnap", "_solvenocontrol", "_samplecontrols",
    "_docontrolactions", "_showcontrolqueue", "_solvedirect", "_solvepflow", "addbusmarker", "uuids",
    "setloadandgenkv", "cvrtloadshapes", "nodediff", "rephase", "setbusxy", "updatestorage", "obfuscate",
    "latlongcoords", "batchedit", "pstcalc", "variable", "reprocessbuses", "clearbusmarkers", "relcalc", "var",
    "cleanup", "finishtimestep", "nodelist", "connect", "disconnect", "remove", "calcincmatrix", "calcincmatrix_o",
    "refine_buslevels", "calclaplacian", "exportoverloads", "exportvviolations", "zsc012", "allpceatbus",
    "allpdeatbus", "totalpowers", "giscoords", "clearall", "comhelp", "newactor", "wait", "solveall", "abort",
    "clone",
)

#: Commands that leave the model as it is (solve, report, plot, export, query, UI), which the reader skips.
#: ``setkvbase`` only sets the engine's bus base for reports; BaseVoltage comes from the topology walk. A command
#: in neither this set nor the ones the reader reads changes the model in a way the reader does not follow, so it
#: raises (DSS_REWRITE_PLAN.md section 3.4).
SKIPPED_COMMANDS = frozenset({
    "save", "show", "solve", "plot", "reset", "dump", "help", "quit", "?", "next", "panel", "sample", "about",
    "calcvoltagebases", "setkvbase", "buildy", "get", "init", "export", "fileedit", "voltages", "currents", "powers",
    "seqvoltages", "seqcurrents", "seqpowers", "losses", "phaselosses", "cktlosses", "formedit", "totals",
    "capacity", "classes", "userclasses", "zsc", "zsc10", "zscrefresh", "ysc", "puvoltages", "varvalues", "varnames",
    "makebuslist", "top", "vdiff", "summary", "di_plot", "comparecases", "yearlycurves", "visualize", "closedi",
    "estimate", "_initsnap", "_solvenocontrol", "_samplecontrols", "_docontrolactions", "_showcontrolqueue",
    "_solvedirect", "_solvepflow", "addbusmarker", "clearbusmarkers", "uuids", "nodediff", "pstcalc", "variable",
    "relcalc", "cleanup", "finishtimestep", "nodelist", "calcincmatrix", "calcincmatrix_o", "refine_buslevels",
    "calclaplacian", "exportoverloads", "exportvviolations", "zsc012", "allpceatbus", "allpdeatbus", "totalpowers",
    "comhelp", "wait", "solveall", "abort",
})


def _engine_name(word: str, names: tuple[str, ...]) -> str | None:
    """The one of ``names`` that ``word`` names, as the engine resolves a command or an option: an exact
    (case-insensitive) name wins; otherwise the first in ``names`` that ``word`` abbreviates; else ``None`` (also
    for an empty word, which the engine reads as no name: ``Set =5`` raises)."""
    word = word.lower()
    if not word:
        return None
    if word in names:
        return word
    return next((name for name in names if name.startswith(word)), None)


def dss_command(word: str) -> str | None:
    """The DSS command ``word`` names, lowercased, or ``None`` (``CalcV`` is ``calcvoltagebases``, ``o`` is
    ``open``)."""
    return _engine_name(word, DSS_COMMANDS)


def dss_option(word: str) -> str | None:
    """The ``Set`` option ``word`` names, lowercased, or ``None`` (``defaultbasefreq`` is ``defaultbasefrequency``,
    ``e`` is ``element``)."""
    return _engine_name(word, DSS_OPTIONS)


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

    cmd: str  # "new", "edit", "batchedit", "set", "clear", "open", "close", "buscoords", "latlongcoords"
    element_type: str | None  # "Load", "Transformer" (original case)
    element_name: str | None  # "671", "sub3"
    params: list[tuple[str, str]]  # raw (key, value) in deck order (original-case keys); a key may repeat
    source_file: str  # for error reporting
    line_number: int
    raw_text: str = ""  # full merged text of the command (for per-winding parsing)


def _resolve_file_case_insensitive(path: Path) -> Path:
    """``path`` as the deck's (Windows) author saw it: ``\\`` separates folders, and each folder and the file name
    match case-insensitively. A part that matches nothing leaves the rest as written, so the caller's "not found"
    names the path."""
    resolved = Path(str(path).replace("\\", "/"))
    if resolved.exists():
        return resolved
    current = Path(resolved.anchor)  # "/" for an absolute path, "." for a relative one
    for part in resolved.parts[1:] if resolved.anchor else resolved.parts:
        if not (current / part).exists() and current.is_dir():
            part = next((child.name for child in current.iterdir() if child.name.lower() == part.lower()), part)
        current = current / part
    return current


#: A coordinate row's field separator: a comma (with any spaces around it) or a run of whitespace.
_COORDINATE_FIELDS = re.compile(r"\s*,\s*|\s+")


@dataclass
class DssModel(GraphModel):
    """The records of a deck, and each record's assignment history.

    The engine applies a deck's assignments in order, and for some properties the order decides the value: a
    Generator keeps ``kvar`` as a power factor taken at the kW of that moment, and a Storage's ``State`` picks one of
    the setpoints that ``kW`` sets. A record keeps only the last value of each slot, so the history keeps every
    ``(slot, value)`` the deck assigned, in deck order (``New``, edits, ``BatchEdit``, and the slots ``like=`` copies,
    first). Mappers replay it where the order matters (CIMTBL_MAPPING.md S4b-8).
    """

    history: dict[tuple[type, str], list[tuple[str, Any]]] = field(default_factory=dict, repr=False)

    def assignments(self, record) -> list[tuple[str, Any]]:
        """``(slot, value)`` in the order the deck assigned them to ``record``."""
        return self.history.get((type(record), str(record.name).lower()), [])

    def last_of(self, record, *slots: str) -> str | None:
        """Which of ``slots`` the deck assigned last to ``record`` (``None`` when it assigned none)."""
        last = None
        for slot, _ in self.assignments(record):
            if slot in slots:
                last = slot
        return last


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
        self._model: DssModel | None = None

    # -----------------------------------------------------------------------
    # Public API  (FormatReader interface)
    # -----------------------------------------------------------------------

    def read_all(self) -> DssModel:
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

    @staticmethod
    def _read_buscoords(files: list[tuple[Path, bool]]) -> list:
        """Parse the ``(csv path, geographic)`` files of the BusCoords/LatLongCoords commands, in deck order, into
        Buscoords objects; a bus a later file gives again takes the later row, as in the engine.

        Both directives use a headerless ``BusName, c1, c2`` CSV, but the column
        order differs: ``BusCoords`` is already ``x, y`` while ``LatLongCoords``
        is ``lat, long`` and must be swapped so x is always the horizontal axis.
        The directive decides, not the filename — IEEE13_Assets points a
        ``BusCoords`` directive at a file called ``..._latlon.csv``.

        Fields are separated by a comma or whitespace, as the engine's command
        parser reads them (the IEEE123 files are whitespace-separated). Blank
        lines and ``!``/``//`` comments are skipped; a row whose coordinates
        are not two numbers raises with its file and line (S5-7). A blank name
        (J1) is kept: it names no bus. A referenced file that does not exist
        raises.
        """
        objects: list = []
        for csv_path, geographic in files:
            with open(csv_path, encoding="utf-8-sig") as fh:
                for line_number, line in enumerate(fh, start=1):
                    line = re.split(r"!|//", line, maxsplit=1)[0].strip()
                    if not line:
                        continue
                    parts = _COORDINATE_FIELDS.split(line)
                    try:
                        c1, c2 = float(parts[1]), float(parts[2])
                    except (IndexError, ValueError):
                        raise ValueError(f"{csv_path.name} line {line_number}: {line!r} is not 'bus, x, y'") from None
                    x, y = (c2, c1) if geographic else (c1, c2)  # lat,long -> x=long, y=lat
                    objects.append(dss_schema.Buscoords(name=parts[0].lower(), x=x, y=y, geographic=geographic))
        return objects

    # -----------------------------------------------------------------------
    # File traversal
    # -----------------------------------------------------------------------

    def _parse_master(self, master_path: str | Path) -> None:
        """Parse Master.dss and all redirected files into a command list."""
        self._commands = []
        raw_lines = list(self._read_with_redirects(Path(master_path)))
        joined = self._join_continuation_lines(raw_lines)

        for line, file_path, line_number in joined:
            try:
                cmd = self._parse_command_line(line, str(file_path), line_number)
            except ValueError as e:
                raise DssParseError(f"{e}: {line}", str(file_path), line_number) from e
            if cmd is not None:
                self._commands.append(cmd)

    def _build_graph(self) -> DssModel:
        """Apply the commands in deck order, as DSS does.

        - ``New`` creates the object. ``like=`` first copies every slot the command leaves unset from the
          named object of the same class, which must already exist.
        - A second ``New`` of an existing object redefines it: DSS applies it as an edit, and so does the
          reader, with one warning per object.
        - ``Edit`` (and ``Class.name.property=value``) changes an object that must already exist.
        - ``BatchEdit Class.<regex>`` changes every object of the class whose name the regular expression
          matches (case-insensitive search, as DSS does); it must match at least one.
        - ``Set`` keeps the circuit options in ``KEPT_OPTIONS`` on one ``Options`` object. The other options
          are solution settings (``mode``, ``controlmode``, ...) and are not part of the model, except
          ``basefrequency``, which raises (``_options``).
        - ``Open Class.name [terminal]`` adds ``Class.name terminal`` to ``Options.open_terminals``; ``Close``
          removes it. The object must already exist.
        - ``BusCoords`` / ``LatLongCoords`` read their files in deck order (``_read_buscoords``).
        - ``Clear`` discards everything defined before it, coordinates included, as in DSS (a deck may build,
          solve and rebuild).
        - ``New Circuit.<name>`` is ``New Vsource.source``, as in DSS; ``Options.circuit`` keeps the name.
          A second ``New Circuit`` raises: a deck is one circuit.

        Names are case-insensitive, as in DSS; an object keeps the spelling of its first ``New``.
        """
        types = build_type_registry()
        graph: dict[type, dict[str, Any]] = {}
        spelled: dict[tuple[type, str], str] = {}  # (class, lowered name) -> name as first written
        redefined: set[tuple[type, str]] = set()
        options: dict[str, Any] = {}
        history: dict[tuple[type, str], list[tuple[str, Any]]] = {}
        coordinate_files: list[tuple[Path, bool]] = []
        for cmd in self._commands:
            if cmd.cmd == "clear":
                graph, spelled, redefined, options, history, coordinate_files = {}, {}, set(), {}, {}, []
                continue
            if cmd.cmd in ("buscoords", "latlongcoords"):
                [(_, csv_path)] = cmd.params
                coordinate_files.append((Path(csv_path), cmd.cmd == "latlongcoords"))
                continue
            try:
                if cmd.cmd == "set":
                    options.update(self._options(cmd))
                    continue
                if cmd.cmd in ("open", "close"):
                    _open_or_close(options.setdefault("open_terminals", []), cmd, types, spelled)
                    continue
                if cmd.element_type.lower() == "circuit":
                    cmd = self._circuit(cmd, options)
                schema_class = types.get(cmd.element_type.lower())
                if schema_class is None:
                    raise ValueError(f"unknown DSS class {cmd.element_type!r}")
                bucket = graph.setdefault(schema_class, {})
                assigned = self._values(cmd, schema_class)
                values = dict(assigned)
                if cmd.cmd == "batchedit":
                    for obj in _batch_edit(bucket, cmd.element_name, values):
                        history[(schema_class, str(obj.name).lower())].extend(assigned)
                    continue
                key = (schema_class, cmd.element_name.lower())
                if cmd.cmd == "new" and key not in spelled:
                    obj = schema_class(name=cmd.element_name, **values)
                    inherited = []
                    if getattr(obj, "like", None):
                        source_key = (schema_class, str(obj.like).lower())
                        _inherit(obj, bucket.get(spelled.get(source_key, "")))
                        inherited = history[source_key]  # like= copies every slot, so it replays all of them
                    bucket[cmd.element_name] = obj
                    spelled[key] = cmd.element_name
                    history[key] = [*inherited, *assigned]
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
                history[key].extend(assigned)
            except (ValueError, TypeError) as e:
                raise DssParseError(f"{cmd.element_type}.{cmd.element_name}: {e}",
                                    cmd.source_file, cmd.line_number) from e

        if options:
            graph[dss_schema.Options] = {"options": dss_schema.Options(name="options", **options)}
        for bc in self._read_buscoords(coordinate_files):
            graph.setdefault(dss_schema.Buscoords, {})[str(bc.name)] = bc
        return DssModel(graph=graph, history=history)

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
        """The kept circuit options a ``Set`` command gives, converted like any property. An option name resolves
        as the engine resolves it (``dss_option``: ``Set voltagebase=`` is ``voltagebases``); a name that is no
        option raises."""
        class_map = get_class_map(dss_schema.Options)
        kept = {}
        for name, raw in cmd.params:
            option = dss_option(name)
            if option is None:
                raise DssParseError(f"Set {name}: no DSS option has that name", cmd.source_file, cmd.line_number)
            if option == "basefrequency":
                # the engine applies it only to objects defined after it (and to the solution), so a deck that sets
                # it can hold two base frequencies; the model has one
                raise DssParseError(f"Set {name}: not read, since objects defined before it keep the old base "
                                    "frequency; set defaultbasefreq before New Circuit", cmd.source_file,
                                    cmd.line_number)
            if option in KEPT_OPTIONS:
                slot = KEPT_OPTIONS[option]
                kept[slot] = self._convert_value(raw, slot, dss_schema.Options, class_map)
        return kept

    def _read_with_redirects(
        self, master_path: Path
    ) -> Iterator[tuple[str, Path, int]]:
        """Read DSS files, following ``Redirect`` / ``Compile`` into each target where it is named.

        Yields ``(stripped_line, file_path, line_number)`` tuples. A target resolves against the folder of the
        file that names it, as in the engine. A file that redirects into one still being read raises (a cycle);
        one file read twice side by side does not. A block comment starts on a line that begins with ``/*`` and
        ends on the line that holds ``*/``; the engine skips both lines whole, and so does this.
        """
        reading: list[Path] = []  # the files being read, outermost first

        def _process_file(file_path: Path) -> Iterator[tuple[str, Path, int]]:
            reading.append(file_path.resolve())
            with open(file_path, "r", encoding="utf-8-sig") as fh:
                in_block_comment = False
                for line_num, raw_line in enumerate(fh, start=1):
                    if in_block_comment or raw_line.startswith("/*"):
                        in_block_comment = "*/" not in raw_line
                        continue
                    line = _strip_comment(raw_line).strip()
                    if not line:
                        continue
                    word, rest = (line.split(None, 1) + [""])[:2]
                    command = dss_command(word)
                    if command not in ("redirect", "compile"):
                        yield line, file_path, line_num
                        continue
                    target_name = _strip_delimiters(rest.strip())
                    if not target_name:
                        raise DssParseError(f"{command} needs a file path", str(file_path), line_num)
                    target = _resolve_file_case_insensitive(file_path.parent / target_name)
                    if not target.exists():
                        raise DssParseError(f"Redirect target not found: {target}", str(file_path), line_num)
                    if target.resolve() in reading:
                        raise DssParseError(f"Redirect cycle: {target} is already being read", str(file_path),
                                            line_num)
                    yield from _process_file(target)
            reading.pop()

        yield from _process_file(_resolve_file_case_insensitive(master_path))

    # -----------------------------------------------------------------------
    # Continuation-line joining
    # -----------------------------------------------------------------------

    @staticmethod
    def _join_continuation_lines(
        raw_lines: list[tuple[str, Path, int]],
    ) -> list[tuple[str, Path, int]]:
        """Merge ``~`` (and ``More``, ``M``) continuation lines with the element they extend.

        In OpenDSS a ``~`` continues the most recent ``New``/``Edit`` element
        command (or ``Class.name.property=value`` edit; none after a ``Clear``),
        even when ``set`` commands, comments, or blank lines appear in
        between (comments/blanks are already stripped upstream). Appending to the
        immediate predecessor would misattach ``~`` params to an intervening
        ``set`` command — e.g. a ``New Circuit`` whose ``~ pu=1.05`` line follows
        a couple of ``set`` commands. A continuation before any ``New`` or ``Edit`` raises.
        """
        result: list[tuple[str, Path, int]] = []
        last_element_idx: int | None = None

        for line, file_path, line_num in raw_lines:
            first_word, rest = (line.split(None, 1) + [""])[:2]
            if line.startswith("~"):
                continued = line[1:].strip()
            elif dss_command(first_word) in ("more", "m"):
                continued = rest.strip()
            else:
                continued = None
            if continued is None:
                result.append((line, file_path, line_num))
                if dss_command(first_word) in ("new", "edit") or _is_dotted_edit(line):
                    last_element_idx = len(result) - 1
                elif dss_command(first_word) in ("clear", "clearall"):
                    last_element_idx = None
            elif last_element_idx is not None:
                prev_line, prev_file, prev_num = result[last_element_idx]
                result[last_element_idx] = (prev_line + " " + continued, prev_file, prev_num)
            else:
                raise DssParseError(f"{first_word}: a continuation with no New or Edit before it",
                                    str(file_path), line_num)

        return result

    # -----------------------------------------------------------------------
    # Command parsing
    # -----------------------------------------------------------------------

    def _parse_command_line(
        self, line: str, file_path: str, line_number: int
    ) -> DssCommand | None:
        """Route a command line to its parser; ``None`` for a command in ``SKIPPED_COMMANDS``.

        ``Class.name.property=value`` (no command word) is an edit. Any other line must start with a DSS command
        the reader reads or skips; an unknown word (a typo such as ``Reditect``) or a command that changes the
        model in a way the reader does not follow (``Disable``, ``Remove``, ``Select``, ...) raises.
        """
        word, rest = (line.split(None, 1) + [""])[:2]
        command = dss_command(word)
        if _is_dotted_edit(line):
            return self._parse_dotted_edit(line.strip(), file_path, line_number)
        if command in ("new", "edit", "batchedit"):
            return self._parse_new_or_edit(command, rest, file_path, line_number)
        if command == "set":
            return self._parse_set_command(rest, file_path, line_number)
        if command in ("clear", "clearall"):
            return DssCommand("clear", None, None, [], file_path, line_number)
        if command in ("buscoords", "latlongcoords"):
            csv_name = _strip_delimiters(rest.strip())
            if not csv_name:
                raise ValueError(f"{command} needs a file path")
            csv_path = _resolve_file_case_insensitive(Path(file_path).parent / csv_name)
            return DssCommand(command, None, None, [("path", str(csv_path))], file_path, line_number)
        if command in ("open", "close"):
            return self._parse_open_or_close(command, rest, file_path, line_number)
        if command in SKIPPED_COMMANDS:
            return None
        if command is None:
            raise ValueError(f"unknown DSS command {word!r}")
        raise ValueError(f"the {command} command changes the model and is not read")

    @staticmethod
    def _parse_open_or_close(command: str, rest: str, file_path: str, line_number: int) -> DssCommand:
        """``Open Class.name [terminal [conductor]]``; the engine reads the arguments by position, so
        ``terminal=2`` and ``2`` are the same. The terminal defaults to 1; opening one conductor raises."""
        values = [_strip_delimiters(token.split("=", 1)[-1]) for token in _tokenize_dss(rest)]
        if not values or "." not in values[0]:
            raise ValueError(f"{command} needs Class.name")
        element_type, element_name = values[0].split(".", 1)
        terminal = values[1] if len(values) > 1 else "1"
        if len(values) > 2 and values[2] != "0":
            raise ValueError(f"{command} of conductor {values[2]} only is not read (no deck in the sweep does it)")
        return DssCommand(command, element_type, element_name, [("terminal", terminal)], file_path, line_number)

    def _parse_new_or_edit(
        self, cmd: str, rest: str, file_path: str, line_number: int
    ) -> DssCommand:
        """Parse ``New Type.Name params...`` or ``Edit Type.Name params...``."""
        if not rest.strip():
            raise ValueError(f"{cmd} needs Class.name")

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
            param_text = self._preprocess_winding_text(param_text, element_type, element_name)
        params = _resolve_positional(self._param_pairs(param_text), element_type)

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
    ) -> DssCommand:
        """Parse ``Type.Name.Property=Value`` implicit edit syntax.

        Example: ``Transformer.Reg1.Taps=[1.0 1.0625]``
        """
        # Split at first '=' to get the dotted path and value
        lhs, rhs = line.split("=", 1)
        parts = lhs.strip().split(".")
        element_type = parts[0]
        element_name = parts[1]
        prop_name = ".".join(parts[2:])  # Handle unlikely multi-dot props
        param_text = f"{prop_name}={rhs}"

        if element_type.lower() in ("transformer", "xfmrcode"):
            param_text = self._preprocess_winding_text(param_text, element_type, element_name)
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
    def _parse_params(text: str) -> list[tuple[str, str]]:
        """``Key1=Value1 Key2=Value2 ...`` as ``(key, value)`` in written order; a value with no property name
        raises (``Set`` and the dotted edit name every property)."""
        params = DssReader._param_pairs(text)
        for key, value in params:
            if key is None:
                raise ValueError(f"the value {value!r} names no property")
        return params

    @staticmethod
    def _param_pairs(text: str) -> list[tuple[str | None, str]]:
        """``(key, value)`` in written order; ``key`` is ``None`` for a positional value (no ``name=``).

        Handles bracketed arrays like ``kVs=[115, 4.16, 13.2]`` and
        ``XSCArray=[ 0.00979 0.02491]``.
        """
        pairs: list[tuple[str | None, str]] = []
        if not text or not text.strip():
            return pairs

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
                        pairs.append((current_key, " ".join(current_value_parts)))
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
                    pairs.append((current_key, " ".join(current_value_parts)))
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
                    pairs.append((current_key, value))
                    current_key = None
                    current_value_parts = []
            elif current_key is None:
                # A value with no name: DSS gives it to the property after the last one named
                opens = token.count("[") + token.count("(") + token.count("{")
                closes = token.count("]") + token.count(")") + token.count("}")
                if opens != closes:
                    raise ValueError(f"unbalanced brackets in positional value {token!r}")
                pairs.append((None, token))
            else:
                # Continuation of previous value (e.g. space-separated items
                # outside brackets, which can happen in some DSS variants)
                current_value_parts.append(token)

        # Flush last param
        if current_key is not None:
            pairs.append((current_key, " ".join(current_value_parts)))

        return pairs

    # -----------------------------------------------------------------------
    # Instance construction
    # -----------------------------------------------------------------------

    def _values(self, cmd: DssCommand, schema_class: type) -> list[tuple[str, Any]]:
        """``(field, value)`` for the properties a ``New`` or ``Edit`` command sets, in deck order.

        Transformer and XfmrCode ``wdg=N`` blocks have become the per-winding arrays (``buses``, ``kVs``, ...)
        and LineGeometry ``cond=N`` blocks the per-conductor arrays (``xs``, ``hs``, ...), so both are only
        accepted on a ``New``: an ``Edit`` would replace whole arrays with one winding's or conductor's values.
        """
        class_map = get_class_map(schema_class)
        params = list(cmd.params)
        lowered = {k.lower() for k, _ in params}
        element_type = cmd.element_type.lower()
        if element_type in ("transformer", "xfmrcode") and "wdg" in lowered and cmd.cmd != "new":
            raise ValueError("per-winding properties (wdg=) on an Edit are not supported")
        if element_type == "linegeometry" and "cond" in lowered:
            if cmd.cmd != "new":
                raise ValueError("per-conductor properties (cond=) on an Edit are not read")
            params += list(_extract_linegeometry_arrays(cmd.raw_text).items())

        values: list[tuple[str, Any]] = []
        for param_name, raw_value in params:
            field_name = class_map.field_for(param_name)
            if field_name == "name":
                continue
            file_ref = _FILE_ARRAY.match(raw_value.strip())
            if file_ref:
                raw_value = _read_array_file(Path(cmd.source_file).parent / file_ref.group(1).strip("\"' "))
            try:
                values.append((field_name, self._convert_value(raw_value, field_name, schema_class, class_map)))
            except ValueError as e:
                raise ValueError(f"{param_name}={raw_value!r}: {e}") from e
        return values

    @staticmethod
    def _preprocess_winding_text(param_text: str, element_type: str, element_name: str) -> str:
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
        #: per-winding values with no array form in DSS: each goes to the active winding's place in its array
        _WDG_VALUE_KEYS = {"rdcohms": "RdcOhms"}

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

        # Walk the tokens in order, as DSS applies them. A per-winding scalar (bus, kV, kVA, conn, tap, %R,
        # RdcOhms) goes to the active winding: the last wdg=, else the last winding an array set (an array sets every
        # winding), else winding 1. On a 2-winding transformer kVA sets both windings (all engine-checked).
        count = next((int(float(_try_eval_rpn(tok.partition("=")[2]))) for tok in merged
                      if tok.partition("=")[0].strip().lower() == "windings"), 2)
        array_keys = {name.lower(): name for name in _WDG_ARRAY_MAP.values()} | {"%rs": "pct_Rs"}
        winding_data: dict[str, list[str]] = {}
        non_winding_tokens: list[str] = []
        scalar_overrides: dict[str, str] = {}
        scalar_neutral_wdg: int | None = None
        active = 1

        def put(target: str, number: int, value: str) -> None:
            values = winding_data.setdefault(target, [])
            values.extend([""] * (number - len(values)))
            values[number - 1] = value

        for tok in merged:
            if "=" not in tok:
                non_winding_tokens.append(tok)
                continue
            key, _, value = tok.partition("=")
            key_lower = key.strip().lower()
            if key_lower == "wdg":
                active = int(float(_try_eval_rpn(value)))
                if active < 1:
                    raise ValueError(f"{element_type}.{element_name}: wdg={value}; windings are numbered from 1")
                continue
            # RPN on numbers only: a bus or connection is a name (bus=(1 2 +) is the bus "1 2 +", as in the engine)
            if key_lower in array_keys:
                items = _array_items(value)
                is_name = array_keys[key_lower] in _WDG_NAME_ARRAYS
                winding_data[array_keys[key_lower]] = items if is_name else [_try_eval_rpn(item) for item in items]
                active = max(len(items), 1)
                continue
            if key_lower in _WDG_ARRAY_MAP:
                target = _WDG_ARRAY_MAP[key_lower]
                resolved = value if target in _WDG_NAME_ARRAYS else _try_eval_rpn(value)
                for number in (range(1, 3) if key_lower == "kva" and count == 2 else (active,)):
                    put(target, number, resolved)
            elif key_lower in _WDG_VALUE_KEYS:
                put(_WDG_VALUE_KEYS[key_lower], active, _try_eval_rpn(value))
            elif key_lower in _WDG_SCALAR_KEYS:
                # Rneut/Xneut belong to the active winding; the schema holds one winding's, so it keeps the winding
                # that sets them and emits "wdg=N" alongside so the binding survives. A second winding raises.
                if scalar_neutral_wdg is None:
                    scalar_neutral_wdg = active
                if active != scalar_neutral_wdg:
                    raise ValueError(f"{element_type}.{element_name}: {key.strip()} on winding {active} after "
                                     f"winding {scalar_neutral_wdg}'s neutral; one winding's Rneut/Xneut is mapped")
                scalar_overrides[key.strip()] = value
            else:
                non_winding_tokens.append(f"{key.strip()}={value}")

        defaults = schema_defaults(build_type_registry()[element_type.lower()], "dss_default")
        for array_key, values in winding_data.items():
            values.extend([""] * (count - len(values)) if any(values) else [])
            unset = [number for number, value in enumerate(values, start=1) if value == ""]
            if unset:
                # The array cannot hold an unset winding: it takes the engine's per-winding default, as DSS does
                scalar = _WINDING_SCALAR[array_key]
                if scalar not in defaults:
                    raise ValueError(f"{array_key}: winding {unset} unset while another winding's is set, and "
                                     f"{scalar} has no default")
                _log.warning("%s: winding %s unset while another winding's is set; the DSS default %s=%s",
                             array_key, unset, scalar, defaults[scalar])
                values = [str(defaults[scalar]) if value == "" else value for value in values]
            non_winding_tokens.append(f"{array_key}=[{','.join(values)}]")
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

        # A delimited number is an RPN expression: (2 3 *), {2 3 *}, "2 3 *". Other text only loses its
        # delimiters, as the engine reads it: bus1="pi" is the bus pi, and bus1=(1 2 +) the bus "1 2 +".
        fld_type = _get_field_type(schema_class, field_name)
        is_number = getattr(_unwrap_optional(fld_type), "__name__", None) in ("int", "float")
        if is_number and field_name not in class_map.enum_value_maps:
            val = _try_eval_rpn(val)
        val = _strip_delimiters(val).rstrip(",")  # DSS delimits with commas too: npts='1,' is 1

        if field_name in class_map.enum_value_maps:
            return DssReader._convert_enum(val, field_name, class_map)
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
            return int(float(val))

        if actual_type is float or type_name == "float":
            return float(val)

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

        Handles nested RPN expressions enclosed in quotes, parens or braces, e.g.:
          kvs=("24.9 3 sqrt /" "10 2 *")
          kvar=[(14.4 13.8 / sqr 300 *), (14.4 13.8 / sqr 300 *)]
          mult=[1 {2 3 *}]
        """
        # Check if it's an array of enums
        if field_name in class_map.enum_value_maps:
            return DssReader._parse_enum_array(raw_value, field_name, class_map)

        inner = raw_value.strip()

        # Strip the outermost array delimiter (but NOT inner ones — they may be RPN).
        # DSS takes quotes and braces as array delimiters too: kvs="4.8 4.8", kvs={4.8 4.8}.
        inner = _strip_delimiters(inner).strip()

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
            elif ch in "([{":
                depth += 1
                current.append(ch)
            elif ch in ")]}":
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
            return [_strip_delimiters(elem) for elem in elements]

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
        for ch in "[](){}'\"":  # brackets, parens, braces and quotes all delimit DSS arrays
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
    if not path.exists():
        raise ValueError(f"array file not found: {path}")
    values = [line.replace(",", " ").split()[0] for line in path.read_text(encoding="utf-8").splitlines()
              if line.strip()]
    return "[" + " ".join(values) + "]"


def _inherit(obj: Any, source: Any) -> None:
    """``like=``: copy every slot ``obj`` leaves unset from ``source``, defined earlier in the deck."""
    if source is None:
        raise ValueError(f"like={obj.like!r}: no object of that name is defined before it")
    for slot in dc_fields(obj):
        if slot.name not in ("name", "like") and getattr(obj, slot.name) in _UNSET:
            setattr(obj, slot.name, getattr(source, slot.name))


def _open_or_close(opened: list[str], cmd: DssCommand, types: dict[str, type],
                   spelled: dict[tuple[type, str], str]) -> None:
    """Add (``Open``) or remove (``Close``) the terminal ``Class.name terminal`` on ``opened``."""
    schema_class = types.get(cmd.element_type.lower())
    key = (schema_class, cmd.element_name.lower())
    if key not in spelled:
        raise ValueError(f"{cmd.cmd.capitalize()} of an object no New defines")
    [(_, number)] = cmd.params
    if int(number) < 1:
        raise ValueError(f"{cmd.cmd.capitalize()} terminal {number} must be 1 or more")
    terminal = f"{schema_class.__name__}.{spelled[key]} {int(number)}"
    if cmd.cmd == "open" and terminal not in opened:
        opened.append(terminal)
    if cmd.cmd == "close" and terminal in opened:
        opened.remove(terminal)


def _batch_edit(bucket: dict[str, Any], pattern: str, values: dict[str, Any]) -> list[Any]:
    """``BatchEdit``: set ``values`` on every object whose name ``pattern`` matches; the objects changed."""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as error:
        raise ValueError(f"BatchEdit pattern {pattern!r} is not a regular expression: {error}") from error
    matched = [obj for name, obj in bucket.items() if regex.search(name)]
    if not matched:
        raise ValueError(f"BatchEdit pattern {pattern!r} matches no object")
    for obj in matched:
        for field_name, value in values.items():
            setattr(obj, field_name, value)
    return matched


def _eval_rpn(expr: str) -> float:
    """Evaluate an OpenDSS RPN expression string and return a float.

    Operators: + - * / ^
    Functions: sqrt sqr inv ln exp log10 sin cos tan asin acos atan atan2 swap
    Constants: pi
    Stack is unlimited; X = top, Y = second from top. ``rollup`` and ``rolldn`` raise: the engine's stack has a
    fixed depth that this one does not model, and no deck in the sweep uses them.

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
        if tl in ("rollup", "rolldn"):
            raise ValueError(f"RPN {tl} is not supported")
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
    """If *val* looks like an RPN expression (enclosed in parens, braces or quotes),
    evaluate it and return the result as a string.  Otherwise return *val*
    unchanged. An expression that does not evaluate (``(1 +)``) raises.

    Handles:
      - ``(.5 1000 /)``         → ``"0.0005"``
      - ``{2 3 *}``             → ``"6.0"``
      - ``"24.9 3 sqrt /"``     → ``"14.375..."``
      - plain numbers / strings → returned as-is

    DSS array literals like ``(115, 69)`` or ``(wye delta)`` are NOT
    evaluated — they are returned unchanged so downstream array parsers
    can split them correctly.
    """
    s = val.strip()
    # Detect delimiters that signal RPN (parens, braces and quotes only — NOT square
    # brackets, which are DSS array delimiters)
    pairs = {'"': '"', "'": "'", "(": ")", "{": "}"}
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
        return inner if opener in "({" else val  # (122) is 122; a quoted number keeps its quotes for stripping
    except ValueError:
        pass
    # Require at least one RPN operator/function token.  If the expression
    # contains only numbers (and commas/whitespace), it is a DSS array literal
    # like ``kvs=(115, 69)`` — NOT an RPN expression.  Evaluating it as RPN
    # would push all numbers onto the stack and return only the last one.
    inner_tokens = inner.replace(",", " ").split()
    if not any(t.lower() in _RPN_OPERATORS for t in inner_tokens):
        return val  # No operators → DSS array literal, return unchanged
    return str(_eval_rpn(inner))


def _array_items(value: str) -> list[str]:
    """The items of a DSS array value: ``[a b]``, ``(a, b)``, ``{a b}``, ``'a b'``, ``"a b"`` or a bare ``a``."""
    text = _strip_delimiters(value.strip())
    return [item for item in _tokenize_dss(text.replace(",", " ").replace("|", " ")) if item]


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
    # a units= before the first cond= is conductor 1's, and the later ones' until another is given (engine-checked)
    units_val = next((tok.partition("=")[2] for tok in reversed(_tokenize_dss(blocks[0]))
                      if tok.partition("=")[0].strip().lower() == "units"), "")
    block_units: list[str] = []  # each block's unit: its own, else the last given, else DSS's initial ft
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

        cond_data.setdefault(cond_num, {}).update(cond_params)  # cond=1 again adds to conductor 1
        if 'units' in cond_params:
            units_val = cond_params['units']
        block_units.append((units_val or 'ft').lower())

    if not cond_data:
        return {}
    if units_val and len(set(block_units)) > 1:
        raise ValueError(f"the cond= blocks give positions in different units ({', '.join(block_units)}); "
                         "one geometry has one length unit")

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


#: The pairs the engine's parser reads as quotes around one value.
_DELIMITERS = {'"': '"', "'": "'", "(": ")", "[": "]", "{": "}"}


def _strip_delimiters(text: str) -> str:
    """``"wire 1"``, ``(a b)``, ``[a b]`` or ``{a b}`` -> the text inside, as the engine's parser reads one value;
    other text is returned unchanged."""
    if len(text) >= 2 and _DELIMITERS.get(text[0]) == text[-1]:
        return text[1:-1]
    return text


def _is_dotted_edit(line: str) -> bool:
    """``Class.name.property=value``: an edit with no command word."""
    return dss_command(line.split(None, 1)[0]) is None and "=" in line and line.split("=", 1)[0].count(".") >= 2


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


#: The per-winding array of a transformer and the scalar slot whose ``dss_default`` fills an unset winding.
_WINDING_SCALAR = {"buses": "bus", "kVs": "kV", "kVAs": "kVA", "conns": "conn", "taps": "tap", "pct_Rs": "pct_R",
                   "RdcOhms": "RdcOhms"}
#: The per-winding arrays that hold names, which RPN leaves alone.
_WDG_NAME_ARRAYS = ("buses", "conns")
#: Classes whose properties the reader rewrites by winding or conductor block, so a positional value raises.
_BLOCK_CLASSES = ("transformer", "xfmrcode", "autotrans", "linegeometry")


def _resolve_positional(pairs: list[tuple[str | None, str]], element_type: str) -> list[tuple[str, str]]:
    """``(property, value)`` in written order: a value with no name goes to the property after the last one given
    (the first property at the start), in the schema's DSS order, as DSS's parser does."""
    params: list[tuple[str, str]] = []
    schema_class = build_type_registry().get(element_type.lower())
    pointer = 0
    for key, value in pairs:
        if key is not None:
            params.append((key, value))
            if schema_class is not None:
                pointer = _property_order(schema_class).get(get_class_map(schema_class).field_for(key), pointer)
            continue
        if schema_class is None or element_type.lower() in _BLOCK_CLASSES:
            raise ValueError(f"{element_type}: the positional value {value!r} is not read on this class")
        pointer += 1
        by_order = {order: slot for slot, order in _property_order(schema_class).items()}
        if pointer not in by_order:
            raise ValueError(f"{element_type}: positional value {value!r} is past the last property")
        params.append((by_order[pointer], value))
    return params


@functools.cache
def _property_order(schema_class: type) -> dict[str, int]:
    """``{field: DSS property index}`` from the schema's ``order`` annotations."""
    return {slot: int(spec["order"]) for slot, spec in get_schema_annotations(schema_class).items()
            if spec.get("order") is not None}


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

        if ch in ("[", "(", "{"):
            bracket_depth += 1
            current.append(ch)
            continue

        if ch in ("]", ")", "}"):
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

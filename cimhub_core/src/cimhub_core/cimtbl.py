"""Native records -> ``.cimtbl`` documents -> CIM: the helpers every importer spoke shares.

A spoke's mappers turn native records into ``cimtables.document`` documents with
:func:`cell`, :func:`mrid` and :func:`lookup`, and classify every native field
with :class:`Field`. :func:`cimtbl_to_cim` writes the documents and builds the
CIM model from the written text, never from the mapper's objects (rewrite plan
invariant I1).

Contract: the ``cimtbl-import-contract`` skill.
"""

from __future__ import annotations

import dataclasses
import functools
import math
import re
import tempfile
import textwrap
from pathlib import Path
from collections.abc import Callable, Iterable
from typing import Literal

import cimtables
from cimgraph.models import GraphModel as CIMGraphModel
from cimtables.document import Column, Document, DocumentSet, Import, write_documents
from linkml_runtime.linkml_model.meta import PermissibleValue
from linkml_runtime.utils.enumerations import EnumDefinitionImpl

from cimhub_core.serialization import get_schema_annotations

__all__ = [
    "CIM_PROFILE",
    "Field",
    "cell",
    "mrid",
    "phases_cell",
    "BALANCED_PHASES",
    "lookup",
    "copied_columns",
    "untranscribed_values",
    "untranscribed_names",
    "parse_default",
    "schema_defaults",
    "fill_defaults",
    "field_names",
    "check_fields",
    "fields_table",
    "fields_stub",
    "cimtbl_to_cim",
]

#: The one profile every artifact declares (``Profile = cim18v17``).
CIM_PROFILE = "cim18v17"

FieldKind = Literal["copied", "mapped", "structural", "derived", "untranscribed"]
FIELD_KINDS = ("copied", "mapped", "structural", "derived", "untranscribed")

#: Comment lines wrap here; the formatter adds the leading ``# ``.
_COMMENT_WIDTH = 116


# ---------------------------------------------------------------------------
# Cell text and identity
# ---------------------------------------------------------------------------

def cell(value) -> str | None:
    """A native value as ``.cimtbl`` cell text, verbatim (plan D2).

    ``None`` is a blank cell (unset). Strings are kept exactly as the reader
    produced them, so a reader that keeps the source text (e.g. ``'4.160000'``)
    puts that text in the artifact. A float is written as its ``repr()``: the
    shortest text that reads back to the identical float. No unit conversion and
    no rounding happen here.
    """
    if value is None:
        return None
    if isinstance(value, bool):  # before int: bool is an int
        return "true" if value else "false"
    if isinstance(value, int):
        return str(int(value))
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{value!r} has no .cimtbl cell text")
        return repr(float(value))
    if isinstance(value, str):
        return str(value)  # drops LinkML's str subclasses (LinecodeName, ...)
    if isinstance(value, EnumDefinitionImpl):
        return value.code.text
    if isinstance(value, PermissibleValue):  # how some generated enum slots hold their value
        return value.text
    raise TypeError(f"no .cimtbl cell text for {type(value).__name__} {value!r}; map it in the mapper")


#: A balanced three-phase device's phases: CIM's default when a device has no per-phase children.
BALANCED_PHASES = "ABC"


def phases_cell(phases: str) -> str | None:
    """The ``phases`` cell of a device that is balanced when three-phase (a load, shunt, source, machine, inverter,
    switch): blank for ``ABC``, so cimtables writes no per-phase children and no ``Terminal.phases`` (the OpenDSS CIM
    export's rule), else ``phases``. A line keeps its phases: its ACLineSegmentPhases are the conductor order.
    UPSTREAM_REQUESTS U10 asks CIM-Tables for a balanced form that keeps ``Terminal.phases``."""
    return None if phases == BALANCED_PHASES else phases


def mrid(prefix: str, native_id, *, lowercase: bool = False) -> str:
    """The mRID of an imported object: ``prefix`` + the native ID as written (plan D3).

    ``prefix`` comes from the cimtbl-translate prefix table (``xc_``, ``lc_``, ...).
    Only the OpenDSS spoke passes ``lowercase=True``, because DSS names are
    case-insensitive. Characters are never sanitized: the formatter quotes
    cells holding ``, ( ) #`` (plan I8).
    """
    if native_id is None or not str(native_id).strip():
        raise ValueError(f"{prefix}: the native ID is missing ({native_id!r})")
    text = prefix + str(native_id)
    return text.lower() if lowercase else text


def lookup(table: dict, value, *, slot: str, record_id):
    """``table[value]``; an unmapped value raises with the record, slot and known values."""
    if value in table:
        return table[value]
    known = ", ".join(sorted(str(key) for key in table))
    raise ValueError(f"{record_id}: {slot}={value!r} has no mapping (known: {known})")


# ---------------------------------------------------------------------------
# Field classification (plan I3)
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Field:
    """How one native field reaches CIM.

    kind:
        ``copied``: the value lands unchanged in a column, the same value in every
        row the record produces for that class. ``mapped``: through an enum or
        code table. ``structural``: it decides rows (one record -> several rows,
        a value on one specific row, a row in another file). ``derived``: computed
        by a named, tested function, because CIM has no attribute for the source
        quantity. ``untranscribed``: no CIM home; recorded in the artifact (D5).
    targets:
        For ``copied``: ``(cim_class, column, unit)`` per column it fills, so
        each column and unit is stated once. Builder-native spokes (GDM) name
        ``(builder_method, keyword, unit)`` instead.
    note:
        Free text for the reviewer: the enum table, the formula, the gap.
    """

    kind: FieldKind
    targets: tuple[tuple[str, str, str | None], ...] = ()
    note: str = ""

    def __post_init__(self):
        if self.kind not in FIELD_KINDS:
            raise ValueError(f"Field kind {self.kind!r} is not one of {FIELD_KINDS}")
        if self.kind == "copied" and not self.targets:
            raise ValueError("a copied Field names its targets")


def copied_columns(fields: dict[str, Field], cim_class: str, **unit_words: str) -> list[tuple[str, Column]]:
    """``(slot, Column)`` for every copied target on ``cim_class``, in ``fields`` order.

    A target unit may name a per-record word, ``"ohm/{length}"``; ``unit_words``
    fills it (``length="mi"``). A word left unfilled raises ``KeyError``.

    The mapper writes the columns, then ``cell(getattr(record, slot))`` for each
    pair. A column filled from two slots raises: a value that differs per row
    (end 1's voltage, end 2's voltage) is ``structural``, not ``copied``.
    """
    pairs = []
    for slot, field in fields.items():
        if field.kind != "copied":
            continue
        for target_class, column, unit in field.targets:
            if target_class == cim_class:
                pairs.append((slot, Column(column, unit.format(**unit_words) if unit else None)))
    names = [column.name for _, column in pairs]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise ValueError(f"{cim_class} columns copied from more than one slot: {repeated}")
    return pairs


def _comment_text(value) -> str:
    if isinstance(value, list):
        return " ".join(cell(item) for item in value)
    return cell(value)


def _wrapped(items: list[str], label: str = "untranscribed") -> str:
    return textwrap.fill(f"{label}: " + ", ".join(items), width=_COMMENT_WIDTH,
                         break_long_words=False, break_on_hyphens=False)


def _is_unset(value) -> bool:
    return value is None or value == "" or value == []


def untranscribed_values(fields: dict[str, Field], record) -> str | None:
    """The D5 catalog record: ``untranscribed: Slot=value, ...`` for one record's non-empty values.

    Written as the comment above the record's row, so a reviewer sees every
    source value that has no CIM home. ``None`` when there is nothing to list.
    """
    items = []
    for slot, field in fields.items():
        if field.kind != "untranscribed":
            continue
        value = getattr(record, slot)
        if _is_unset(value):
            continue
        items.append(f"{slot}={_comment_text(value)}")
    return _wrapped(items) if items else None


def untranscribed_names(fields: dict[str, Field]) -> str | None:
    """The D5 instance record: ``untranscribed: Slot, Slot, ...``, once above an instance table."""
    names = [slot for slot, field in fields.items() if field.kind == "untranscribed"]
    return _wrapped(names) if names else None


# ---------------------------------------------------------------------------
# Native defaults (keyword formats: the `linkml-native-schema` skill, rule 5)
# ---------------------------------------------------------------------------

_DEFAULT_EXPRESSION = re.compile(r"^(float|int|integer|string|str)\((.*)\)$")


def parse_default(expression):
    """A LinkML default expression as a Python value.

    ``float(1.0)`` -> 1.0, ``int(3)`` -> 3, ``string(abc)`` -> 'abc', ``"true"`` -> True; any other text
    (an enum value such as ``Deri``) is returned as text.
    """
    if isinstance(expression, (bool, int, float)):
        return expression
    text = str(expression).strip()
    match = _DEFAULT_EXPRESSION.match(text)
    if match:
        kind, inner = match.groups()
        if kind == "float":
            return float(inner)
        if kind in ("int", "integer"):
            return int(inner)
        return inner.strip("\"'")
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    return text


@functools.cache
def schema_defaults(native_cls: type, annotation: str) -> dict[str, object]:
    """``{slot: default}`` from a native schema's ``<fmt>_default`` annotation (``dss_default``)."""
    return {slot: parse_default(spec[annotation]) for slot, spec in get_schema_annotations(native_cls).items()
            if annotation in spec}


def fill_defaults(fields: dict[str, Field], record, defaults: dict[str, object]):
    """``(record, comment)``: the record with every unset slot the mapper reads filled from ``defaults``.

    Untranscribed slots are left alone. The record is a copy (``dataclasses.replace``, so the schema's
    ``__post_init__`` types the defaults); the original is not changed. Attributes set on the record outside its
    fields (a reader's composite ``record.ID``, which ``GraphModel`` keys on) are carried over, because
    ``dataclasses.replace`` drops them. ``comment`` is ``defaulted: slot=value, ...`` for the row comment, or
    ``None`` when nothing was filled.
    """
    filled = {slot: defaults[slot] for slot, field in fields.items()
              if field.kind != "untranscribed" and slot in defaults and _is_unset(getattr(record, slot))}
    if not filled:
        return record, None
    items = [f"{slot}={_comment_text(value)}" for slot, value in filled.items()]
    copy = dataclasses.replace(record, **filled)
    field_names_of_record = {field.name for field in dataclasses.fields(record)}
    for name, value in vars(record).items():
        if name not in field_names_of_record:
            setattr(copy, name, value)
    return copy, _wrapped(items, "defaulted")


def field_names(native_cls: type) -> list[str]:
    """Every field of a native class, in declaration order.

    LinkML dataclasses give their slots (inherited ones included); pydantic
    models (GDM) give ``model_fields``.
    """
    if hasattr(native_cls, "model_fields"):
        return list(native_cls.model_fields)
    if dataclasses.is_dataclass(native_cls):
        return [field.name for field in dataclasses.fields(native_cls)]
    raise TypeError(f"{native_cls!r} is neither a LinkML dataclass nor a pydantic model")


def check_fields(fields: dict[str, Field], native_cls: type) -> None:
    """Raise ``AssertionError`` unless ``fields`` classifies exactly the fields of ``native_cls``.

    The completeness test of every mapper: it fails on a field added by a schema
    regeneration and on a stale entry.
    """
    expected = field_names(native_cls)
    missing = [name for name in expected if name not in fields]
    stale = [name for name in fields if name not in expected]
    if missing or stale:
        raise AssertionError(
            f"{native_cls.__name__} classification: missing {missing}, stale {stale}"
        )


# ---------------------------------------------------------------------------
# Skeletons for the Phase 2 mapping specs
# ---------------------------------------------------------------------------

def _field_types(native_cls: type) -> dict[str, str]:
    if hasattr(native_cls, "model_fields"):
        hints = {name: info.annotation for name, info in native_cls.model_fields.items()}
    else:
        hints = {field.name: field.type for field in dataclasses.fields(native_cls)}
    return {name: hint.__name__ if isinstance(hint, type) else re.sub(r"\b(?:\w+\.)+(\w+)", r"\1", str(hint))
            for name, hint in hints.items()}


def _samples(name: str, records, limit: int) -> list[str]:
    """Up to ``limit`` distinct non-empty values of one field, as short text."""
    seen = []
    for record in records:
        value = getattr(record, name, None)
        if value is None or value == "" or value == []:
            continue
        text = str(value)
        if len(text) > 40:
            text = text[:37] + "..."
        if text not in seen:
            seen.append(text)
        if len(seen) == limit:
            break
    return seen


def _target_text(field: Field) -> str:
    targets = [f"`{cim_class}.{column}`" + (f" ({unit})" if unit else "") for cim_class, column, unit in field.targets]
    return "; ".join(part for part in (", ".join(targets), field.note) if part)


def fields_table(native_cls: type, records=(), *, fields: dict[str, Field] | None = None, limit: int = 3) -> str:
    """A markdown classification table of every field, with sample values from ``records``.

    Without ``fields`` the *kind* and *target* columns are empty, for a Phase 2
    agent to fill, so it classifies the real fields rather than invents them.
    With a mapper's ``FIELDS`` they are filled from it, so the mapping spec can
    be regenerated from the code it describes.
    """
    types = _field_types(native_cls)
    lines = [
        f"| {native_cls.__name__} field | type | samples | kind | target |",
        "|---|---|---|---|---|",
    ]
    for name in field_names(native_cls):
        samples = ", ".join(f"`{text}`" for text in _samples(name, records, limit))
        field = (fields or {}).get(name)
        kind, target = (field.kind, _target_text(field)) if field else ("", "")
        lines.append(f"| `{name}` | `{types[name]}` | {samples} | {kind} | {target} |")
    return "\n".join(lines) + "\n"


def fields_stub(native_cls: type, records=(), *, limit: int = 3) -> str:
    """Python source for a ``FIELDS`` dict with one unclassified entry per field.

    Every entry has kind ``'TODO'``, which :class:`Field` rejects, so the stub
    cannot be imported until each field is classified.
    """
    lines = [f"FIELDS = {{  # {native_cls.__name__}"]
    for name in field_names(native_cls):
        samples = ", ".join(_samples(name, records, limit))
        lines.append(f"    {name!r}: Field('TODO', note={samples!r}),")
    lines.append("}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Documents -> CIM
# ---------------------------------------------------------------------------

def cimtbl_to_cim(documents: DocumentSet, *, model_cls: type | None = None, network=None,
                  artifact_dir: str | Path | None = None,
                  bound_parts: Callable[[CIMGraphModel], Iterable[Document]] | None = None):
    """Write ``documents`` and build CIM from the written files (plan I1).

    The files go to ``artifact_dir`` (the human audit artifact), or to a
    temporary directory when it is ``None``, so an in-memory import and an
    artifact import cannot differ.

    Without ``network``, ``cimtables.load_model`` builds a new model: its type
    comes from the master (one Feeder -> FeederModel, ...) or is ``model_cls``
    (``BusBranchModel``). With ``network``, the rows are bound onto it and it is
    returned; that is how several native models merge into one network, and
    ``model_cls`` does not apply.

    ``bound_parts(network)`` maps the parts that read what binding made, such as
    the Terminals a coordinates part locates (``CimtblImporter.bound_parts``).
    Its non-empty parts join the set after the rest has bound: the master
    imports them last, the whole set is written again, and they are bound onto
    the same network. So the directory still holds the complete model.
    """
    if documents.master.profile != CIM_PROFILE:
        raise ValueError(
            f"master {documents.master.name!r} declares Profile={documents.master.profile!r}; "
            f"CIMHub artifacts declare {CIM_PROFILE!r}"
        )
    if artifact_dir is not None:
        return _write_and_load(documents, Path(artifact_dir), model_cls, network, bound_parts)
    with tempfile.TemporaryDirectory(prefix="cimtbl_") as directory:
        return _write_and_load(documents, Path(directory), model_cls, network, bound_parts)


def _write_and_load(documents: DocumentSet, directory: Path, model_cls: type | None, network, bound_parts):
    network = _load(write_documents(documents, directory), model_cls, network)
    late = [part for part in bound_parts(network) if part.statements] if bound_parts is not None else []
    if not late:
        return network
    master = dataclasses.replace(documents.master,
                                 statements=[*documents.master.statements, *(Import(part.name) for part in late)])
    write_documents(DocumentSet(master=master, parts=[*documents.parts, *late]), directory)
    for part in late:  # under the master's model scope, which cimtables keeps process-wide, as for any Import
        cimtables.load(directory / f"{part.name}.cimtbl", network)
    return network


def _load(master: Path, model_cls: type | None, network):
    if network is None:
        return cimtables.load_model(master, model_cls=model_cls)
    cimtables.load(master, network)
    return network

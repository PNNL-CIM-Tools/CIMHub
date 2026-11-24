"""Mermaid diagram generation for LinkML-generated dataclasses.

Mirrors the surface of ``cimgraph.utils.mermaid.get_mermaid`` but works on the
plain LinkML dataclasses produced by ``pythongen`` (raw RAW, OpenDSS, etc.)
rather than cimgraph's ``Identity`` profile classes.

The single entry point is :func:`get_mermaid`, which accepts an instance, a
class, or a list of either::

    from cimhub_core import get_mermaid
    from cimhub_raw.schema.raw_v34.raw34_schema import BusRecord

    bus = raw_model.first(BusRecord)
    Mermaid(get_mermaid(bus))           # instance -> mindmap of its fields
    Mermaid(get_mermaid(BusRecord))     # class    -> class diagram

Why this exists: cimgraph's ``get_mermaid`` calls ``cim_class.__mro__`` and
keys off its ``Identity`` base class. LinkML dataclasses are not ``Identity``
subclasses, and ``GraphModel.first()`` returns an *instance*, so the cimgraph
helper raises ``AttributeError: 'BusRecord' object has no attribute '__mro__'``.

Field classification (attribute vs. association) is driven by the LinkML YAML
schema via :func:`cimhub_core.serialization.get_schema_annotations`, which is
extended here to also surface ``range``, ``description``, and ``multivalued``.
A field is rendered as an association when its declared ``range`` resolves to
another class in the same module; otherwise it is a scalar attribute.
"""
from __future__ import annotations

import base64
import logging
import sys
from dataclasses import fields, is_dataclass
from functools import lru_cache

import requests

from cimhub_core.serialization import get_schema_annotations

__all__ = ["get_mermaid", "download_mermaid"]

_log = logging.getLogger(__name__)

INDENT = "    "
WRAP = 22


# ---------------------------------------------------------------------------
# Small text helpers (mirrors cimgraph's wrapping behavior)
# ---------------------------------------------------------------------------

def _wrap(text: str) -> list[str]:
    """Split a string into at most two WRAP-length chunks."""
    if len(text) <= WRAP:
        return [text]
    return [text[:WRAP], text[WRAP:]]


def _identifier(obj: object) -> str:
    """Return a short, mermaid-safe node id for an instance.

    Uses the schema identifier field when present, else the first non-empty
    common id field, else the object's ``id()``.
    """
    cls = type(obj)
    id_field = _identifier_field(cls)
    if id_field is not None:
        value = getattr(obj, id_field, None)
        if value is not None:
            return _safe(str(value))
    for attr in ("ID", "name", "identifier"):
        value = getattr(obj, attr, None)
        if value is not None:
            return _safe(str(value))
    return f"n{id(obj)}"


def _safe(text: str) -> str:
    """Sanitize a string for use as a mermaid node identifier."""
    return "".join(c if c.isalnum() else "_" for c in text.strip()) or "node"


# ---------------------------------------------------------------------------
# Schema introspection
# ---------------------------------------------------------------------------

@lru_cache(maxsize=256)
def _identifier_field(cls: type) -> str | None:
    """Return the field flagged ``identifier: true`` in the schema, if any."""
    for name, annot in get_schema_annotations(cls).items():
        if annot.get("identifier"):
            return name
    return None


@lru_cache(maxsize=256)
def _module_classes(module_name: str) -> dict[str, type]:
    """Map class name -> class for every dataclass in *module_name*."""
    module = sys.modules.get(module_name)
    if module is None:
        return {}
    out = {}
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and is_dataclass(obj):
            out[name] = obj
    return out


def _range_class(cls: type, field_annot: dict) -> type | None:
    """Resolve a field's ``range`` annotation to a sibling dataclass, or None.

    Scalar ranges (integer, float, string, bool) and unknown names return None,
    marking the field as a plain attribute rather than an association.
    """
    rng = field_annot.get("range")
    if not isinstance(rng, str) or rng in ("integer", "float", "string", "boolean", "double", "date", "datetime", "time"):
        return None
    return _module_classes(cls.__module__).get(rng)


def _unit(field_annot: dict) -> str:
    """Extract a human-readable unit from a LinkML ``unit`` annotation."""
    unit = field_annot.get("unit")
    if isinstance(unit, dict):
        return unit.get("ucum_code") or unit.get("symbol") or ""
    return str(unit) if unit else ""


# ---------------------------------------------------------------------------
# Instance rendering -> mindmap
# ---------------------------------------------------------------------------

def _object_mermaid(obj: object) -> str:
    """Render a single dataclass instance as a mermaid mindmap of its fields."""
    cls_name = type(obj).__name__
    node = _identifier(obj)
    annotations = get_schema_annotations(type(obj))

    mermaid = "mindmap\n"
    mermaid += f"{INDENT}{node}(({cls_name}))\n"
    for f in fields(obj):
        value = getattr(obj, f.name)
        if value is None:
            continue
        # Only scalar fields belong in the mindmap; nested objects get their own.
        if _range_class(type(obj), annotations.get(f.name, {})) is not None:
            continue
        unit = _unit(annotations.get(f.name, {}))
        suffix = f" {unit}" if unit else ""
        mermaid += f"{INDENT * 2}{f.name}: {value}{suffix}\n"
    return mermaid


# ---------------------------------------------------------------------------
# Class rendering -> class diagram
# ---------------------------------------------------------------------------

def _class_block(cls: type, show_attributes: bool, annotations: dict) -> str:
    """Render the ``class Foo { +field: type }`` block for one class."""
    mermaid = f"{INDENT}class {cls.__name__} {{\n"
    if cls.__doc__ and cls.__doc__.strip():
        mermaid += f"{INDENT * 2}<<{cls.__doc__.strip().splitlines()[0]}>>\n"
    if show_attributes:
        for f in fields(cls):
            field_annot = annotations.get(f.name, {})
            if _range_class(cls, field_annot) is not None:
                continue  # association, rendered as an edge instead
            type_name = field_annot.get("range") or _scalar_type(f)
            unit = _unit(field_annot)
            suffix = f" [{unit}]" if unit else ""
            mermaid += f"{INDENT * 2}+ {f.name}: {type_name}{suffix}\n"
    mermaid += f"{INDENT}}}\n"
    return mermaid


def _scalar_type(field_obj) -> str:
    """Best-effort scalar type name from a dataclass field's type hint."""
    t = field_obj.type
    return getattr(t, "__name__", str(t))


def _class_associations(cls: type, annotations: dict) -> str:
    """Render association edges (e.g. container -> record) for one class."""
    mermaid = ""
    for f in fields(cls):
        field_annot = annotations.get(f.name, {})
        target = _range_class(cls, field_annot)
        if target is None:
            continue
        cardinality = '"0..*"' if field_annot.get("multivalued") else '"0..1"'
        mermaid += f"{INDENT}{cls.__name__} --> {cardinality} {target.__name__} : {f.name}\n"
    return mermaid


def _class_mermaid(cls: type, show_attributes: bool) -> str:
    """Class block plus its association edges."""
    annotations = get_schema_annotations(cls)
    return _class_block(cls, show_attributes, annotations) + _class_associations(cls, annotations)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def get_mermaid(root: object | type | list, show_attributes: bool = True,
                theme: str = "neutral") -> str:
    """Generate a mermaid diagram for a LinkML dataclass instance, class, or list.

    Args:
        root: A dataclass *instance* (rendered as a mindmap of its fields),
            a dataclass *class* (rendered as a class diagram), or a list of
            classes (rendered as a combined class diagram with associations).
        show_attributes: Whether to include scalar attributes in class diagrams.
        theme: Mermaid theme name.

    Returns:
        A mermaid diagram string suitable for ``IPython.display.Mermaid(...)``.

    Raises:
        TypeError: If *root* is not a dataclass instance, class, or list thereof.
    """
    prelude = '%%{init: {"theme":"' + str(theme) + '"}}%%\n'

    # Instance: anything that is a dataclass value but not a class.
    if is_dataclass(root) and not isinstance(root, type):
        return _object_mermaid(root)

    # Single class.
    if isinstance(root, type) and is_dataclass(root):
        return prelude + "classDiagram\n" + _class_mermaid(root, show_attributes)

    # List of classes -> one combined class diagram.
    if isinstance(root, list):
        classes = [r for r in root if isinstance(r, type) and is_dataclass(r)]
        if classes and len(classes) == len(root):
            mermaid = prelude + "classDiagram\n"
            for cls in classes:
                mermaid += _class_mermaid(cls, show_attributes)
            return mermaid
        # List of instances -> concatenated mindmaps.
        instances = [r for r in root if is_dataclass(r) and not isinstance(r, type)]
        if instances and len(instances) == len(root):
            return "".join(_object_mermaid(r) for r in instances)

    raise TypeError(
        f"get_mermaid expects a LinkML dataclass instance, class, or list thereof, got {type(root)!r}"
    )


def download_mermaid(mermaid: str, filename: str, timeout: int = 30) -> bool:
    """Download a rendered mermaid diagram from mermaid.ink and save it.

    Args:
        mermaid: The mermaid diagram source.
        filename: Output image path.
        timeout: Request timeout in seconds.

    Returns:
        True on success, False on a network/HTTP error.
    """
    graphbytes = mermaid.encode("utf-8")  # a docstring may hold Ω or µ
    base64_string = base64.b64encode(graphbytes).decode("ascii")
    url = "https://mermaid.ink/img/" + base64_string
    try:
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with open(filename, "wb") as file:
                for chunk in response.iter_content(chunk_size=16384):
                    if chunk:
                        file.write(chunk)
        return True
    except requests.exceptions.RequestException as e:
        _log.error("Error downloading mermaid diagram to %s: %s", filename, e)
        return False

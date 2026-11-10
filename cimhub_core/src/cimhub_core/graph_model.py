"""Format-agnostic data access layer for LinkML-generated dataclasses.

``GraphModel`` is a thin sorted-dictionary interface (keyed by type and
identifier) that mirrors the cimgraph ``GraphModel`` API. It is decoupled
from CIM-specific concepts — no database, no SPARQL, no SHACL — so it can
hold any collection of LinkML dataclass instances.

Usage::

    from cimhub_core import GraphModel

    model = GraphModel()
    model.add_to_graph(some_object)

    for sub in model.list_by_class(schema.Substation):
        print(sub.ID)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable, Iterator, TypeVar, cast

__all__ = ["GraphModel"]

_log = logging.getLogger(__name__)
T = TypeVar("T")

# Fallback priority order when the schema has no ``identifier: true`` annotation.
# PSM schemas use 'ID', OpenDSS schemas use 'name', cimgraph uses 'identifier'.
_IDENTIFIER_FIELDS = ("ID", "name", "identifier")


@lru_cache(maxsize=128)
def _get_identifier_field(cls: type) -> str | None:
    """Discover which field has ``identifier: true`` in the LinkML schema.

    Returns the field name, or ``None`` if no schema annotation is found.
    Result is cached per class.
    """
    # Import lazily to avoid circular imports at module load time.
    from cimhub_core.serialization import get_schema_annotations

    annotations = get_schema_annotations(cls)
    for field_name, annot in annotations.items():
        if annot.get("identifier"):
            return field_name
    return None


def _get_identifier(obj: object) -> str:
    """Extract the identifier from a LinkML dataclass instance.

    First checks the LinkML schema for an ``identifier: true`` field.
    Falls back to common field names in priority order, then ``id(obj)``.
    """
    # Schema-aware lookup (cached per class)
    id_field = _get_identifier_field(type(obj))
    if id_field is not None:
        value = getattr(obj, id_field, None)
        if value is not None:
            return str(value)

    # Heuristic fallback
    for attr in _IDENTIFIER_FIELDS:
        value = getattr(obj, attr, None)
        if value is not None:
            return str(value)
    # id(obj) is non-deterministic and not stable across runs or serialization.
    # Log a warning so the missing ``identifier: true`` annotation is visible.
    _log.warning(
        "%s has no identifier field; falling back to id(obj) — "
        "add ``identifier: true`` to the LinkML schema",
        type(obj).__name__,
    )
    return str(id(obj))


# ---------------------------------------------------------------------------
# GraphModel
# ---------------------------------------------------------------------------

@dataclass
class GraphModel:
    """Sorted-dictionary data store with pluggable I/O.

    ``graph`` is structured as ``{type: {identifier: instance}}``.
    """

    graph: dict[type, dict[str, object]] = field(default_factory=dict)
    _class_iter: dict[type, Iterator] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        # Preserve a graph passed to the constructor — assigning a fresh
        # defaultdict unconditionally would silently discard it. Readers that
        # build their own ``{cls: {id: obj}}`` dict (because they need custom
        # collision handling) hand it over via ``GraphModel(graph=...)``.
        self.graph = defaultdict(dict, self.graph)

    @classmethod
    def from_objects(cls, objects: Iterable[object]) -> "GraphModel":
        """Build a GraphModel from a flat iterable of objects.

        Converters and readers that accumulate a flat list still need to hand a
        GraphModel to a writer; this is that one step.
        """
        model = cls()
        for obj in objects:
            model.add_to_graph(obj)
        return model

    # -- Add ----------------------------------------------------------------

    def add_to_graph(self, obj: object) -> None:
        """Insert *obj* into the graph, keyed by its identifier.

        An identifier is unique within its class in the model, because it seeds
        the object's mRID, so a collision raises ``ValueError``. It is usually a
        duplicate declaration in the source file, or an identifier scheme too
        coarse to tell two records apart (see ``composite_id`` in cimhub_raw).
        Native formats scope names by class (an OpenDSS ``Line.l1`` and
        ``Load.l1``), so two classes may share one.
        """
        key = _get_identifier(obj)
        bucket = self.graph[type(obj)]
        if key in bucket:
            raise ValueError(f"{type(obj).__name__} identifier {key!r} is already in the model; identifiers are "
                             "unique within a class (they seed the mRID)")
        bucket[key] = obj

    # -- Retrieve -----------------------------------------------------------

    def list_by_class(self, cls: type[T]) -> list[T]:
        """Return all instances of *cls*, sorted by identifier."""
        values = list(self.graph.get(cls, {}).values())
        return [cast(T, v) for v in sorted(values, key=_get_identifier)]

    def iter_by_class(self, cls: type[T]) -> Iterator[T]:
        """Iterate over all instances of *cls* (insertion order)."""
        return iter(self.graph.get(cls, {}).values())

    def iter_all(self) -> Iterator[object]:
        """Iterate over every instance in the graph, grouped by class.

        Exists so callers never hand-roll the nested walk: ``graph`` is
        ``{type: {identifier: instance}}``, so iterating the inner dict directly
        yields identifier *strings*, not objects. Writers use this to serialize
        a whole model.
        """
        for bucket in self.graph.values():
            yield from bucket.values()

    def first(self, cls: type[T]) -> T | None:
        """Return the first instance of *cls* (sorted), or ``None``."""
        items = self.list_by_class(cls)
        if items:
            self._class_iter[cls] = iter(items)
            return next(self._class_iter[cls])
        return None

    def next(self, cls: type[T]) -> T | None:
        """Continue iterating from the last ``first()`` call, or ``None``."""
        it = self._class_iter.get(cls)
        if it is None:
            return self.first(cls)
        try:
            return next(it)
        except StopIteration:
            return None

    # -- Search -------------------------------------------------------------

    def find_by_attribute(self, cls: type[T], attribute: str, value) -> list[T]:
        """Return all instances of *cls* where *attribute* equals *value*."""
        return [
            obj
            for obj in self.graph.get(cls, {}).values()
            if str(getattr(obj, attribute, None)) == str(value)
        ]

    # -- Introspection ------------------------------------------------------

    def __contains__(self, cls: type) -> bool:
        return bool(self.graph.get(cls))

    def __len__(self) -> int:
        return sum(len(b) for b in self.graph.values())

    def count(self, cls: type) -> int:
        """Return the number of *cls* instances in the graph."""
        return len(self.graph.get(cls, {}))

    def __repr__(self) -> str:
        summary = {cls.__name__: len(b) for cls, b in self.graph.items() if b}
        return f"GraphModel({summary})"

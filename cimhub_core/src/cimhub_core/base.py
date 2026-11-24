"""Abstract base classes for format-specific I/O and conversion.

Every CIMHub sub-package implements one or more of these interfaces to
bridge its native file format with LinkML-generated dataclasses and the
CIM graph model.

Serialization layer (file ↔ LinkML objects):
    FormatReader   — parse a native source into a ``GraphModel`` of dataclasses
    FormatWriter   — write dataclass instances back to native files

Conversion layer (LinkML objects ↔ CIM graph):
    FormatImporter — native format → CIM graph
    CimtblImporter — native format → ``.cimtbl`` documents → CIM graph
                     (the file-format importers; the ``cimtbl-import-contract`` skill)
    FormatExporter — CIM graph → native format
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from cimgraph.models import GraphModel as CIMGraphModel
from cimtables.document import Document, DocumentSet

from cimhub_core.cimtbl import cimtbl_to_cim
from cimhub_core.graph_model import GraphModel as SpokeGraphModel

__all__ = ["FormatReader", "FormatWriter", "FormatImporter", "CimtblImporter", "FormatExporter"]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class FormatReader(ABC):
    """Parse a native-format source into LinkML dataclass instances.

    The source is bound once, at construction, and never passed again::

        network = DssReader("Master.dss").read_all()
        loads = network.list_by_class(schema.Load)

    ``read_all`` is the only way to read a model. There is deliberately no
    per-class read method: a single entry point means every consumer — a
    converter, a CLI inspector, a model browser — walks the same
    ``SpokeGraphModel.graph`` without needing to know which classes the format
    contains.
    """

    #: The bound source, as passed to ``__init__``. Subclasses may narrow the
    #: type but must keep the attribute so callers can report what was read.
    source: Any

    @abstractmethod
    def __init__(self, source: Any) -> None:
        """Bind *source* without parsing it.

        Args:
            source: Format-specific. Usually a path to a file (OpenDSS
                ``Master.dss``, a raw ``.raw``) or a directory (distOPF CSVs).
                Deliberately unconstrained so a reader can accept a DSN, a live
                connection, or an in-memory object without changing this
                contract — what matters is that :meth:`read_all` returns a
                ``SpokeGraphModel``.

        Parsing belongs in :meth:`read_all`, not here, so constructing a reader
        stays cheap and side-effect-free.
        """
        ...

    @abstractmethod
    def read_all(self) -> SpokeGraphModel:
        """Parse the bound source and return every object found.

        Returns:
            A ``SpokeGraphModel`` keyed ``{schema_class: {identifier: instance}}``
            holding native-format dataclasses (not CIM objects). Formats that
            parse incrementally should still return one graph covering the
            whole source.
        """
        ...


class FormatWriter(ABC):
    """Write native-format dataclass instances back out to their format.

    Mirror of :class:`FormatReader`: ``write`` takes the same
    ``SpokeGraphModel`` that ``read_all`` produces, so a round trip is::

        network = DssReader("Master.dss").read_all()
        DssWriter().write(network, "out.dss")

    Taking the graph rather than a flat list keeps the by-class grouping the
    graph already has. Formats that emit one file per class (distOPF CSVs) or
    one section per class (raw RAW) need that grouping, and rebuilding it from
    a flat list is both wasted work and a chance to lose objects.
    """

    @abstractmethod
    def write(self, model: SpokeGraphModel, destination: str) -> None:
        """Write every object in *model* to *destination*.

        Args:
            model: A ``SpokeGraphModel`` of native-format dataclasses, keyed
                ``{schema_class: {identifier: instance}}``.
            destination: Path to output file or directory. Formats that write
                one file per class take a directory; single-file formats take
                a file path. Documented per writer.
        """
        ...

    @abstractmethod
    def serialize(self, obj) -> str:
        """Return *obj* rendered in the native format.

        This is the primitive; :meth:`write` is the file-writing convenience
        built on it. Some formats have no file step at all — the OpenDSS
        exporter builds a list of DSS command strings purely from
        ``serialize``, so this must stand alone.

        Returns:
            The native representation (DSS command, RAW record, GLM block, etc.).
        """
        ...


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

class FormatImporter(ABC):
    """Convert an already-parsed native model to CIM.

    Importers do no file I/O. Reading is the reader's job, so the pipeline is
    three explicit steps and each stage is independently inspectable::

        native = DssReader("Master.dss").read_all()      # parse
        feeder = DssImporter().to_cim(native)            # convert
        write_xml(feeder, "out.xml")                     # persist

    The thin ``<fmt>_to_cim(model, *, name=...)`` function builds the importer and calls ``to_cim``; it takes the
    parsed model too, never a path.

    Taking a ``SpokeGraphModel`` rather than a path is what removes the old
    ambiguity: there is no ``source`` whose type varies per format, and no
    reader to construct or not construct. A caller that wants to inspect what
    was parsed before converting simply looks at ``native.graph``.

    Subclasses declare the concrete cimgraph model type they produce
    (``model_cls``) and implement :meth:`to_cim`. Each format also exposes a
    thin ``<fmt>_to_cim`` convenience function delegating here.

    See the ``reader-writer`` skill for the full spec.
    """

    #: Concrete cimgraph GraphModel subclass this importer populates
    #: (e.g. ``FeederModel``, ``NodeBreakerModel``, ``BusBranchModel``).
    model_cls: type

    @abstractmethod
    def to_cim(self, model: SpokeGraphModel, *, network=None) -> CIMGraphModel:
        """Convert the native objects in *model* to CIM.

        Args:
            model: A ``SpokeGraphModel`` of native-format dataclasses, as
                returned by the format's ``FormatReader.read_all()``.
            network: Existing CIM graph to populate. If ``None``, a new
                ``model_cls`` is created via :meth:`make_network`. Pass one to
                merge several native models into a single CIM network.

        Returns:
            A populated cimgraph ``GraphModel`` subclass (never raw records).
        """
        ...

    def make_network(self, network=None):
        """Return *network* if given, else a fresh empty ``self.model_cls``."""
        if network is not None:
            return network
        from cimgraph.databases import XMLFile
        return self.model_cls(connection=XMLFile(""), container=None)


class CimtblImporter(FormatImporter):
    """Convert a native model to CIM through ``.cimtbl`` documents.

    The spoke implements :meth:`to_cimtbl`, a pure mapping from native
    records to documents, and :meth:`bound_parts` only for a part that reads
    the bound Terminals. :meth:`to_cim` writes those documents and builds CIM
    from the written text, so the artifact a reviewer reads is exactly what the
    model was built from::

        native = DssReader("Master.dss").read_all()
        feeder = DssImporter().to_cim(native, artifact_dir="out/feeder")

    Spokes with no file format (GDM builds CIM with CIM-Builder's keyword
    methods) subclass :class:`FormatImporter` directly.
    See the ``cimtbl-import-contract`` skill.
    """

    #: ``None``: the master's one Feeder (``FeederModel``) or Substation
    #: (``NodeBreakerModel``) decides. ``BusBranchModel`` for RAW, MATPOWER and
    #: PSM, whose container is the file's one GeographicalRegion.
    model_cls: type | None = None

    @abstractmethod
    def to_cimtbl(self, model: SpokeGraphModel) -> DocumentSet:
        """Map the native objects in *model* to documents: the master plus one per native table.

        Pure: no file I/O, and no CIM objects (plan I5, I7).
        """
        ...

    def bound_parts(self, model: SpokeGraphModel, network: CIMGraphModel) -> list[Document]:
        """The parts mapped from what binding made, not from the native records alone: a part that needs the
        Terminals of the other parts' equipment (a coordinates part locates each piece at its Terminals' buses).

        Called with the network the ``to_cimtbl`` documents bound; ``to_cim`` adds these parts to the artifact,
        imported last, and binds them onto the same network. Reads the network, never constructs on it (plan I5).
        Terminals are what binding makes, so this is where they are read: CIM-Tables declined a text-level
        inverse of its connectivity columns (UPSTREAM_REQUESTS U11). None by default.
        """
        return []

    def to_cim(self, model: SpokeGraphModel, *, network=None, artifact_dir=None) -> CIMGraphModel:
        """``to_cimtbl``, then write the documents and load them, then the ``bound_parts`` (see ``cimtbl_to_cim``).

        Args:
            model: The native model from the format's ``FormatReader.read_all()``.
            network: Existing cim18v17 network to bind onto, to merge several
                native models into one. If ``None``, a new model is built.
            artifact_dir: Where the ``.cimtbl`` files go. If ``None``, a
                temporary directory, removed after loading.
        """
        return cimtbl_to_cim(self.to_cimtbl(model), model_cls=self.model_cls, network=network,
                             artifact_dir=artifact_dir, bound_parts=lambda bound: self.bound_parts(model, bound))


class FormatExporter(ABC):
    """Convert a CIM graph model into native-format dataclasses.

    Exact mirror of :class:`FormatImporter`, and the reverse of
    :meth:`FormatReader.read_all`. Exporters do no file I/O — they return a
    ``SpokeGraphModel``, and :class:`FormatWriter` persists it::

        raw = RawExporter().to_model(network)     # convert
        Raw34Writer().write(raw, "out.raw")       # persist

    There is deliberately no ``destination`` argument. An exporter that took a
    path would have to decide whether to write, to return, or both, which is
    what produced the old grab-bag of return types (a commands dict here, a
    native model or ``None`` there). Returning the graph makes the native model
    inspectable *before* it is serialized, so a bad export can be diagnosed as
    a converter bug or a writer bug rather than one opaque failure.

    Each format may still expose a thin ``cim_to_<fmt>(network, path)``
    convenience function that does the build-then-write in one call. See
    ``cimhub_core/docs/developer/converter-api.md`` for the full spec.
    """

    @abstractmethod
    def to_model(self, network: CIMGraphModel, **opts) -> SpokeGraphModel:
        """Convert the CIM objects in *network* to native-format dataclasses.

        Args:
            network: A cimgraph ``GraphModel`` containing CIM objects.
            **opts: Format-specific options (e.g. ``system_base_mva``,
                ``case_name``). Documented per exporter.

        Returns:
            A ``SpokeGraphModel`` keyed ``{schema_class: {identifier: instance}}``
            holding native-format dataclasses — the same shape the format's
            ``FormatReader.read_all()`` returns, so export output can be fed
            straight back through the importer in a round-trip test.
        """
        ...

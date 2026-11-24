"""Scaffold generator for new CIMHub spoke packages.

``scaffold_package`` writes the layout the shipped spokes (``cimhub_raw``, ``cimhub_opendss``) use::

    cimhub_<fmt>/src/cimhub_<fmt>/
        __init__.py
        <fmt>_reader.py              # FormatReader (importer side)
        <fmt>_writer.py              # FormatWriter (exporter side)
        schema/                      # LinkML skeleton
        importer/<fmt>_to_cimtbl.py  # MAPPING_ORDER, the CimtblImporter subclass, <fmt>_to_cim
        importer/cimtbl/__init__.py  # one mapper module per native table (scaffold_mapper)
        exporter/cim_to_<fmt>.py     # EXPORT_ORDER, export_tables, the FormatExporter subclass, cim_to_<fmt>

The contracts are the ``reader-writer`` and ``cimtbl-import-contract`` skills. Everything targets cim18v17.

Usage::

    from cimhub_core.scaffold import scaffold_mapper, scaffold_package

    scaffold_package("matpower", direction="both")

    # once the schema is generated: one mapper per native table
    scaffold_mapper("matpower", schema.Branch, prefix="ln_")
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from cimhub_core.cimtbl import fields_stub

__all__ = ["scaffold_package", "scaffold_mapper"]

#: The values ``scaffold_package`` accepts for ``direction``.
DIRECTIONS = ("importer", "exporter", "both")


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------

def scaffold_package(
    format_name: str,
    direction: str = "both",
    parent_dir: str = ".",
    schema_prefix: str | None = None,
) -> Path:
    """Create the directory tree and stub files for a new spoke package.

    The import side is the reader and ``importer/``; the export side is the writer and ``exporter/``.

    Args:
        format_name: Short name for the format (e.g. ``"raw"``, ``"gridlabd"``).
        direction: ``"importer"``, ``"exporter"``, or ``"both"``.
        parent_dir: Parent directory to create the package in.
        schema_prefix: Prefix for LinkML schema namespace. Defaults to
            *format_name*.

    Returns:
        Path to the created package root (e.g. ``./cimhub_raw``).

    Raises:
        ValueError: ``direction`` is not one of ``DIRECTIONS``.
        FileExistsError: the package directory exists; nothing is written.
    """
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}, not {direction!r}")
    pkg = f"cimhub_{format_name}"
    package_root = Path(parent_dir) / pkg
    if package_root.exists():
        raise FileExistsError(f"{package_root} exists; scaffold_package never overwrites")
    root = package_root / "src" / pkg

    _write(root / "__init__.py", "")
    _create_schema_skeleton(root / "schema", format_name, schema_prefix or format_name)
    if direction in ("importer", "both"):
        _create_reader_stub(root, format_name)
        _create_importer_tree(root / "importer", format_name, pkg)
    if direction in ("exporter", "both"):
        _create_writer_stub(root, format_name)
        _create_exporter_tree(root / "exporter", format_name, pkg)
    return package_root


def scaffold_mapper(
    format_name: str,
    native_cls: type,
    *,
    prefix: str,
    table_name: str | None = None,
    records=(),
    parent_dir: str = ".",
) -> Path:
    """Write the mapper and atom-test stubs for one native table (contract section 5).

    ``importer/cimtbl/<table>.py`` gets ``NATIVE_CLASS``, ``PREFIX``, a ``FIELDS``
    dict with one ``Field('TODO')`` per real slot (samples from ``records``) and a
    ``map_<table>`` stub. The ``TODO`` kind does not import, so every field must be
    classified first. ``tests/test_cimtbl_<table>.py`` gets the completeness test.
    Existing files are never overwritten.

    Args:
        format_name: The spoke (``"opendss"`` for ``cimhub_opendss``).
        native_cls: The LinkML (or pydantic) class of the native table.
        prefix: The mRID prefix from the cimtbl-translate prefix table (``"lc_"``).
        table_name: The artifact stem = the LinkML schema module of the class
            (``transformer_db``). Defaults to the class name in snake case.
        records: Native records whose values become the stub's samples.
        parent_dir: The directory holding ``cimhub_<fmt>/``.

    Returns:
        The path of the mapper module.
    """
    pkg = f"cimhub_{format_name}"
    table = table_name or _to_snake_case(native_cls.__name__)
    package_root = Path(parent_dir) / pkg
    mapper = package_root / "src" / pkg / "importer" / "cimtbl" / f"{table}.py"
    test = package_root / "tests" / f"test_cimtbl_{table}.py"
    for path in (mapper, test):
        if path.exists():
            raise FileExistsError(f"{path} exists; scaffold_mapper never overwrites")

    cls = native_cls.__name__
    _write(mapper, f'''"""{format_name} ``{cls}`` -> ``{table}.cimtbl``.

Mapping spec: ``{pkg}/docs/CIMTBL_MAPPING.md#{table}``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, copied_columns, lookup, mrid, untranscribed_values
import {native_cls.__module__} as schema

NATIVE_CLASS = schema.{cls}
PREFIX = "{prefix}"

{fields_stub(native_cls, records)}

def map_{table}(native) -> Document:
    """Every ``{cls}`` of a {format_name} model as one ``{table}`` document."""
    records = native.list_by_class(NATIVE_CLASS)
    if not records:
        return Document(name="{table}", statements=[], profile=CIM_PROFILE)
    raise NotImplementedError("TODO: map {cls} per CIMTBL_MAPPING.md#{table}")
''')
    _write(test, f'''"""Atom tests: {format_name} {cls} -> {table}.cimtbl -> cim18v17."""

from __future__ import annotations

from pathlib import Path

import pytest

from cimhub_core.cimtbl import check_fields, cimtbl_to_cim
from cimhub_core.cimtbl_testing import assert_matches_golden, atom_documents, cim_scope
from {pkg}.importer.cimtbl.{table} import FIELDS, NATIVE_CLASS, map_{table}

ATOMS = Path(__file__).parent / "atoms" / "{table}"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def test_classification_is_complete():
    check_fields(FIELDS, NATIVE_CLASS)


# TODO: an atom = source lines copied from a test model, ATOMS / "<record>.<ext>", and its golden.
# Generate the golden with CIMHUB_UPDATE_GOLDENS=1, then review it.
#
# def test_matches_golden():
#     assert_matches_golden(map_{table}(<Reader>(ATOMS / "<record>.<ext>").read_all()), ATOMS / "<record>.cimtbl")
#
# def test_binds_under_cim18v17():
#     network = cimtbl_to_cim(atom_documents(map_{table}(...)))
''')
    return mapper


# -----------------------------------------------------------------------
# Schema skeleton
# -----------------------------------------------------------------------

def _create_schema_skeleton(schema_dir: Path, fmt: str, prefix: str) -> None:
    (schema_dir / "classes").mkdir(parents=True)

    _write(schema_dir / "main.yaml", dedent(f"""\
        id: https://gridappsd.org/cimhub/{fmt}
        name: {fmt}-schema
        title: {fmt.upper()} Data Schema
        version: 0.1.0

        prefixes:
          linkml: https://w3id.org/linkml/
          {prefix}: https://gridappsd.org/cimhub/{fmt}

        default_prefix: {prefix}
        default_range: string

        imports:
          - linkml:types
          # - classes/substation
          # - classes/load
          # - classes/line
    """))

    _write(schema_dir / "types" / "common_types.yaml", dedent(f"""\
        id: https://gridappsd.org/cimhub/{fmt}/types/common_types
        name: common-types

        imports:
          - linkml:types

        prefixes:
          linkml: https://w3id.org/linkml/
          {prefix}: https://gridappsd.org/cimhub/{fmt}

        default_prefix: {prefix}

        # Define shared enums and types here
    """))

    _write(schema_dir / f"{fmt}.py", dedent(f"""\
        # Auto-generated by LinkML gen-python. DO NOT HAND-EDIT.
        # Run: gen-python schema/main.yaml > schema/{fmt}.py
        #
        # This file is a placeholder. Generate it after defining your
        # LinkML YAML schemas in schema/classes/.
    """))


# -----------------------------------------------------------------------
# Reader / writer stubs (package root)
# -----------------------------------------------------------------------

def _create_reader_stub(root: Path, fmt: str) -> None:
    cls_name = f"{_to_pascal_case(fmt)}Reader"
    _write(root / f"{fmt}_reader.py", dedent(f"""\
        \"\"\"FormatReader for {fmt.upper()} native files (the ``reader-writer`` skill).\"\"\"

        from __future__ import annotations

        from cimhub_core import FormatReader, GraphModel

        __all__ = ["{cls_name}"]


        class {cls_name}(FormatReader):
            \"\"\"Parse a {fmt.upper()} source into schema dataclass instances.\"\"\"

            def __init__(self, source: str) -> None:
                \"\"\"Bind *source* (path to a {fmt.upper()} file) without parsing it.\"\"\"
                self.source = source

            def read_all(self) -> GraphModel:
                \"\"\"Parse the bound source and return every object found.

                Returns:
                    A ``GraphModel`` keyed ``{{schema_class: {{identifier: instance}}}}``.
                    Build it by calling ``model.add_to_graph(obj)`` per parsed record.
                \"\"\"
                raise NotImplementedError("TODO: implement the {fmt.upper()} reader")
    """))


def _create_writer_stub(root: Path, fmt: str) -> None:
    cls_name = f"{_to_pascal_case(fmt)}Writer"
    _write(root / f"{fmt}_writer.py", dedent(f"""\
        \"\"\"FormatWriter for {fmt.upper()} native files (the ``reader-writer`` skill).\"\"\"

        from __future__ import annotations

        from pathlib import Path

        from cimhub_core import FormatWriter, GraphModel

        __all__ = ["{cls_name}"]


        class {cls_name}(FormatWriter):
            \"\"\"Write a ``GraphModel`` of {fmt.upper()} schema dataclasses.\"\"\"

            def write(self, model: GraphModel, destination: str) -> None:
                \"\"\"Write every object in *model* to the {fmt.upper()} file *destination*.\"\"\"
                path = Path(destination)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("".join(self.serialize(obj) + "\\n" for obj in model.iter_all()), encoding="utf-8")

            def serialize(self, obj) -> str:
                \"\"\"*obj* as its {fmt.upper()} text, driven by the schema's annotations.\"\"\"
                raise NotImplementedError("TODO: implement the {fmt.upper()} serializer")
    """))


# -----------------------------------------------------------------------
# Importer tree
# -----------------------------------------------------------------------

def _create_importer_tree(importer_dir: Path, fmt: str, pkg: str) -> None:
    """``importer/<fmt>_to_cimtbl.py`` and an empty ``importer/cimtbl/`` mapper package."""
    cls_name = f"{_to_pascal_case(fmt)}Importer"
    _write(importer_dir / "__init__.py", f'"""{fmt.upper()} -> cim18v17 through ``.cimtbl`` artifacts."""\n')
    _write(importer_dir / "cimtbl" / "__init__.py", dedent(f"""\
        \"\"\"{fmt.upper()} native tables -> ``.cimtbl`` documents, one mapper module per native table.

        Add each with ``cimhub_core.scaffold.scaffold_mapper``.
        Contract: the ``cimtbl-import-contract`` skill.
        Mapping spec: ``{pkg}/docs/CIMTBL_MAPPING.md``.
        \"\"\"
    """))
    _write(importer_dir / f"{fmt}_to_cimtbl.py", dedent(f"""\
        \"\"\"{fmt.upper()} -> ``.cimtbl`` documents -> cim18v17.

        Usage::

            from {pkg}.{fmt}_reader import {_to_pascal_case(fmt)}Reader
            from {pkg}.importer.{fmt}_to_cimtbl import {fmt}_to_cim

            network = {fmt}_to_cim({_to_pascal_case(fmt)}Reader(path).read_all(), name="case", artifact_dir="out/case")

        Contract: the ``cimtbl-import-contract`` skill.
        Mapping spec: ``{pkg}/docs/CIMTBL_MAPPING.md``.
        \"\"\"

        from __future__ import annotations

        from cimtables.document import Document, DocumentSet, Import

        from cimhub_core import CimtblImporter, GraphModel
        from cimhub_core.cimtbl import CIM_PROFILE

        __all__ = ["MAPPING_ORDER", "{cls_name}", "map_master", "{fmt}_to_cim"]

        #: ``(native class, mapper(native) -> Document)`` in ``Import`` order: catalogs before the instances that use
        #: them. One mapper per native table, from ``importer/cimtbl/<native_table>.py``.
        MAPPING_ORDER = (
            # (linecode.NATIVE_CLASS, linecode.map_linecode),
        )


        def map_master(native: GraphModel, parts: list[Document], *, name: str) -> Document:
            \"\"\"The master: model scope, containers and BaseVoltages, then one ``Import`` per non-empty part.\"\"\"
            statements = [
                # TODO (spec: CIMTBL_MAPPING.md#master): the containers and Table BaseVoltage
                *(Import(part.name) for part in parts),
            ]
            return Document(name=name, statements=statements, profile=CIM_PROFILE, model=name,
                            comment=f"{fmt.upper()} case {{name}}\\nMapping: {pkg}/docs/CIMTBL_MAPPING.md#master")


        class {cls_name}(CimtblImporter):
            \"\"\"A {fmt.upper()} model to ``.cimtbl`` documents: the master and one document per mapped native table.

            ``name`` is the master's ``Model`` and file stem.
            \"\"\"

            def __init__(self, name: str):
                self.name = name

            def to_cimtbl(self, model: GraphModel) -> DocumentSet:
                parts = [part for part in (mapper(model) for _, mapper in MAPPING_ORDER) if part.statements]
                return DocumentSet(master=map_master(model, parts, name=self.name), parts=parts)


        def {fmt}_to_cim(model: GraphModel, *, name: str, network=None, artifact_dir=None):
            \"\"\"A {fmt.upper()} model (``{_to_pascal_case(fmt)}Reader(path).read_all()``) as a cim18v17 network, built from
            its written artifacts (a temporary directory when ``artifact_dir`` is None).\"\"\"
            return {cls_name}(name).to_cim(model, network=network, artifact_dir=artifact_dir)
    """))


# -----------------------------------------------------------------------
# Exporter tree
# -----------------------------------------------------------------------

def _create_exporter_tree(exporter_dir: Path, fmt: str, pkg: str) -> None:
    """``exporter/cim_to_<fmt>.py``: ``EXPORT_ORDER``, ``export_tables``, the exporter class and ``cim_to_<fmt>``."""
    cls_base = _to_pascal_case(fmt)
    exporter_cls = f"{cls_base}Exporter"
    writer_cls = f"{cls_base}Writer"
    _write(exporter_dir / "__init__.py", f'"""cim18v17 -> {fmt.upper()} (``{pkg}/docs/EXPORT_MAPPING.md``)."""\n')
    _write(exporter_dir / f"cim_to_{fmt}.py", dedent(f"""\
        \"\"\"cim18v17 network -> {fmt.upper()} records (spec ``{pkg}/docs/EXPORT_MAPPING.md``).

        Each module of ``EXPORT_ORDER`` exports its CIM classes through the core getters (the ``export-getters``
        skill), over the whole network. The result has the shape ``{cls_base}Reader.read_all()`` returns, so
        ``{writer_cls}`` writes a file the reader and the importer read back.
        \"\"\"

        from __future__ import annotations

        from typing import NamedTuple

        import cimprofiles.cim18.cim18v17 as cim

        from cimhub_core import FormatExporter, GraphModel
        from {pkg}.{fmt}_writer import {writer_cls}

        #: Modules in export order. Each has ``NATIVE_CLASS``, ``CIM_CLASSES`` (the CIM classes it exports),
        #: ``SLOTS`` (``{{native class: {{slot: Slot}}}}``) and ``export(context) -> list[record]``.
        EXPORT_ORDER = ()

        __all__ = ["EXPORT_ORDER", "ExportContext", "{exporter_cls}", "cim_to_{fmt}", "export_tables"]


        class ExportContext(NamedTuple):
            \"\"\"What every module shares. Add the values computed once over the network (numbering, names).\"\"\"
            network: object

            def objects(self, *cim_classes: type) -> list:
                \"\"\"The network's objects of ``cim_classes``, class by class in the order given.\"\"\"
                return [obj for cim_class in cim_classes for obj in self.network.graph.get(cim_class, {{}}).values()]


        def export_tables(network, modules) -> GraphModel:
            \"\"\"The records of ``modules`` over ``network``.\"\"\"
            context = ExportContext(network)
            model = GraphModel()
            for module in modules:
                for record in module.export(context):
                    model.add_to_graph(record)
            return model


        class {exporter_cls}(FormatExporter):
            \"\"\"``to_model(network) -> GraphModel`` of {fmt.upper()} records. Conducting equipment of a class no module
            exports raises.\"\"\"

            def to_model(self, network) -> GraphModel:
                _check_exported(network)
                return export_tables(network, EXPORT_ORDER)


        def cim_to_{fmt}(network, destination) -> None:
            \"\"\"Export ``network`` and write it to ``destination``.\"\"\"
            {writer_cls}().write({exporter_cls}().to_model(network), destination)


        def _check_exported(network) -> None:
            \"\"\"Raise on conducting equipment no module exports, so nothing is dropped silently.\"\"\"
            exported = {{cim_class for module in EXPORT_ORDER for cim_class in module.CIM_CLASSES}}
            missing = {{cls.__name__: len(objects) for cls, objects in network.graph.items()
                       if objects and issubclass(cls, cim.ConductingEquipment) and cls not in exported}}
            if missing:
                raise ValueError(f"no {fmt.upper()} export yet for {{dict(sorted(missing.items()))}}")
    """))


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _to_snake_case(name: str) -> str:
    """Convert PascalCase to snake_case, handling acronyms.

    ``ACLineSegment`` -> ``ac_line_segment``
    ``DCLineSegment`` -> ``dc_line_segment``
    ``PowerTransformerEnd`` -> ``power_transformer_end``
    """
    result: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper():
            # Insert underscore before uppercase if:
            # - not at start
            # - previous char was lowercase, OR
            # - next char is lowercase (end of acronym like "AC" in "ACLine")
            if i > 0:
                prev_upper = name[i - 1].isupper()
                next_lower = (i + 1 < len(name) and name[i + 1].islower())
                if not prev_upper or next_lower:
                    result.append("_")
        result.append(ch.lower())
    return "".join(result)


def _to_pascal_case(name: str) -> str:
    """Convert snake_case or lowercase to PascalCase."""
    return "".join(part.capitalize() for part in name.split("_"))


def _write(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

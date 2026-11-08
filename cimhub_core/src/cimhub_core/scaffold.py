"""Scaffold generator for new CIMHub sub-packages.

Creates the standard directory structure and stubs for a new format package.
The importer follows the ``.cimtbl`` contract (the ``cimtbl-import-contract`` skill):
a reader, ``<fmt>_to_cimtbl.py`` (``MAPPING_ORDER``, the ``CimtblImporter``
subclass, ``<fmt>_to_cim``) and one mapper module per native table under
``importer/cimtbl/``. The exporter keeps the registry layout of
the ``reader-writer`` skill. Everything targets cim18v17 (plan D13).

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

#: Exporter stub layout: one subpackage per domain, one stub per CIM class.
DOMAIN_CIM_CLASSES: dict[str, list[str]] = {
    "base":         [],
    "topology":     ["Substation", "ConnectivityNode", "VoltageLevel"],
    "lines":        ["ACLineSegment"],
    "loads":        ["EnergyConsumer"],
    "generators":   ["GeneratingUnit", "SynchronousMachine"],
    "transformers": ["PowerTransformer", "PowerTransformerEnd", "RatioTapChanger"],
    "switches":     ["Breaker", "Disconnector"],
    "shunts":       ["LinearShuntCompensator"],
    "series":       ["SeriesCompensator"],
    "hvdc":         ["DCLineSegment", "CsConverter"],
    "inverters":    ["BatteryUnit", "PowerElectronicsConnection"],
}
DOMAINS: list[str] = list(DOMAIN_CIM_CLASSES)

#: The profile module every generated stub imports (plan D13).
_CIM_IMPORT = "import cimprofiles.cim18.cim18v17 as cim"


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------

def scaffold_package(
    format_name: str,
    direction: str = "both",
    parent_dir: str = ".",
    schema_prefix: str | None = None,
) -> Path:
    """Create the directory tree and stub files for a new sub-package.

    Args:
        format_name: Short name for the format (e.g. ``"raw"``, ``"gridlabd"``).
        direction: ``"importer"``, ``"exporter"``, or ``"both"``.
        parent_dir: Parent directory to create the package in.
        schema_prefix: Prefix for LinkML schema namespace. Defaults to
            *format_name*.

    Returns:
        Path to the created package root (e.g. ``./cimhub_raw``).
    """
    prefix = schema_prefix or format_name
    pkg = f"cimhub_{format_name}"
    root = Path(parent_dir) / pkg / "src" / pkg

    # Schema skeleton
    _write(root / "__init__.py", "")
    _create_schema_skeleton(root / "schema", format_name, prefix)

    # Importer / exporter
    if direction in ("importer", "both"):
        _create_importer_tree(root / "importer", format_name, pkg)
    if direction in ("exporter", "both"):
        _create_exporter_tree(root / "exporter", format_name)

    # MCP service stub
    _create_service_stub(root / "service.py", format_name, direction)

    return Path(parent_dir) / pkg


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
    schema_dir.mkdir(parents=True, exist_ok=True)
    (schema_dir / "classes").mkdir(exist_ok=True)
    (schema_dir / "types").mkdir(exist_ok=True)

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

    _write(schema_dir / f"{fmt}.py", dedent("""\
        # Auto-generated by LinkML gen-python. DO NOT HAND-EDIT.
        # Run: gen-python schema/main.yaml > schema/{fmt}.py
        #
        # This file is a placeholder. Generate it after defining your
        # LinkML YAML schemas in schema/classes/.
    """.format(fmt=fmt)))


# -----------------------------------------------------------------------
# Converter tree (importer or exporter)
# -----------------------------------------------------------------------

def _create_importer_tree(conv_dir: Path, fmt: str, pkg: str) -> None:
    """Reader stub, ``<fmt>_to_cimtbl.py`` and an empty ``cimtbl/`` mapper package."""
    _write(conv_dir / "__init__.py", "")
    _create_reader_stub(conv_dir, fmt, pkg)
    _write(conv_dir / "cimtbl" / "__init__.py", dedent(f"""\
        \"\"\"{fmt.upper()} native tables -> ``.cimtbl`` documents, one mapper module per native table.

        Add each with ``cimhub_core.scaffold.scaffold_mapper``.
        Contract: the ``cimtbl-import-contract`` skill.
        Mapping spec: ``{pkg}/docs/CIMTBL_MAPPING.md``.
        \"\"\"
    """))
    _create_cimtbl_orchestrator_stub(conv_dir, fmt, pkg)


def _create_exporter_tree(conv_dir: Path, fmt: str) -> None:
    """Registry, writer stub, orchestrator and one stub converter per CIM class (CONVERTER_API.md)."""
    pkg = f"cimhub_{fmt}"
    direction = "exporter"
    conv_dir.mkdir(parents=True, exist_ok=True)

    # Registry
    reg_name = f"{fmt}_{direction}_registry"
    _write(conv_dir / "__init__.py", "")
    _write(conv_dir / "registry.py", dedent(f"""\
        from cimhub_core import ConverterRegistry

        {reg_name} = ConverterRegistry()
    """))

    _create_writer_stub(conv_dir, fmt, pkg)
    _create_exporter_orchestrator_stub(conv_dir, fmt, pkg, reg_name)

    # Domain subdirectories with stub converters
    for domain in DOMAINS:
        domain_dir = conv_dir / domain
        domain_dir.mkdir(exist_ok=True)

        classes = DOMAIN_CIM_CLASSES.get(domain, [])
        init_imports = []

        for class_name in classes:
            module_name = _to_snake_case(class_name)
            _create_converter_stub(
                domain_dir / f"{module_name}.py",
                fmt=fmt,
                pkg=pkg,
                direction=direction,
                domain=domain,
                class_name=class_name,
                module_name=module_name,
                reg_name=reg_name,
            )
            init_imports.append(
                f"from {pkg}.{direction}.{domain} import {module_name}"
                f"  # noqa: F401"
            )

        _write(domain_dir / "__init__.py", "\n".join(init_imports) + "\n")


# -----------------------------------------------------------------------
# Converter stub
# -----------------------------------------------------------------------

def _create_converter_stub(
    path: Path,
    *,
    fmt: str,
    pkg: str,
    direction: str,
    domain: str,
    class_name: str,
    module_name: str,
    reg_name: str,
) -> None:
    func_name = f"convert_{module_name}"

    lines = [
        f'"""Convert CIM {class_name} to {fmt.upper()} format.',
        "",
        f"CIM class:    cim.{class_name}",
        f"Schema class: {fmt}.{class_name}  (define in schema/classes/)",
        '"""',
        "from __future__ import annotations",
        "",
        _CIM_IMPORT,
        f"from {pkg}.{direction}.registry import {reg_name}",
        "",
        f"# import {pkg}.schema.{fmt} as {fmt}  # uncomment after gen-python",
        "",
        "",
        f"@{reg_name}.register(cim.{class_name})",
        f"def {func_name}(cim_obj: cim.{class_name}, network):",
        f'    raise NotImplementedError("TODO: implement {class_name} conversion")',
        "",
    ]
    _write(path, "\n".join(lines))


# -----------------------------------------------------------------------
# Reader / Writer stubs
# -----------------------------------------------------------------------

def _create_reader_stub(conv_dir: Path, fmt: str, pkg: str) -> None:
    cls_name = f"{_to_pascal_case(fmt)}Reader"
    _write(conv_dir / f"{fmt}_reader.py", dedent(f"""\
        \"\"\"FormatReader for {fmt.upper()} native files.\"\"\"
        from __future__ import annotations

        from cimhub_core import FormatReader, GraphModel


        class {cls_name}(FormatReader):
            \"\"\"Parse {fmt.upper()} sources into schema dataclass instances.\"\"\"

            def __init__(self, source: str) -> None:
                \"\"\"Bind *source* (path to a {fmt.upper()} file) without parsing it.\"\"\"
                self.source = source

            def read_all(self) -> GraphModel:
                \"\"\"Parse the bound source and return every object found.

                Returns:
                    A ``GraphModel`` keyed ``{{schema_class: {{identifier: instance}}}}``.
                    Build it by calling ``model.add_to_graph(obj)`` per parsed record.
                \"\"\"
                raise NotImplementedError("TODO: implement {fmt.upper()} file reader")
    """))


def _create_writer_stub(conv_dir: Path, fmt: str, pkg: str) -> None:
    cls_name = f"{_to_pascal_case(fmt)}Writer"
    _write(conv_dir / f"{fmt}_writer.py", dedent(f"""\
        \"\"\"FormatWriter for {fmt.upper()} native files.\"\"\"
        from __future__ import annotations

        from cimhub_core import FormatWriter, GraphModel


        class {cls_name}(FormatWriter):
            def write(self, model: GraphModel, destination: str) -> None:
                \"\"\"Write every object in *model* to {fmt.upper()} format.

                Args:
                    model: A ``GraphModel`` of schema dataclass instances.
                    destination: Output path.
                \"\"\"
                with open(destination, "w") as f:
                    for objects in model.graph.values():
                        for obj in objects.values():
                            f.write(self.serialize(obj) + "\\n")

            def serialize(self, obj) -> str:
                \"\"\"Serialize a single object to its {fmt.upper()} string.\"\"\"
                raise NotImplementedError("TODO: implement {fmt.upper()} serializer")
    """))


# -----------------------------------------------------------------------
# Orchestrator stub
# -----------------------------------------------------------------------

def _create_exporter_orchestrator_stub(conv_dir: Path, fmt: str, pkg: str, reg_name: str) -> None:
    direction = "exporter"
    reg_lines = [f"import {pkg}.{direction}.{domain}  # noqa: F401" for domain in DOMAINS]
    cls_base = _to_pascal_case(fmt)
    exporter_cls = f"{cls_base}Exporter"
    writer_cls = f"{cls_base}Writer"
    lines = [
        f'"""CIM to {fmt.upper()} export orchestrator.',
        "",
        "Implements the unified converter API — see",
        "the reader-writer skill.",
        '"""',
        "from __future__ import annotations",
        "",
        _CIM_IMPORT,
        "",
        "from cimhub_core import FormatExporter, GraphModel",
        "",
        f"from {pkg}.{direction}.registry import {reg_name}",
        f"from {pkg}.{direction}.{fmt}_writer import {writer_cls}",
        "",
        "# Trigger @register() decorators",
        *reg_lines,
        "",
        f"__all__ = [\"cim_to_{fmt}\", \"{exporter_cls}\"]",
        "",
        "EXPORT_ORDER: list[type] = [",
        "    # TODO: populate with CIM classes in dependency order",
        "    # cim.Substation,",
        "    # cim.ConnectivityNode,",
        "    # cim.ACLineSegment,",
        "    # cim.EnergyConsumer,",
        "]",
        "",
        "",
        f"class {exporter_cls}(FormatExporter):",
        f'    """CIM → {fmt.upper()} exporter (see CONVERTER_API.md)."""',
        "",
        "    def to_model(self, network, **opts) -> GraphModel:",
        "        model = GraphModel()",
        "",
        "        for cim_class in EXPORT_ORDER:",
        f"            converter = {reg_name}.get(cim_class)",
        "            for obj in network.list_by_class(cim_class):",
        "                result = converter(obj, network)",
        "                if result is not None:",
        "                    model.add_to_graph(result)",
        "",
        "        return model",
        "",
        "",
        f"def cim_to_{fmt}(network, output_dir, **opts) -> None:",
        '    """Convenience wrapper — build the native model and write it."""',
        f"    model = {exporter_cls}().to_model(network, **opts)",
        f"    {writer_cls}().write(model, output_dir)",
        "",
    ]

    _write(conv_dir / f"cim_to_{fmt}.py", "\n".join(lines))


def _create_cimtbl_orchestrator_stub(conv_dir: Path, fmt: str, pkg: str) -> None:
    """``<fmt>_to_cimtbl.py``: ``MAPPING_ORDER``, the master, the importer class and ``<fmt>_to_cim``."""
    cls_base = _to_pascal_case(fmt)
    _write(conv_dir / f"{fmt}_to_cimtbl.py", dedent(f"""\
        \"\"\"{fmt.upper()} -> ``.cimtbl`` -> CIM (cim18v17).

        Contract: the ``cimtbl-import-contract`` skill.
        Mapping spec: ``{pkg}/docs/CIMTBL_MAPPING.md``.
        \"\"\"
        from __future__ import annotations

        from cimtables.document import Document, DocumentSet, Import

        from cimhub_core import CimtblImporter, GraphModel
        from cimhub_core.cimtbl import CIM_PROFILE

        from {pkg}.importer.{fmt}_reader import {cls_base}Reader

        __all__ = ["MAPPING_ORDER", "{cls_base}Importer", "{fmt}_to_cim"]

        #: The master's Import order: catalogs before instances. One mapper per native table,
        #: each from importer/cimtbl/<native_table>.py.
        MAPPING_ORDER = [
            # map_<native_table>,
        ]


        def map_master(model: GraphModel, parts: list[Document]) -> Document:
            \"\"\"The master: model scope, containers and BaseVoltages, then one Import per part.\"\"\"
            statements = [
                # TODO (spec: CIMTBL_MAPPING.md#master): Object Substation, Object Feeder, Table BaseVoltage
                *(Import(part.name) for part in parts),
            ]
            return Document(name="TODO_model_name", profile=CIM_PROFILE, statements=statements)


        class {cls_base}Importer(CimtblImporter):
            \"\"\"{fmt.upper()} -> CIM through ``.cimtbl`` artifacts.\"\"\"

            def to_cimtbl(self, model: GraphModel) -> DocumentSet:
                parts = [part for part in (mapper(model) for mapper in MAPPING_ORDER) if part.statements]
                return DocumentSet(master=map_master(model, parts), parts=parts)


        def {fmt}_to_cim(path, *, artifact_dir=None):
            \"\"\"Read ``path``, write the artifacts to ``artifact_dir`` (a temporary one when None), load CIM.\"\"\"
            return {cls_base}Importer().to_cim({cls_base}Reader(path).read_all(), artifact_dir=artifact_dir)
    """))


# -----------------------------------------------------------------------
# MCP service stub
# -----------------------------------------------------------------------

def _create_service_stub(path: Path, fmt: str, direction: str) -> None:
    cls_name = f"{_to_pascal_case(fmt)}Service"

    _write(path, dedent(f"""\
        \"\"\"{fmt.upper()} Conversion Service (MCP + GridAPPS-D).\"\"\"
        from __future__ import annotations

        from typing import Any

        from cimhub_core.mcp import DualTransportMCPService


        class {cls_name}(DualTransportMCPService):
            def __init__(self, port: int = 8000):
                self.network = None
                super().__init__(service_name="{fmt}", port=port)

            def setup_tools(self) -> None:

                @self.tool()
                async def convert() -> dict[str, Any]:
                    \"\"\"Run the {fmt.upper()} conversion pipeline.\"\"\"
                    raise NotImplementedError("TODO: implement conversion")

                @self.tool()
                async def get_status() -> dict[str, Any]:
                    \"\"\"Get current service status.\"\"\"
                    return {{
                        "network_loaded": self.network is not None,
                    }}


        def main():
            import logging, sys
            logging.basicConfig(level=logging.INFO, stream=sys.stdout)
            service = {cls_name}()
            service.run()


        if __name__ == "__main__":
            main()
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

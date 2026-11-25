"""The scaffold emits the spoke layout of cimhub_raw / cimhub_opendss, and never overwrites."""

from __future__ import annotations

import ast
import dataclasses
import importlib
import sys
import tomllib
from pathlib import Path
from typing import Optional

import pytest

from cimhub_core import CimtblImporter, FormatExporter, FormatReader, FormatWriter, GraphModel
from cimhub_core.scaffold import DEPENDENCIES, scaffold_mapper, scaffold_package

REPO = Path(__file__).resolve().parents[2]
SHIPPED_SPOKES = ("cimhub_raw", "cimhub_opendss", "cimhub_gridlabd")


@dataclasses.dataclass
class Branch:
    name: str
    r: Optional[float] = None


EXPECTED_FILES = {
    "__init__.py",
    "toy_reader.py",
    "toy_writer.py",
    "schema/main.yaml",
    "schema/types/common_types.yaml",
    "schema/toy.py",
    "importer/__init__.py",
    "importer/toy_to_cimtbl.py",
    "importer/cimtbl/__init__.py",
    "exporter/__init__.py",
    "exporter/cim_to_toy.py",
}


@pytest.fixture
def toy_modules(tmp_path, monkeypatch):
    """Scaffold ``cimhub_toy`` into ``tmp_path`` and import its reader, writer, importer and exporter."""
    scaffold_package("toy", direction="both", parent_dir=tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path / "cimhub_toy" / "src"))
    names = ["cimhub_toy.toy_reader", "cimhub_toy.toy_writer", "cimhub_toy.importer.toy_to_cimtbl",
             "cimhub_toy.exporter.cim_to_toy"]
    yield [importlib.import_module(name) for name in names]
    for name in [name for name in sys.modules if name.split(".")[0] == "cimhub_toy"]:
        del sys.modules[name]


def test_package_has_the_spoke_layout(tmp_path):
    package = scaffold_package("toy", direction="both", parent_dir=tmp_path)
    root = package / "src" / "cimhub_toy"
    files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    assert files == EXPECTED_FILES
    assert (root / "schema" / "classes").is_dir()
    assert not (package / "service.py").exists() and not (root / "service.py").exists()


def test_package_has_the_project_files(tmp_path):
    package = scaffold_package("toy", direction="both", parent_dir=tmp_path)
    project = tomllib.loads((package / "pyproject.toml").read_text())["project"]
    assert (project["name"], project["readme"]) == ("cimhub_toy", "README.md")
    assert project["dependencies"] == list(DEPENDENCIES)
    assert (package / "README.md").exists() and (package / "tests" / "atoms" / "prereqs").is_dir()
    assert (package / "docs" / "CIMTBL_MAPPING.md").read_text().startswith("# TOY -> .cimtbl -> cim18v17")
    assert (package / "docs" / "EXPORT_MAPPING.md").read_text().startswith("# cim18v17 -> TOY")


@pytest.mark.parametrize("spoke", SHIPPED_SPOKES)
def test_scaffold_pins_match_the_shipped_spokes(spoke):
    shipped = tomllib.loads((REPO / spoke / "pyproject.toml").read_text())["project"]["dependencies"]
    assert set(DEPENDENCIES) <= set(shipped)


def test_generated_package_imports(toy_modules):
    reader, writer, importer, exporter = toy_modules
    assert issubclass(reader.ToyReader, FormatReader)
    assert issubclass(writer.ToyWriter, FormatWriter)
    assert issubclass(importer.ToyImporter, CimtblImporter) and importer.MAPPING_ORDER == ()
    assert issubclass(exporter.ToyExporter, FormatExporter) and exporter.EXPORT_ORDER == ()
    documents = importer.ToyImporter("case").to_cimtbl(GraphModel())
    assert documents.master.name == "case" and documents.parts == []
    assert len(exporter.export_tables(object(), exporter.EXPORT_ORDER)) == 0


@pytest.mark.parametrize("direction, present, absent", [
    ("importer", ["toy_reader.py", "importer/toy_to_cimtbl.py"], ["toy_writer.py", "exporter"]),
    ("exporter", ["toy_writer.py", "exporter/cim_to_toy.py"], ["toy_reader.py", "importer"]),
])
def test_direction_picks_the_side(tmp_path, direction, present, absent):
    root = scaffold_package("toy", direction=direction, parent_dir=tmp_path) / "src" / "cimhub_toy"
    assert all((root / path).exists() for path in present)
    assert not any((root / path).exists() for path in absent)
    docs = {path.name for path in (root.parents[1] / "docs").iterdir()}
    assert docs == {"importer": {"CIMTBL_MAPPING.md"}, "exporter": {"EXPORT_MAPPING.md"}}[direction]


def test_bad_direction_raises_and_writes_nothing(tmp_path):
    with pytest.raises(ValueError, match="'export'"):
        scaffold_package("toy", direction="export", parent_dir=tmp_path)
    assert not (tmp_path / "cimhub_toy").exists()


def test_existing_package_raises_and_writes_nothing(tmp_path):
    (tmp_path / "cimhub_toy").mkdir()
    with pytest.raises(FileExistsError, match="never overwrites"):
        scaffold_package("toy", parent_dir=tmp_path)
    assert list((tmp_path / "cimhub_toy").iterdir()) == []


def test_mapper_stub_lists_every_slot_and_never_overwrites(tmp_path):
    mapper = scaffold_mapper("toy", Branch, prefix="ln_", records=[Branch("b1", 0.1)], parent_dir=tmp_path)
    text = mapper.read_text()
    ast.parse(text)
    assert mapper.name == "branch.py"
    assert "'name': Field('TODO', note='b1')" in text and "'r': Field('TODO', note='0.1')" in text
    assert (tmp_path / "cimhub_toy" / "tests" / "test_cimtbl_branch.py").exists()
    with pytest.raises(FileExistsError, match="never overwrites"):
        scaffold_mapper("toy", Branch, prefix="ln_", parent_dir=tmp_path)

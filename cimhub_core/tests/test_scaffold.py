"""The scaffold emits the .cimtbl importer contract and cim18v17 exporter stubs."""

from __future__ import annotations

import ast
import dataclasses
from typing import Optional

import pytest

from cimhub_core.scaffold import scaffold_mapper, scaffold_package


@dataclasses.dataclass
class Branch:
    name: str
    r: Optional[float] = None


def _python_files(root):
    return sorted(root.rglob("*.py"))


def test_package_follows_the_cimtbl_contract(tmp_path):
    root = scaffold_package("toy", direction="both", parent_dir=tmp_path) / "src" / "cimhub_toy"
    importer = root / "importer"
    assert (importer / "toy_to_cimtbl.py").exists() and (importer / "cimtbl" / "__init__.py").exists()
    assert not (importer / "registry.py").exists()
    for path in _python_files(root):
        ast.parse(path.read_text(), filename=str(path))
        assert "cim17v40" not in path.read_text() and "cimhub_2026" not in path.read_text(), path
    assert "class ToyImporter(CimtblImporter)" in (importer / "toy_to_cimtbl.py").read_text()


def test_mapper_stub_lists_every_slot_and_never_overwrites(tmp_path):
    mapper = scaffold_mapper("toy", Branch, prefix="ln_", records=[Branch("b1", 0.1)], parent_dir=tmp_path)
    text = mapper.read_text()
    ast.parse(text)
    assert mapper.name == "branch.py"
    assert "'name': Field('TODO', note='b1')" in text and "'r': Field('TODO', note='0.1')" in text
    assert (tmp_path / "cimhub_toy" / "tests" / "test_cimtbl_branch.py").exists()
    with pytest.raises(FileExistsError, match="never overwrites"):
        scaffold_mapper("toy", Branch, prefix="ln_", parent_dir=tmp_path)

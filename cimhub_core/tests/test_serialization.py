"""cimhub_core.serialization: a schema file that does not parse raises, naming the file."""

from __future__ import annotations

import importlib
import sys

import pytest
import yaml

from cimhub_core.serialization import get_schema_annotations


def test_a_schema_file_that_does_not_parse_raises(tmp_path, monkeypatch):
    (tmp_path / "schema").mkdir()
    (tmp_path / "schema" / "broken.yaml").write_text("classes:\n  Bus: [unclosed\n")
    (tmp_path / "broken_schema_module.py").write_text("class Bus:\n    pass\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    module = importlib.import_module("broken_schema_module")
    try:
        with pytest.raises(yaml.YAMLError, match="broken.yaml"):
            get_schema_annotations(module.Bus)
    finally:
        del sys.modules["broken_schema_module"]

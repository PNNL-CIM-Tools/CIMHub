"""Atom-test helpers for ``.cimtbl`` mappers (rewrite plan Phase 1e).

A mapper atom test checks three things:

1. ``assert_matches_golden(document, golden)``: the formatted document equals the
   reviewed golden ``.cimtbl`` text. On a mismatch the message is a record-level
   diff (``Class mRID.column: expected X, got Y``), not a wall of text. Run with
   ``CIMHUB_UPDATE_GOLDENS=1`` to rewrite the golden, then review it in git.
2. ``cimtbl_to_cim(atom_documents(document))``: the golden binds under cim18v17.
   Atoms that reference objects they do not declare (an instance's template, its
   BaseVoltage) bind onto a network loaded from prerequisite ``.cimtbl`` files:
   ``cimtbl_to_cim(atom_documents(document), network=cimtables.load_model(prerequisite))``.
3. ``check_fields(FIELDS, NATIVE_CLASS)``: the classification is complete.
"""

from __future__ import annotations

import contextlib
import difflib
import os
from pathlib import Path

from cimgraph.core import get_cim_profile, get_model_authority, get_model_name, set_model_scope
from cimtables.document import Document, DocumentSet, Import, format_document
from cimtables.parser import parse_text
from cimtables.records import ImportRecord

from cimhub_core.cimtbl import CIM_PROFILE

__all__ = ["cim_scope", "atom_documents", "record_diff", "assert_matches_golden", "assert_text_matches_golden"]

UPDATE_GOLDENS = "CIMHUB_UPDATE_GOLDENS"


@contextlib.contextmanager
def cim_scope():
    """Put back the profile and model scope that ``cimtables.load_model`` sets process-wide (plan G5).

    Spoke suites still run old-profile tests in the same process, so every test
    that loads ``.cimtbl`` runs inside this, usually from an autouse fixture.
    """
    profile = os.environ.get("CIMG_CIM_PROFILE")
    authority, model = get_model_authority(), get_model_name()
    try:
        yield
    finally:
        if profile is None:
            os.environ.pop("CIMG_CIM_PROFILE", None)
        else:
            os.environ["CIMG_CIM_PROFILE"] = profile
        set_model_scope(authority, model)
        get_cim_profile.cache_clear()


def atom_documents(*parts: Document, name: str = "atom") -> DocumentSet:
    """A document set whose master imports ``parts``, in order. Empty parts are left out."""
    parts = [part for part in parts if part.statements]
    master = Document(name=name, profile=CIM_PROFILE, statements=[Import(part.name) for part in parts])
    return DocumentSet(master=master, parts=parts)


def _keyed_records(text: str, source_file: str) -> dict[tuple[str, str], dict[str, str]]:
    """``{(class, key): {column (unit): text}}``, keyed by mRID, else identifier, else position in the class."""
    records, header = parse_text(text, source_file=source_file)
    keyed = {("Profile", ""): {"value": str(header.profile)}}
    counts: dict[str, int] = {}
    for record in records:
        if isinstance(record, ImportRecord):
            keyed[("Import", record.path)] = {}
            continue
        counts[record.cim_class] = counts.get(record.cim_class, 0) + 1
        key = (record.fields.get("mRID") or record.fields.get("identifier") or record.fields.get("path")
               or f"#{counts[record.cim_class]}")
        keyed[(record.cim_class, key)] = {
            (f"{column} ({record.units[column]})" if record.units.get(column) else column): value
            for column, value in record.fields.items()
        }
    return keyed


def record_diff(expected_text: str, actual_text: str) -> list[str]:
    """The record-level differences between two ``.cimtbl`` texts; empty when they hold the same records.

    Comments, column order and padding are ignored. Each difference reads
    ``Class key.column: expected X, got Y``, or names a missing or extra record.
    """
    expected = _keyed_records(expected_text, "expected")
    actual = _keyed_records(actual_text, "actual")
    differences = []
    for key in expected:
        if key not in actual:
            differences.append(f"missing {key[0]} {key[1]}")
    for key in actual:
        if key not in expected:
            differences.append(f"extra {key[0]} {key[1]}")
    for key, expected_fields in expected.items():
        actual_fields = actual.get(key)
        if actual_fields is None:
            continue
        for column in [*expected_fields, *(c for c in actual_fields if c not in expected_fields)]:
            want, got = expected_fields.get(column, "<no column>"), actual_fields.get(column, "<no column>")
            if want != got:
                differences.append(f"{key[0]} {key[1]}.{column}: expected {want!r}, got {got!r}")
    return differences


def assert_matches_golden(document: Document, golden_path: str | Path) -> None:
    """Raise ``AssertionError`` unless ``format_document(document)`` equals the golden file's text."""
    assert_text_matches_golden(format_document(document), golden_path)


def assert_text_matches_golden(actual: str, golden_path: str | Path) -> None:
    """Raise ``AssertionError`` unless ``actual`` (``.cimtbl`` text, e.g. a written artifact file) equals the golden
    file's text."""
    golden_path = Path(golden_path)
    if os.environ.get(UPDATE_GOLDENS) == "1":
        golden_path.write_text(actual)
        return
    expected = golden_path.read_text()
    if actual == expected:
        return
    differences = record_diff(expected, actual)
    if not differences:
        lines = difflib.unified_diff(expected.splitlines(), actual.splitlines(), "golden", "mapper", lineterm="")
        differences = ["the records match; comments or layout differ:", *list(lines)[:40]]
    raise AssertionError(
        f"{golden_path.name} differs from the mapper output ({UPDATE_GOLDENS}=1 rewrites it):\n  "
        + "\n  ".join(differences)
    )

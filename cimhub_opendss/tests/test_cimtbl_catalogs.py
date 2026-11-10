"""S2 catalog stubs: every native slot of the wire, spacing and geometry classes is classified."""

from __future__ import annotations

import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_opendss.importer.cimtbl import geometry, wire


@pytest.mark.parametrize("native_class, prefix, fields", wire.CATALOGS + geometry.CATALOGS,
                         ids=lambda value: getattr(value, "__name__", None))
def test_classification_is_complete(native_class, prefix, fields):
    check_fields(fields, native_class)

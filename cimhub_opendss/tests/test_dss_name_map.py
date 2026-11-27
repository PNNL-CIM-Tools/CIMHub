"""The DSS name map: property names and class names resolve as the engine resolves them."""
from __future__ import annotations

import pytest

from cimhub_opendss.dss_name_map import build_type_registry, get_class_map
from cimhub_opendss.schema import opendss_schema as schema


def test_an_abbreviation_never_names_the_object():
    """The engine has no ``name`` property: ``New Loadshape.s n=2`` sets npts."""
    assert get_class_map(schema.Loadshape).field_for("n") == "npts"


def test_an_empty_property_name_raises():
    with pytest.raises(ValueError, match="unknown property '' on Load"):
        get_class_map(schema.Load).field_for("")


@pytest.mark.parametrize("dss_class", ["options", "buscoords"])
def test_deck_records_are_no_dss_class(dss_class):
    """``New Options.o`` and ``New Buscoords.b`` raise #263 (Object Type not found) in the engine."""
    assert dss_class not in build_type_registry()


def test_tcc_curve_is_the_engine_class_name():
    """The engine's class is ``TCC_Curve`` (``New TCC_Curve.t npts=2`` compiles)."""
    assert build_type_registry()["tcc_curve"] is schema.TccCurve

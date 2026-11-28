"""The DSS name map: property names and class names resolve as the engine resolves them."""
from __future__ import annotations

import opendssdirect as dss
import pytest

from cimhub_opendss.dss_name_map import build_type_registry, get_class_map
from cimhub_opendss.dss_reader import DssParseError, DssReader
from cimhub_opendss.schema import opendss_schema as schema

from conftest import clear_engine


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
    """The engine's class is ``TCC_Curve`` (General/TCC_Curve.pas:92): ``New TCC_Curve.x`` and ``New tcc_curve.x``
    compile."""
    assert build_type_registry()["tcc_curve"] is schema.TccCurve


@pytest.mark.parametrize("dss_class", ["tcccurve", "tcc curve"])
def test_a_class_name_the_engine_rejects_raises(tmp_path, dss_class):
    """``New tcccurve.x`` raises ``(#263) New Command: Object Type "tcccurve" not found`` in the engine, and
    ``New tcc curve.x`` raises #263 for ``Object Type ""``."""
    deck = tmp_path / "deck.dss"
    deck.write_text(f"New {dss_class}.x npts=2 C_array=[1 2] T_array=[1 2]\n")
    with pytest.raises(DssParseError, match="at line 1"):
        DssReader(deck).read_all()


def test_every_class_name_is_one_the_engine_accepts():
    """Each registry key is a class of opendssdirect 0.9.4, except ``circuit`` (the ``New Circuit`` command) and
    four classes EPRI's OpenDSS has and DSS C-API does not: ``New FMonitor.x``, ``New Generic5.x``, ``New
    PyControl.x`` and ``New WindGen.x`` raise #263 in opendssdirect, while EPRI names them in Meters/fMonitor.pas:296,
    PCElements/Generic5OrderMach.pas:387, Controls/pyControl.pas:90 and PCElements/WindGen.pas:266. The two engines
    disagree, so those four stay until that is decided."""
    clear_engine()
    engine = {name.lower() for name in dss.Basic.Classes()}
    assert set(build_type_registry()) - engine == {"circuit", "fmonitor", "generic5", "pycontrol", "windgen"}

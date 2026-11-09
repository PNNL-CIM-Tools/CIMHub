"""Compare two decks in the engine: the original and one written (or exported) from it.

Per element its buses and YPrim, then the solved node voltages, with controls off and a tight tolerance: solution
settings (``Set controlmode``) are not part of the model, and the tolerance makes both decks converge to one answer
from their different starting points. ``engine_settings`` reads named properties after Compile, for the settings a
YPrim does not show (a control's, a battery's).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import opendssdirect as dss
import pytest

from conftest import compile_deck


def engine_buses(path: Path) -> dict[str, tuple]:
    """``{element: (bus names, node order)}`` after Compile, without a solve (for a deck that does not converge)."""
    compile_deck(path)
    found = {}
    for name in dss.Circuit.AllElementNames():
        dss.Circuit.SetActiveElement(name)
        if not dss.CktElement.Enabled():  # no nodes, as in _engine_state
            found[name.lower()] = ("disabled",)
            continue
        found[name.lower()] = (tuple(bus.split(".")[0].lower() for bus in dss.CktElement.BusNames()),
                               tuple(dss.CktElement.NodeOrder()))
    return found


def _engine_state(path: Path) -> tuple[dict[str, tuple], dict[str, complex]]:
    """``({element: ((bus names, node order), YPrim)}, {node: voltage})``, solved with controls off and a tight tolerance."""
    compile_deck(path)
    dss.Text.Command("Set controlmode=off tolerance=1e-10 maxiterations=500")
    dss.Solution.Solve()
    assert dss.Solution.Converged(), path
    elements = {}
    for name in dss.Circuit.AllElementNames():
        dss.Circuit.SetActiveElement(name)
        if not dss.CktElement.Enabled():  # a disabled element has no nodes and no YPrim: both decks must disable it
            elements[name.lower()] = (("disabled",), np.array([]))
            continue
        # the engine's own connection: bus names and the node of each conductor (bare `650` = `650.1.2.3`)
        buses = (tuple(bus.split(".")[0].lower() for bus in dss.CktElement.BusNames()),
                 tuple(dss.CktElement.NodeOrder()))
        elements[name.lower()] = (buses, np.array(dss.CktElement.YPrim()))
    values = dss.Circuit.AllBusVolts()
    nodes = [name.lower() for name in dss.Circuit.AllNodeNames()]
    return elements, {node: complex(values[2 * i], values[2 * i + 1]) for i, node in enumerate(nodes)}


def assert_same_engine_state(original: Path, written: Path, *, by_element: bool = True,
                             bus_names: dict[str, str] | None = None, yprim_differs: frozenset[str] = frozenset(),
                             added: frozenset[str] = frozenset()) -> None:
    """The same elements (buses, YPrim) and node voltages. ``by_element=False`` compares the voltages only, for an
    export under another name source, which renames the elements; ``bus_names`` (original -> written, lowercased)
    maps its buses when it renames them too (``uri``). The listed differences (``Class.name``, lowercased):
    ``yprim_differs`` keep their buses but not their YPrim (a switch's invented impedance, B3), ``added`` are only in
    the written deck (a SwtControl for an open switch, E6)."""
    elements, voltages = _engine_state(original)
    written_elements, written_voltages = _engine_state(written)
    if by_element:
        _assert_same_elements(elements, written_elements, yprim_differs, added)
    if bus_names is not None:
        voltages = {_renamed(node, bus_names): voltage for node, voltage in voltages.items()}
    assert written_voltages.keys() == voltages.keys()
    for node, voltage in voltages.items():
        # YPrim is the exact check; 10 uV absolute covers a neutral node near zero
        assert abs(written_voltages[node] - voltage) <= 1e-8 * abs(voltage) + 1e-5, node


def _assert_same_elements(elements: dict, written_elements: dict, yprim_differs: frozenset[str],
                          added: frozenset[str]) -> None:
    assert written_elements.keys() == elements.keys() | added
    assert not added & elements.keys(), "an added element is in the original"
    for name, (buses, yprim) in elements.items():
        written_buses, written_yprim = written_elements[name]
        assert written_buses == buses, name
        if name not in yprim_differs:
            assert np.allclose(written_yprim, yprim, rtol=1e-9, atol=1e-12), name


def _renamed(node: str, bus_names: dict[str, str]) -> str:
    bus, _, conductor = node.partition(".")
    return f"{bus_names[bus]}.{conductor}"


def engine_settings(path: Path, properties: dict[str, tuple[str, ...]]) -> dict[str, dict[str, object]]:
    """``{element: {property: value}}`` after Compile for every element of a class in ``properties`` (``{'Load':
    ('kW', ...)}``); numbers as floats, text lowercased."""
    compile_deck(path)
    found = {}
    for name in dss.Circuit.AllElementNames():
        kind = name.split(".")[0]
        if kind in properties:
            dss.Circuit.SetActiveElement(name)
            found[name.lower()] = {prop: _value(dss.Properties.Value(prop)) for prop in properties[kind]}
    return found


def assert_same_settings(expected: dict, actual: dict, *, tolerance: dict[str, float] | None = None,
                         differs: frozenset[tuple[str, str]] = frozenset()) -> None:
    """The same elements, each property alike: text exactly, numbers to rel 1e-9 or ``tolerance[property]``. The
    listed ``differs`` (``(element, property)``) are not compared."""
    tolerance = tolerance or {}
    assert actual.keys() == expected.keys()
    for element, values in expected.items():
        for name, value in values.items():
            if (element, name) in differs:
                continue
            if isinstance(value, str):
                assert actual[element][name] == value, f"{element}.{name}"
            else:
                assert actual[element][name] == pytest.approx(value, rel=tolerance.get(name, 1e-9), abs=1e-12), \
                    f"{element}.{name}"


def _value(text: str) -> object:
    text = text.strip().lower()
    try:
        return float(text)
    except ValueError:
        return text

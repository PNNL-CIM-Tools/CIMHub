"""Compare two decks in the engine: the original and one written (or exported) from it.

Per element its buses and YPrim, then the solved node voltages, with controls off and a tight tolerance: solution
settings (``Set controlmode``) are not part of the model, and the tolerance makes both decks converge to one answer
from their different starting points.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import opendssdirect as dss

from conftest import compile_deck


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

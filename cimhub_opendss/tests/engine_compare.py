"""Compare two decks in the engine: the original and one written (or exported) from it.

Per element its buses and YPrim, then the solved node voltages, with controls off and a tight tolerance: solution
settings (``Set controlmode``) are not part of the model, and the tolerance makes both decks converge to one answer
from their different starting points. ``engine_settings`` reads named properties after Compile, for the settings a
YPrim does not show (a control's, a battery's).
"""
from __future__ import annotations

import math

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


# power flow parity (S6f) -------------------------------------------------------------------------------------------

#: settings CIM has no home for (E10, L6; the earth model since S6g only on a deck with geometry), and the control
#: state an in-deck ``Solve`` leaves (the importer reads the deck's text). The parity solve takes them from the
#: original; each is named when the written deck differed.
UNTRANSCRIBED = ("earthmodel", "Load.Vminpu/Vmaxpu", "Transformer.ppm_antifloat", "Transformer.taps",
                 "Capacitor.states")


def assert_same_power_flow(original: Path, written: Path, *, tolerance: float = 1e-3) -> set[str]:
    """Every node voltage within ``tolerance`` of its bus's base (0.1 %, plan section 5), both solved with controls
    off at the original's ``UNTRANSCRIBED`` settings and control state; the control settings themselves are compared
    one by one (``assert_same_settings``). Returns which of ``UNTRANSCRIBED`` the written deck had otherwise."""
    compile_deck(original)
    settings = _untranscribed()
    voltages, bases = _solved_voltages(original)
    compile_deck(written)
    dss.Text.Command("Get earthmodel")
    differed = set()
    if dss.Text.Result().lower() != settings["earthmodel"].lower():
        differed.add("earthmodel")
        written = _with_earth_model(written, settings["earthmodel"])
        compile_deck(written)
    differed |= _apply(settings)
    written_voltages, _ = _solved_voltages(written)
    assert written_voltages.keys() == voltages.keys()
    for node, voltage in voltages.items():
        assert abs(written_voltages[node] - voltage) <= tolerance * bases[node.split(".")[0]], node
    return differed


def _untranscribed() -> dict:
    """The compiled deck's ``UNTRANSCRIBED`` values."""
    dss.Text.Command("Get earthmodel")
    loads = {}
    for name in dss.Loads.AllNames() or []:
        dss.Loads.Name(name)
        loads[name] = (dss.Loads.Vminpu(), dss.Loads.Vmaxpu())
    transformers = {}
    for name in dss.Transformers.AllNames() or []:
        dss.Transformers.Name(name)
        taps = []
        for winding in range(1, dss.Transformers.NumWindings() + 1):
            dss.Transformers.Wdg(winding)
            taps.append(dss.Transformers.Tap())
        transformers[name] = (dss.Properties.Value("ppm_antifloat"), taps)
    capacitors = {}
    for name in dss.Capacitors.AllNames() or []:
        dss.Capacitors.Name(name)
        capacitors[name] = list(dss.Capacitors.States())
    return {"earthmodel": dss.Text.Result(), "loads": loads, "transformers": transformers, "capacitors": capacitors}


def _apply(settings: dict) -> set[str]:
    """Put ``settings`` on the compiled written deck; the names of those that differed."""
    differed = set()
    for name, limits in settings["loads"].items():
        dss.Loads.Name(name)
        if (dss.Loads.Vminpu(), dss.Loads.Vmaxpu()) != limits:
            dss.Loads.Vminpu(limits[0])
            dss.Loads.Vmaxpu(limits[1])
            differed.add("Load.Vminpu/Vmaxpu")
    for name, (ppm, taps) in settings["transformers"].items():
        dss.Transformers.Name(name)
        if dss.Properties.Value("ppm_antifloat") != ppm:
            dss.Text.Command(f"Transformer.{name}.ppm_antifloat={ppm}")
            differed.add("Transformer.ppm_antifloat")
        for winding, tap in enumerate(taps, 1):
            dss.Transformers.Wdg(winding)
            if dss.Transformers.Tap() != tap:
                dss.Transformers.Tap(tap)
                differed.add("Transformer.taps")
    for name, states in settings["capacitors"].items():
        dss.Capacitors.Name(name)
        if list(dss.Capacitors.States()) != states:
            dss.Capacitors.States(states)
            differed.add("Capacitor.states")
    return differed


def _with_earth_model(written: Path, earth_model: str) -> Path:
    """A copy of ``written`` that sets ``earth_model`` before any line is built (after it, Compile has used it)."""
    lines = written.read_text(encoding="utf-8").splitlines()
    circuit = next(number for number, line in enumerate(lines) if line.lower().startswith("new circuit."))
    lines.insert(circuit + 1, f"Set earthmodel={earth_model}")
    copy = written.with_name(f"{written.stem}_parity{written.suffix}")
    copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return copy


def _solved_voltages(path: Path) -> tuple[dict[str, complex], dict[str, float]]:
    """``({node: voltage (V)}, {bus: base (V, LN)})`` solved with controls off."""
    dss.Text.Command("Set controlmode=off maxiterations=100")
    dss.Solution.Solve()
    assert dss.Solution.Converged(), path
    values = dss.Circuit.AllBusVolts()
    nodes = [name.lower() for name in dss.Circuit.AllNodeNames()]
    bases = {}
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        bases[bus.lower()] = dss.Bus.kVBase() * 1000
        assert bases[bus.lower()] > 0, f"{path.name}: bus {bus} has no voltage base"
    return {node: complex(values[2 * i], values[2 * i + 1]) for i, node in enumerate(nodes)}, bases


def engine_coordinates(path: Path) -> dict[str, tuple[float, float]]:
    """``{bus: (x, y)}`` after Compile, for every bus with coordinates."""
    compile_deck(path)
    found = {}
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        if dss.Bus.Coorddefined():
            found[bus.lower()] = (dss.Bus.X(), dss.Bus.Y())
    return found


#: float noise allowed on an exported bus coordinate: a bus only a device point places is solved from the
#: importer's midpoint, (a + b) / 2, which rounded a + b once
COORDINATE_REL_TOL, COORDINATE_ABS_TOL = 1e-12, 1e-9


def assert_same_coordinates(written: Path, original: Path) -> None:
    """The written deck's buses have coordinates where the original's do, equal to float noise."""
    ours, theirs = engine_coordinates(written), engine_coordinates(original)
    assert sorted(ours) == sorted(theirs)
    differences = {bus: (ours[bus], theirs[bus]) for bus in theirs
                   if not all(math.isclose(a, b, rel_tol=COORDINATE_REL_TOL, abs_tol=COORDINATE_ABS_TOL)
                              for a, b in zip(ours[bus], theirs[bus]))}
    assert differences == {}

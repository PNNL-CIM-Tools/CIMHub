"""Tier 4: the IEEE 13 GLM import against the DSS import of the same model (GLM S5-3, GLM-16).

IEEE13_cdpsm.glm is the Java CIMHub export of the model the DSS importer's IEEE13_CDPSM golden holds. This binds the
two committed golden directories with cimtables alone (no spoke, no engine), matches equipment by its terminal buses,
and compares through the core getters in SI. Each expected difference is asserted as a difference, so a change on
either side shows (``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s5-the-deck-sweep-tier-4-and-g7``).
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import cimtables
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.control import get_tap_changer_control
from cimhub_core.getters.der import get_der_output, get_inverter_rating
from cimhub_core.getters.line_impedance import get_line_phase_impedance_matrix
from cimhub_core.getters.load import get_phase_loads
from cimhub_core.getters.shunt import get_shunt_reactive_power
from cimhub_core.getters.source import get_source
from cimhub_core.getters.switch_state import get_switch_state
from cimhub_core.getters.tap_changer import get_tap_steps
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from cimhub_core.getters.transformer import get_transformer_model, get_transformer_units

ROOT = Path(__file__).parents[2]
MASTERS = {
    "dss": ROOT / "cimhub_opendss" / "tests" / "goldens" / "IEEE13_CDPSM" / "IEEE13_CDPSM.cimtbl",
    "glm": ROOT / "cimhub_gridlabd" / "tests" / "goldens" / "IEEE13_cdpsm" / "IEEE13_cdpsm.cimtbl",
}
SWITCHES = (cim.LoadBreakSwitch, cim.Fuse, cim.Recloser, cim.Breaker)


@pytest.fixture(scope="module")
def dss_glm():
    with cim_scope():
        yield tuple(cimtables.load_model(MASTERS[side]) for side in ("dss", "glm"))


def buses(equipment) -> tuple[str, ...]:
    return tuple(sorted(str(node.name) for node in get_terminal_nodes(equipment)))


def phases(equipment) -> str:
    return "".join(sorted(phase.name for phase in get_conductor_phases(equipment)))


def by_buses(network, *classes) -> dict:
    found = {}
    for cls in classes:
        for equipment in network.list_by_class(cls):
            assert buses(equipment) not in found, buses(equipment)
            found[buses(equipment)] = equipment
    return found


def assert_close(actual, expected, what, rel: float | None = None) -> None:
    """Equal within ``pytest.approx``'s tolerance on floats, through tuples, lists and dicts (approx stops at one
    level)."""
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), what
        for key in expected:
            assert_close(actual[key], expected[key], (what, key), rel)
    elif isinstance(expected, (tuple, list)):
        assert len(actual) == len(expected), what
        for actual_item, expected_item in zip(actual, expected, strict=True):
            assert_close(actual_item, expected_item, what, rel)
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=rel), what
    else:
        assert actual == expected, what


def both(dss_glm, *classes) -> list[tuple]:
    """The equipment of ``classes`` paired by terminal buses; both sides must have the same set."""
    dss, glm = (by_buses(network, *classes) for network in dss_glm)
    assert dss.keys() == glm.keys()
    return [(dss[key], glm[key]) for key in sorted(dss)]


# -- equal ---------------------------------------------------------------------------------------------------------

def test_buses(dss_glm):
    """The bus names agree; DSS adds the substation transformer's tertiary bus (expected difference 2)."""
    dss, glm = ({str(node.name) for node in network.list_by_class(cim.ConnectivityNode)} for network in dss_glm)
    assert dss - glm == {"650z"} and glm <= dss


def base_voltages(network) -> dict:
    """(class, buses) -> the line-to-line base voltages there (DSS has several consumers on one bus)."""
    found = defaultdict(set)
    for cls in (cim.ACLineSegment, cim.EnergyConsumer, cim.LinearShuntCompensator):
        for equipment in network.list_by_class(cls):
            found[(cls.__name__, buses(equipment))].add(get_base_voltage(equipment, "V", form="LL"))
    return found


def test_base_voltages(dss_glm):
    dss, glm = (base_voltages(network) for network in dss_glm)
    assert glm == dss


def ohms(line) -> dict[tuple[str, str], tuple[float, float, float | None]]:
    """The line's phase matrix in ohms (and siemens), keyed by phase pair, so conductor order does not matter."""
    matrix = get_line_phase_impedance_matrix(line, "ohm/m", "S/m")
    length = float(line.length.to("m"))
    names = [phase.name for phase in matrix.phases]
    values = {}
    for (row, column), r in matrix.r.items():
        pair = tuple(sorted((names[row - 1], names[column - 1])))
        b = None if matrix.b is None else matrix.b[(row, column)] * length
        values[pair] = (r * length, matrix.x[(row, column)] * length, b)
    return values


def test_lines(dss_glm):
    for dss, glm in both(dss_glm, cim.ACLineSegment):
        assert phases(glm) == phases(dss), buses(dss)
        assert float(glm.length.to("m")) == pytest.approx(float(dss.length.to("m")))
        assert_close(ohms(glm), ohms(dss), buses(dss))


def test_switches(dss_glm):
    for dss, glm in both(dss_glm, *SWITCHES):
        assert type(glm) is type(dss) and phases(glm) == phases(dss), buses(dss)
        assert get_switch_state(glm, which="normal") == get_switch_state(dss, which="normal")


def phase_power(network) -> dict:
    """p, q by bus and phase: DSS has one EnergyConsumer per DSS Load (16), GLM one per GLM load (10)."""
    totals = defaultdict(lambda: [0.0, 0.0])
    for consumer in network.list_by_class(cim.EnergyConsumer):
        for phase, power in get_phase_loads(consumer).per_phase.items():
            total = totals[(buses(consumer), phase.name)]
            total[0] += power.p
            total[1] += power.q
    return {key: tuple(value) for key, value in totals.items()}


def test_loads(dss_glm):
    dss, glm = (phase_power(network) for network in dss_glm)
    assert_close(glm, dss, "loads", rel=1e-5)  # the Java export writes 6 digits (646's impedance load: 0.09 W)


def test_capacitors(dss_glm):
    for dss, glm in both(dss_glm, cim.LinearShuntCompensator):
        assert phases(glm) == phases(dss), buses(dss)
        assert (get_shunt_reactive_power(glm, sections="normal", voltage="nominal").total
                == pytest.approx(get_shunt_reactive_power(dss, sections="normal", voltage="nominal").total))
        assert glm.RegulatingControl is None and dss.RegulatingControl is None


def taps(network) -> dict:
    return {str(tap.TapChangerControl.monitoredPhase.value): tap for tap in network.list_by_class(cim.RatioTapChanger)}


def test_regulator_taps(dss_glm):
    dss, glm = (taps(network) for network in dss_glm)
    assert dss.keys() == glm.keys() == {"A", "B", "C"}
    for phase in dss:
        # neutralU is expected difference 4
        assert_close(get_tap_steps(glm[phase])._replace(neutral_u=None),
                     get_tap_steps(dss[phase])._replace(neutral_u=None), phase)


def model_of(transformer):
    units = get_transformer_units(transformer)
    assert len(units) == 1, f"{transformer.mRID}: a bank; IEEE 13 has none"
    return get_transformer_model(units[0])


def winding_ratings(model) -> list[tuple]:
    return [(winding.rated_s, winding.rated_u, winding.connection) for winding in model.windings]


def impedances(model) -> tuple[list, dict]:
    return [winding.r for winding in model.windings], {pair: tuple(mesh) for pair, mesh in model.mesh.items()}


def test_transformers(dss_glm):
    """The distribution transformer and the house center tap: ratings, voltages, connections, impedance, core. GLM's
    %Z on the template reads back as the DSS mesh, the center tap by its Hopkinson split (S3b-5)."""
    dss, glm = (by_buses(network, cim.PowerTransformer) for network in dss_glm)
    for key in (("634", "xf1"), ("670", "house")):
        dss_model, glm_model = model_of(dss[key]), model_of(glm[key])
        assert_close(winding_ratings(glm_model), winding_ratings(dss_model), key)
        assert_close(impedances(glm_model), impedances(dss_model), key)
        assert_close(glm_model.core, dss_model.core, key)


# -- expected differences (the spec's numbered list) ----------------------------------------------------------------

def test_1_source(dss_glm):
    """DSS: 30 deg and the deck's short-circuit impedance; GLM: 0 deg and the stiff default (S1-3)."""
    (dss,), (glm,) = (network.list_by_class(cim.EnergySource) for network in dss_glm)
    dss_source, glm_source = (get_source(source, angle_unit="deg") for source in (dss, glm))
    assert glm_source.magnitude == pytest.approx(dss_source.magnitude) == 115_000
    assert (dss_source.angle, glm_source.angle) == (pytest.approx(30), 0)
    assert glm_source.impedance.x == pytest.approx(10 * glm_source.impedance.r)  # X/R 10
    assert glm_source.impedance != pytest.approx(dss_source.impedance)


def test_2_substation_transformer(dss_glm):
    """DSS has a 13.2 kV tertiary on 650z; the Java export wrote two windings. The two it has agree."""
    dss, glm = (by_buses(network, cim.PowerTransformer) for network in dss_glm)
    dss_model = model_of(dss[("650", "650z", "sourcebus")])
    glm_model = model_of(glm[("650", "sourcebus")])
    assert (len(dss_model.windings), len(glm_model.windings)) == (3, 2)
    assert dss_model.windings[2].rated_u == 13_200
    assert_close(winding_ratings(glm_model), winding_ratings(dss_model)[:2], "substation")
    dss_r, dss_mesh = impedances(dss_model)
    assert_close(impedances(glm_model), (dss_r[:2], {(1, 2): dss_mesh[(1, 2)]}), "substation")


def test_4_regulator_controls(dss_glm):
    """The Java export wrote Control MANUAL with the band commented out: GLM's controls are off with no target, and
    the core getter cannot read them (S5-4). GLM's line drop is 1/5 of DSS's: the export wrote DSS's CT ratio
    (700 A / 0.2 A), which GridLAB-D reads as on a 1 A secondary (S5-5). neutralU: DSS's 2.4 kV winding; GLM's coil,
    the 4.16 kV bus over sqrt 3 (S3c)."""
    dss, glm = (taps(network) for network in dss_glm)
    for phase in dss:
        settings = get_tap_changer_control(dss[phase])
        assert (settings.control.target, settings.control.deadband, settings.control.enabled) == (2440, 40, True)
        assert (get_tap_steps(dss[phase]).neutral_u, get_tap_steps(glm[phase]).neutral_u) == (2400, 2401.78)
        control = glm[phase].TapChangerControl
        assert (control.enabled, control.targetValue) == (False, None)
        with pytest.raises(ValueError, match="targetValue is unset"):
            get_tap_changer_control(glm[phase])
        for name in ("lineDropR", "lineDropX"):
            assert float(getattr(control, name).to("ohm")) * 5 == pytest.approx(
                float(getattr(dss[phase].TapChangerControl, name).to("ohm")))


def der(network) -> dict:
    """(bus, unit class) -> sorted (p, ratedS) of the connections there, generation positive."""
    found = defaultdict(list)
    for connection in network.list_by_class(cim.PowerElectronicsConnection):
        (unit,) = connection.PowerElectronicsUnit
        output = get_der_output(connection, sign="generation")
        found[(buses(connection), type(unit).__name__)].append(
            (output.total.p, get_inverter_rating(connection, sign="generation").rated_s))
    return {key: sorted(values) for key, values in found.items()}


def test_5_der(dss_glm):
    """The S4b cross-solver note: the batteries and the ratings agree; the PV is GridLAB-D's static-weather output,
    not the P written, and the house's DER sit across the legs at 240 V where the DSS shape has Y at 208 V."""
    dss, glm = (der(network) for network in dss_glm)
    assert dss.keys() == glm.keys()
    for key in dss:
        if key[1] == "BatteryUnit":
            assert_close(glm[key], dss[key], key)
    assert_close(dss[(("634",), "PhotoVoltaicUnit")], [(240_000.0, 300_000.0)], "school PV")
    assert_close(dss[(("house",), "PhotoVoltaicUnit")], [(4_000.0, 5_000.0)], "house PV")
    [(school, _)], [(house, _)] = glm[(("634",), "PhotoVoltaicUnit")], glm[(("house",), "PhotoVoltaicUnit")]
    assert (school, house) == (pytest.approx(298_254.5, abs=0.1), pytest.approx(4_970.9, abs=0.1))
    for network, connection, rated_u in zip(dss_glm, (cim.PhaseShuntConnectionKind.Y, cim.PhaseShuntConnectionKind.D),
                                            (208, 240), strict=True):
        house = [pec for pec in network.list_by_class(cim.PowerElectronicsConnection) if buses(pec) == ("house",)]
        assert len(house) == 2
        for pec in house:
            assert (pec.phaseConnection, get_inverter_rating(pec, sign="generation").rated_u) == (connection, rated_u)

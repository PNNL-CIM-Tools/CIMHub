"""S4b: inverters with their solar or battery: classification, the atom, GridLAB-D's output through the core DER
getters, fail fast; the decks run in
test_cimtbl_sweep.py."""
from __future__ import annotations

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_core.getters.der import (get_battery_unit, get_der_output, get_inverter_rating, get_inverter_unit,
                                     get_photovoltaic_unit)
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.cimtbl import inverter
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

ATOM = Path(__file__).parent / "atoms" / "inverter"
MODEL = "atom"


def read(path: Path, **kwargs):
    return GlmReader(path, **kwargs).read_all()


def inverter_part(model, name: str):
    return next(part for part in GlmImporter(name).to_cimtbl(model).parts if part.name == "inverter")


@pytest.mark.parametrize("native", (schema.Inverter, schema.Solar, schema.Battery), ids=("inverter", "solar",
                                                                                         "battery"))
def test_every_slot_is_classified(native):
    check_fields(inverter.CLASSIFIED[native], native)


# -- GridLAB-D's output, written out again from the C++ (not from the mapper) -------------------------------------

def gridlabd_pv_ac(solar, inv) -> float:
    """``solar.cpp:1170``, ``:1218-1222`` with no climate (59 degF, Rated_Insolation x shading), then the inverter's
    efficiency (``inverter.cpp:3290``) and its |S| cap (``:3798``); W, generation positive. Every value here is in
    GridLAB-D's default unit (W, W/sf, degF), as the decks and the atom write them."""
    panels = {"MULTI_CRYSTAL_SILICON": -0.00416 / 33.8, "SINGLE_CRYSTAL_SILICON": -0.00437 / 33.8}
    rated_ins = 92.902 if solar.Rated_Insolation is None else float(solar.Rated_Insolation)
    shading = 1.0 if solar.shading_factor is None else float(solar.shading_factor)
    noct = 118.4 if solar.NOCT is None else float(solar.NOCT)
    coefficient = (panels[str(solar.panel_type or "SINGLE_CRYSTAL_SILICON")] if solar.Pmax_temp_coeff is None
                   else float(solar.Pmax_temp_coeff))
    derating = 0.95 if solar.derating is None else float(solar.derating)
    soiling = 0.95 if solar.soiling is None else float(solar.soiling)
    insolation = rated_ins * shading
    t_module = 59.0 + (noct - 68.0) / 74.32 * insolation
    dc = float(solar.rated_power) * insolation / rated_ins * (1 + coefficient * (t_module - 77.0)) * derating * soiling
    efficiency = float(inv.inverter_efficiency or 0.9)
    return min(dc * efficiency, rated_s(inv))


def gridlabd_battery(battery, inv) -> float:
    """CONSTANT_PQ (``inverter.cpp:3485-3540``): P_Out, 0 into a full battery or out of one at its reserve, capped at
    |S|; W, generation positive."""
    p_out, soc, reserve = float(inv.P_Out or 0), float(battery.state_of_charge), float(inv.soc_reserve or 0)
    if (soc >= 1 and p_out < 0) or (soc <= reserve and p_out > 0):
        return 0.0
    return math.copysign(min(abs(p_out), rated_s(inv)), p_out)


def phase_count(inv) -> int:
    return 1 if "S" in str(inv.phases) else sum(letter in str(inv.phases) for letter in "ABC")


def rated_s(inv) -> float:
    return float(inv.rated_power) * phase_count(inv)


def children(model, inv):
    return [record for cls in (schema.Solar, schema.Battery) for record in model.list_by_class(cls)
            if str(record.parent) == str(inv.name)]


def assert_gridlabd_der(model, network) -> int:
    """Every inverter reads back through the core DER getters as GridLAB-D runs it (S4b-2, -4, -5, -7, -9)."""
    connections = {str(pec.mRID): pec for pec in network.list_by_class(cim.PowerElectronicsConnection)}
    checked = 0
    for inv in model.list_by_class(schema.Inverter):
        (unit_record,) = children(model, inv)
        solar = isinstance(unit_record, schema.Solar)
        pec = connections[f"{'pv_' if solar else 'storage_'}{inv.name}"]
        online = str(inv.generator_status or "ONLINE") == "ONLINE"
        expected = (gridlabd_pv_ac(unit_record, inv) if solar else gridlabd_battery(unit_record, inv)) if online else 0
        output = get_der_output(pec, sign="generation")
        assert output.total.p == pytest.approx(expected), inv.name
        assert output.total.q == 0.0
        split = "S" in str(inv.phases)
        assert output.connection == (cim.PhaseShuntConnectionKind.D if split else cim.PhaseShuntConnectionKind.Y)
        rating = get_inverter_rating(pec, sign="generation")
        assert rating.rated_s == pytest.approx(rated_s(inv))
        assert (rating.min_q, rating.max_q) == (pytest.approx(-rated_s(inv)), pytest.approx(rated_s(inv)))
        bus_kv = float(pec.BaseVoltage.nominalVoltage.to("kV"))
        assert rating.rated_u == pytest.approx(bus_kv * 1000)  # line to line (S4b-5)
        assert pec.normallyInService is online
        unit = get_inverter_unit(pec)
        if solar:
            pv = get_photovoltaic_unit(unit, sign="generation")
            assert (pv.min_p, pv.max_p) == (0.0, float(unit_record.rated_power))
            assert isinstance(pec.AssetDatasheet, cim.GenerationInverterInfo)
            assert isinstance(unit.AssetDatasheet, cim.SolarArrayInfo) and unit.AssetDatasheet.SolarPanels
        else:
            battery = get_battery_unit(unit, sign="generation")
            capacity = float(unit_record.battery_capacity) * (1000 if model.unit(unit_record, "battery_capacity")
                                                              == "kWh" else 1)
            assert battery.rated_e == pytest.approx(capacity)
            assert battery.stored_e == pytest.approx(float(unit_record.state_of_charge) * capacity)
            assert battery.charging_efficiency == pytest.approx(
                100 * math.sqrt(float(unit_record.round_trip_efficiency or 0.8)))
            state = "discharging" if expected > 0 else "charging" if expected < 0 else "waiting"
            assert battery.state.value == state, inv.name
            assert isinstance(pec.AssetDatasheet, cim.StorageInverterInfo)
            assert isinstance(unit.AssetDatasheet, cim.BatteryInfo)
        checked += 1
    return checked


# -- tier 1 / 1b: the atom ----------------------------------------------------------------------------------------

def test_atom_golden():
    assert_matches_golden(inverter_part(read(ATOM / "inverter.glm"), MODEL), ATOM / "inverter.inverter.cimtbl")


def test_atom_binds(scope):
    model = read(ATOM / "inverter.glm")
    network = glm_to_cim(model, name=MODEL)
    assert assert_gridlabd_der(model, network) == 8
    pecs = {str(pec.mRID): pec for pec in network.list_by_class(cim.PowerElectronicsConnection)}
    # split phase sits across the legs at 240 V; the DC output above rated_power is capped
    pvs = pecs["pv_inv_pvs"]
    assert (pvs.phaseConnection.value, float(pvs.ratedU.to("V")), float(pvs.p.to("W"))) == ("D", 240.0, -5000.0)
    # the Java defect: a CONSTANT_PF battery charges at its P_Out, read as CONSTANT_PQ
    assert float(pecs["storage_inv_bpf"].p.to("W")) == 3000.0
    # a full battery does not charge; one at its reserve does not discharge
    assert float(pecs["storage_inv_bfull"].p.to("W")) == float(pecs["storage_inv_bres"].p.to("W")) == 0.0
    # the irradiance is GridLAB-D's static weather by the shading factor
    pv3 = next(unit for unit in network.list_by_class(cim.PhotoVoltaicUnit) if str(unit.mRID) == "pv_inv_pv3_unit")
    assert float(pv3.irradiance.to("W/m**2")) == pytest.approx(800, rel=1e-4)
    assert float(pv3.AssetDatasheet.tiltAngle.to("deg")) == 30.0
    lead = next(info for info in network.list_by_class(cim.BatteryInfo) if str(info.mRID).startswith("storage_inv_bfull"))
    assert (lead.batteryType.value, lead.numberOfCells) == ("leadAcid", None)


# -- fail fast -------------------------------------------------------------------------------------------------------

def raises(tmp_path, text: str, match: str):
    """The line atom plus ``text`` must raise ``match``."""
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM.parent / "line" / "line.glm"}"\n'
                    "object meter { name mx; parent n2; phases ABCN; nominal_voltage 2401.78; }\n" + text)
    with pytest.raises(ValueError, match=match):
        GlmImporter(MODEL).to_cimtbl(read(path))


_SOLAR = "object solar { name s; rated_power 1000; };"
_BATTERY = "object battery { name b; use_internal_battery_model true; battery_capacity 1000; state_of_charge 0.5; " \
           "rated_power 1000; };"


def _inverter(body: str, child: str = _SOLAR) -> str:
    return f"object inverter {{ name x; parent mx; phases ABCN; inverter_type FOUR_QUADRANT; rated_power 1000; " \
           f"{body} {child} }}\n"


def test_no_unit_raises(tmp_path):
    raises(tmp_path, _inverter("", child=""), "has 0 solar or battery children")


def test_hybrid_raises(tmp_path):
    raises(tmp_path, _inverter("", child=_SOLAR + _BATTERY), "has 2 solar or battery children")


def test_solar_outside_an_inverter_raises(tmp_path):
    raises(tmp_path, "object solar { name s; parent mx; rated_power 1000; }\n", "parent mx is not an inverter")


def test_other_inverter_type_raises(tmp_path):
    raises(tmp_path, "object inverter { name x; parent mx; phases ABCN; rated_power 1000; " + _SOLAR + " }\n",
           "inverter_type unset \\(PWM\\); FOUR_QUADRANT is mapped")


def test_volt_var_raises(tmp_path):
    raises(tmp_path, _inverter("four_quadrant_control_mode VOLT_VAR;"), "VOLT_VAR on a solar; CONSTANT_PF is mapped")


def test_constant_pq_solar_raises(tmp_path):
    raises(tmp_path, _inverter("four_quadrant_control_mode CONSTANT_PQ;"), "CONSTANT_PQ on a solar")


def test_power_factor_below_one_raises(tmp_path):
    raises(tmp_path, _inverter("power_factor 0.9;"), "power_factor 0.9; \\|pf\\| < 1 is not mapped")


def test_battery_reactive_set_point_raises(tmp_path):
    raises(tmp_path, _inverter("four_quadrant_control_mode CONSTANT_PQ; Q_Out 100;", child=_BATTERY),
           "Q_Out 100.0; a non-zero CONSTANT_PQ Q is not mapped")


def test_unrated_inverter_raises(tmp_path):
    raises(tmp_path, "object inverter { name x; parent mx; phases ABCN; inverter_type FOUR_QUADRANT; "
                     + _SOLAR + " }\n", "rated_power unset or 0; GridLAB-D would use 25 kVA")


def test_climate_raises(tmp_path):
    raises(tmp_path, "object climate { name w; }\n" + _inverter(""), "a climate object")


def test_panel_area_raises(tmp_path):
    raises(tmp_path, _inverter("", child="object solar { name s; rated_power 1000; area 100; };"),
           "area 100.0; not mapped")


def test_legacy_battery_raises(tmp_path):
    raises(tmp_path, _inverter("", child=_BATTERY.replace("true", "false")),
           "use_internal_battery_model false; the legacy model is not mapped")


def test_multipoint_efficiency_raises(tmp_path):
    raises(tmp_path, _inverter("use_multipoint_efficiency TRUE;"), "use_multipoint_efficiency TRUE; not mapped")

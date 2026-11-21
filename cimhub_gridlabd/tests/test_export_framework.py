"""The exporter's framework and its pure rules (EXPORT_MAPPING.md): SLOTS cover every schema slot, names, the
transformer forms (X2-X4, the bank rule), the regulator bank letters and the tape-shield formulas."""
from __future__ import annotations

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.export_slots import check_slots, slots_table
from cimhub_core.getters.transformer import (CoreAdmittance, MeshImpedance, TransformerForm, TransformerModel,
                                             Winding)
from cimhub_gridlabd.exporter import line_catalog, regulator, transformer
from cimhub_gridlabd.exporter.cim_to_glm import EXPORT_ORDER, GlmExporter
from cimhub_gridlabd.exporter.naming import Names, glm_safe_name

SPEC = Path(__file__).parents[1] / "docs" / "EXPORT_MAPPING.md"
A, B, C, N = (cim.SinglePhaseKind(letter) for letter in "ABCN")
Y, YN, D = cim.WindingConnection.Y, cim.WindingConnection.Yn, cim.WindingConnection.D


def test_slots_cover_every_schema_slot():
    for module in EXPORT_ORDER:
        for native_class, slots in module.SLOTS.items():
            check_slots(slots, native_class)


def spec_table(slots: dict, native_class: type) -> str:
    """A class's spec table: every slot the exporter writes, rules or leaves out on purpose; the rest counted."""
    shown = {name: slot for name, slot in slots.items() if slot.kind != "unset"}
    unset = len(slots) - len(shown)
    return f"### {native_class.class_name}\n\n{slots_table(shown, 'GLM')}\n\n{unset} other slots: unset"


def spec_tables() -> str:
    return "\n\n".join(spec_table(slots, native_class) for module in EXPORT_ORDER
                       for native_class, slots in module.SLOTS.items())


def test_the_spec_tables_are_the_slots():
    """``EXPORT_MAPPING.md`` holds the tables generated from SLOTS, so the spec cannot drift from the code."""
    assert spec_tables() in SPEC.read_text(), "regenerate the slot tables: print(spec_tables())"


@pytest.mark.parametrize(("text", "safe"), [("632", "632"), ("lcon 601.ABC", "lcon_601_ABC"),
                                            ("line_spacing:10", "line_spacing_10"), ("tpc_triplex_4/0 AA",
                                                                                     "tpc_triplex_4/0_AA")])
def test_glm_safe_name(text, safe):
    assert glm_safe_name(text) == safe


def test_two_objects_on_one_name_raise():
    names = Names("name")
    names.name(cim.ConnectivityNode(mRID="n1", name="a.b"))
    with pytest.raises(ValueError, match=r"ACLineSegment 'l1' and 'n1' are both named 'a_b' in GLM"):
        names.name(cim.ACLineSegment(mRID="l1", name="a:b"))


def test_equipment_no_module_exports_raises():
    class Network:
        graph = {cim.SynchronousMachine: {"g": cim.SynchronousMachine(mRID="g")}}

    with pytest.raises(ValueError, match=r"no GLM export yet for \{'SynchronousMachine': 1\}"):
        GlmExporter().to_model(Network())


# transformer forms (X2-X4) ----------------------------------------------------------------------------------------


def winding(number: int, phases, connection, rated_u: float, rated_s: float = 500.0, r: float = 0.005,
            phase_shift=None) -> Winding:
    return Winding(number, cim.PowerTransformerEnd(mRID=f"end_{number}"), tuple(phases), connection, None, None, None,
                   rated_u, rated_s, None, None, r, phase_shift)


@pytest.mark.parametrize(("first", "second", "expected"), [
    (winding(1, (A, B, C, N), Y, 4160), winding(2, (A, B, C, N), YN, 480), "WYE_WYE"),
    (winding(1, (B, N), YN, 4160), winding(2, (B, N), YN, 240), "SINGLE_PHASE"),
    (winding(1, (A, B, C), D, 4160), winding(2, (A, B, C), D, 480), "DELTA_DELTA"),
    (winding(1, (A, B, C), D, 115000), winding(2, (A, B, C, N), YN, 4160), "DELTA_GWYE"),
    (winding(1, (A, B, C), D, 115000), winding(2, (A, B, C, N), YN, 4160, phase_shift=-30.0), "DELTA_GWYE"),
    # every other model has no native GridLAB-D form: the wye-wye replacement (X3)
    (winding(1, (A, B, C), D, 115000), winding(2, (A, B, C, N), YN, 4160, phase_shift=30.0), None),  # Dyn11
    (winding(1, (A, B, C), D, 4160), winding(2, (A, B, C, N), Y, 480), None),  # an ungrounded wye
    (winding(1, (A, B, C, N), YN, 4160), winding(2, (A, B, C), D, 480), None),  # YNd
    (winding(1, (A, N), YN, 7200), winding(2, (A, B), D, 4160), None),  # an open-delta can
])
def test_native_connect_types(first, second, expected):
    assert transformer.native_connect_type((first, second)) == expected


def model(windings, mesh, base_power=500.0) -> TransformerModel:
    return TransformerModel(TransformerForm.BY_ENDS, tuple(windings), mesh, CoreAdmittance(None, None), base_power)


def test_the_star_of_three_windings():
    """Zi = (Zij + Zik - Zjk) / 2, the windings' r in each pair (the YYD can's: XHL 7.5, XHT 36, XLT 28 percent)."""
    windings = [winding(1, (A, N), YN, 39830, r=0.0011), winding(2, (A, N), YN, 7620, r=0.0011),
                winding(3, (A, B), D, 2400, rated_s=166.6, r=0.0055)]
    mesh = {(1, 2): MeshImpedance(None, 0.075), (1, 3): MeshImpedance(None, 0.36), (2, 3): MeshImpedance(None, 0.28)}
    first, second, third = transformer._star(model(windings, mesh))
    assert (first.real, first.imag) == pytest.approx((0.0011, (0.075 + 0.36 - 0.28) / 2))
    assert (second.real, second.imag) == pytest.approx((0.0011, (0.075 + 0.28 - 0.36) / 2))  # negative: the floor
    assert (third.real, third.imag) == pytest.approx((0.0055, (0.36 + 0.28 - 0.075) / 2))


def test_a_branch_that_is_not_positive_takes_the_floor():
    assert transformer._positive(complex(0.0011, -0.0025), "x") == complex(0.0011, transformer.FLOOR)
    assert transformer._positive(complex(0.0, 0.02), "x") == complex(transformer.FLOOR, 0.02)


def test_a_bank_of_open_delta_cans():
    """Two cans A-N to A-B and B-N to B-C: winding 1 a wye on A, B; winding 2 a delta on A, B, C; ratedS summed."""
    mesh = {(1, 2): MeshImpedance(None, 0.06)}
    cans = [model([winding(1, (A, N), YN, 12470, 2000), winding(2, (A, B), D, 4160, 2000)], mesh, 2000),
            model([winding(1, (B, N), YN, 12470, 2000), winding(2, (B, C), D, 4160, 2000)], mesh, 2000)]
    bank = transformer.bank_model(cans)
    first, second = bank.windings
    assert (first.phases, first.connection, first.rated_s) == ((A, B, N), YN, 4000)
    assert (second.phases, second.connection, second.rated_s) == ((A, B, C), D, 4000)
    assert bank.base_power == 4000
    assert transformer.native_connect_type(bank.windings) is None  # an open delta: the wye-wye replacement


def test_a_bank_of_unlike_cans_raises():
    cans = [model([winding(1, (A, N), YN, 12470), winding(2, (A, B), D, 4160)], {(1, 2): MeshImpedance(None, 0.06)}),
            model([winding(1, (B, N), YN, 12470), winding(2, (B, C), D, 4160)], {(1, 2): MeshImpedance(None, 0.07)})]
    with pytest.raises(ValueError, match="only like cans are written as a bank"):
        transformer.bank_model(cans)


@pytest.mark.parametrize(("coils", "expected"), [(["AB", "BC"], ["A", "C"]), (["AB", "BC", "AC"], ["A", "B", "C"]),
                                                 (["BC", "AC"], ["B", "A"])])
def test_regulator_bank_letters(coils, expected):
    assert regulator._bank_letters(coils) == expected


def test_tape_shield_formulas_match_the_java_exports():
    """IEEE13_assets' tscab_ts_1/0: diameterOverScreen 0.87 in, tape 5 mil -> shield_gmr 0.03625 ft, 4.327833 ohm/mi
    (the Java exports carry one more digit of Kersting's 18.826: 4e-6 apart)."""
    assert line_catalog.tape_shield_gmr(0.87 / 12) == pytest.approx(0.03625)
    assert line_catalog.tape_shield_resistance(0.87, 5.0) == pytest.approx(4.327833, rel=1e-5)


def test_the_coil_factor_of_a_two_phase_wye():
    assert transformer._coil_factor(2, "WYE_WYE") == pytest.approx(2 / 3)
    assert transformer._coil_factor(3, "WYE_WYE") == transformer._coil_factor(1, "SINGLE_PHASE") == 1.0
    assert math.isclose(transformer.STAR_VOLTAGE, 1000.0)

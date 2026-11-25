"""cimhub_core.getters.transformer: one model of windings, mesh and core from each CIM transformer form."""

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimgraph.models import BusBranchModel
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.transformer import (
    CoreAdmittance,
    MeshImpedance,
    TransformerForm,
    get_transformer_model,
    get_transformer_units,
)

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"
A, B, N, S1, S2 = (cim.SinglePhaseKind(token) for token in ("A", "B", "N", "s1", "s2"))
ABC = (A, B, cim.SinglePhaseKind.C)
CENTER_TAP_MESH = {(1, 2): (None, 2.04), (1, 3): (None, 2.04), (2, 3): (None, 1.36)}

# three windings of unequal rating: every percent on its own end, so ends 2 and 3 move to end 1's 10 MVA
THREE_WINDING = """Profile = cim18v17
Object PowerTransformer: mRID=xf_3w, name=3w
Table PowerTransformerEnd: mRID, node, phases, endNumber, connectionKind, ratedU (kV), ratedS (kVA), r (percent), PowerTransformer=xf_3w
    xf_3w_1, a, ABC, 1, D, 115,  10000, 0.4
    xf_3w_2, b, ABC, 2, Y, 13.8, 5000,  0.5
    xf_3w_3, c, ABC, 3, Y, 4.16, 5000,  0.5
Table TransformerMeshImpedance: mRID, FromTransformerEnd, ToTransformerEnd, x (percent)
    xf_3w_m12, xf_3w_1, xf_3w_2, 8
    xf_3w_m13, xf_3w_1, xf_3w_3, 10
    xf_3w_m23, xf_3w_2, xf_3w_3, 4
"""

# the same windings with a star x on every end (percent on its own end) and no mesh: on 10 MVA, x = 4, 4, 6
STAR_THREE_WINDING = """Profile = cim18v17
Object PowerTransformer: mRID=xf_3w, name=3w
Table PowerTransformerEnd: mRID, node, phases, endNumber, connectionKind, ratedU (kV), ratedS (kVA), r (percent), x (percent), PowerTransformer=xf_3w
    xf_3w_1, a, ABC, 1, D, 115,  10000, 0.4, 4
    xf_3w_2, b, ABC, 2, Y, 13.8, 5000,  0.5, 2
    xf_3w_3, c, ABC, 3, Y, 4.16, 5000,  0.5, 3
"""


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _get(network, cls, mrid):
    return next(obj for obj in network.graph[cls].values() if obj.mRID == mrid)


def _shape(name):
    return load_model(SHAPES / f"{name}.cimtbl")


def _model(network, mrid, cls=cim.PowerTransformer, **options):
    [unit] = get_transformer_units(_get(network, cls, mrid))
    return get_transformer_model(unit, voltage_unit="kV", power_unit="kVA", **options)


def _three_winding(tmp_path, extra=""):
    path = tmp_path / "atom.cimtbl"
    path.write_text(THREE_WINDING + extra)
    return load_model(path)


def _mesh(model):
    return {pair: (impedance.r, pytest.approx(impedance.x)) for pair, impedance in model.mesh.items()}


# the five forms ----------------------------------------------------------------------------------------------------


def test_by_ends():
    model = _model(_shape("transformer_by_ends"), "xf_sub")
    assert model.form is TransformerForm.BY_ENDS
    assert model.base_power == pytest.approx(5000)
    first, second = model.windings
    assert (first.end.mRID, first.phases, first.connection, first.grounded) == ("xf_sub_1", ABC, cim.WindingConnection.D,
                                                                               False)
    assert (second.phases, second.connection, second.rground, second.xground) == (ABC + (N,), cim.WindingConnection.Yn,
                                                                                 0.0, pytest.approx(0.4))
    assert [(w.rated_u, w.rated_s, w.base_u, w.base_s) for w in model.windings] == [
        (pytest.approx(115), pytest.approx(5000), None, None), (pytest.approx(4.16), pytest.approx(5000), None, None)]
    assert [w.r for w in model.windings] == pytest.approx([0.5, 0.5])
    assert _mesh(model) == {(1, 2): (None, 8.0)}
    assert model.core == CoreAdmittance(None, None)


def test_by_template_tank_ends():
    model = _model(_shape("transformer_by_template"), "xf_t1")
    assert model.form is TransformerForm.BY_TANK_ENDS
    assert model.base_power == pytest.approx(500)
    for winding in model.windings:
        # Yn on both the instance end and the template's tank end; rground/xground from the tank end only
        assert (winding.connection, winding.grounded, winding.rground, winding.xground) == (cim.WindingConnection.Yn,
                                                                                           True, 0.0, 0.0)
        assert winding.r is None
    assert [(w.rated_u, w.base_u, w.base_s) for w in model.windings] == [
        (pytest.approx(4.16), pytest.approx(2.4), pytest.approx(166.667)),
        (pytest.approx(0.48), pytest.approx(0.277), pytest.approx(166.667))]
    assert model.mesh == {(1, 2): MeshImpedance(pytest.approx(1.1), pytest.approx(2.0))}
    assert model.core == CoreAdmittance(0.0, 0.0)


@pytest.mark.parametrize(("shape", "mrid", "form", "connections"), [
    ("transformer_by_template", "xf_t2", TransformerForm.BY_LUGS,
     [cim.WindingConnection.Y, cim.WindingConnection.I, cim.WindingConnection.I]),
    ("transformer_by_phase_ends", "xf_t3", TransformerForm.BY_PHASE_ENDS, [None, None, None]),
])
def test_center_tap_by_lugs_and_by_phase_ends(shape, mrid, form, connections):
    model = _model(_shape(shape), mrid)
    assert model.form is form
    assert model.base_power == pytest.approx(5)
    assert [w.end.mRID for w in model.windings] == [f"{mrid}_1", f"{mrid}_2", f"{mrid}_2"]
    primary = (B, N) if form is TransformerForm.BY_LUGS else (A, B)
    assert [w.phases for w in model.windings] == [primary, (S1, N), (N, S2)]
    assert [w.connection for w in model.windings] == connections
    assert [w.rated_s for w in model.windings] == pytest.approx([5, 2.5, 2.5])
    assert [w.base_u for w in model.windings[1:]] == pytest.approx([0.12, 0.12])
    assert [w.r for w in model.windings] == pytest.approx([0.6, 1.2, 1.2])
    assert _mesh(model) == CENTER_TAP_MESH
    # 10 W of no-load loss on 5 kVA, and 0.5 % magnetizing current
    assert model.core == pytest.approx(CoreAdmittance(0.2, 0.5))


def test_auto_transformer():
    model = _model(_shape("voltage_regulator"), "xf_reg1", cim.VoltageRegulator)
    assert model.form is TransformerForm.AUTO
    assert [(w.phases, w.rated_u, w.base_u, w.rated_s, w.r, w.connection) for w in model.windings] == [
        ((A, N), None, pytest.approx(2.4), pytest.approx(1666), None, None)] * 2
    assert model.mesh == {(1, 2): MeshImpedance(pytest.approx(0.01), pytest.approx(0.01))}
    assert model.core == CoreAdmittance(None, None)


# an ideal VoltageRegulator (GLM's): two AutoTransformerEnds with no ratedS and no mesh
IDEAL_REGULATOR = """Profile = cim18v17
Object VoltageRegulator: mRID=xf_ideal, name=ideal
Table AutoTransformerEnd: mRID, node, phase, endNumber, grounded, baseU (V), AutoTransformer=xf_ideal
    xf_ideal_1, n0, AN, 1, true, 2401.78
    xf_ideal_2, n1, AN, 2, true, 2401.78
"""


def _ideal_regulator(tmp_path, extra=""):
    path = tmp_path / "ideal.cimtbl"
    path.write_text(IDEAL_REGULATOR + extra)
    return load_model(path)


def test_ideal_auto_transformer(tmp_path):
    model = _model(_ideal_regulator(tmp_path), "xf_ideal", cim.VoltageRegulator)
    assert model.form is TransformerForm.AUTO
    assert [(w.phases, w.base_u, w.rated_s, w.r) for w in model.windings] == [((A, N), pytest.approx(2.40178), None,
                                                                               None)] * 2
    assert (model.mesh, model.core, model.base_power) == ({}, CoreAdmittance(None, None), None)


def test_ideal_auto_transformer_on_a_declared_base(tmp_path):
    model = _model(_ideal_regulator(tmp_path), "xf_ideal", cim.VoltageRegulator, base_power=1000)
    assert model.base_power == pytest.approx(1000)


def test_unrated_auto_transformer_with_a_mesh_raises(tmp_path):
    # the binder takes a percent only on a rated From end, so the mesh runs from a rated end 2; end 1 is the base
    path = tmp_path / "unrated.cimtbl"
    path.write_text("""Profile = cim18v17
Object VoltageRegulator: mRID=xf_unrated, name=unrated
Table AutoTransformerEnd: mRID, node, phase, endNumber, baseU (V), ratedS (kVA), AutoTransformer=xf_unrated
    xf_unrated_1, n0, AN, 1, 2401.78,
    xf_unrated_2, n1, AN, 2, 2401.78, 500
Object TransformerMeshImpedance: mRID=xf_unrated_m, FromTransformerEnd=xf_unrated_2, ToTransformerEnd=xf_unrated_1, x (percent)=0.01
""")
    with pytest.raises(ValueError, match="AutoTransformerEnd 'xf_unrated_1': ratedS is unset"):
        _model(load_model(path), "xf_unrated", cim.VoltageRegulator)


def test_regulator_by_ends():
    model = _model(_shape("regulator"), "xf_reg1")
    assert [(w.phases, w.connection, w.r) for w in model.windings] == [((A,), cim.WindingConnection.Y,
                                                                         pytest.approx(0.005))] * 2
    assert _mesh(model) == {(1, 2): (None, 0.01)}


# a single-phase unit by PowerTransformerEnds alone: ratedU is the phase-to-phase nameplate on both ends
SINGLE_PHASE_BY_ENDS = """Profile = cim18v17
Object PowerTransformer: mRID=xf_1ph, name=1ph
Table PowerTransformerEnd: mRID, node, phases, endNumber, connectionKind, grounded, ratedU (kV), ratedS (kVA), PowerTransformer=xf_1ph
    xf_1ph_1, hv,  CN,   1, Y, true, 12.47, 15
    xf_1ph_2, lv,  s1s2, 2, Y, true, 0.24,  15
    xf_1ph_3, lv2, AB,   3, Y, true, 0.48,  15
Object TransformerMeshImpedance: mRID=xf_1ph_m12, FromTransformerEnd=xf_1ph_1, ToTransformerEnd=xf_1ph_2, x (percent)=2.3
"""


def test_single_phase_end_coil_voltage_comes_from_rated_u(tmp_path):
    """Phase to neutral is ratedU / sqrt(3); between two phases (s1s2, AB) it is ratedU."""
    path = tmp_path / "1ph.cimtbl"
    path.write_text(SINGLE_PHASE_BY_ENDS)
    model = _model(load_model(path), "xf_1ph")
    assert model.form is TransformerForm.BY_ENDS
    assert [w.rated_u for w in model.windings] == pytest.approx([12.47, 0.24, 0.48])
    assert [w.base_u for w in model.windings] == pytest.approx([12.47 / 3 ** 0.5, 0.24, 0.48])


# BY_TANK_IMPEDANCE: a GIS's nameplate kVA and %Z on two ends and one tank. The centre tap is the core shape's xf_t2
# (transformer_template_1ph): R = 1.2 %, X = 1.7 % on 5 kVA, so %Z = hypot(1.2, 1.7) and loadLoss = 60 W.
TANK_IMPEDANCE = f"""Profile = cim18v17
Table PowerTransformer: mRID, name
    xf_ct, ct
    xf_3p, 3p
Table PowerTransformerEnd: mRID, node, phases, endNumber, connectionKind, grounded, ratedU (kV), ratedS (kVA), PowerTransformer
    xf_ct_1, n1,    BN,    1, Y,  true, 4.16, 5,   xf_ct
    xf_ct_2, house, s1s2N, 2, I,  true, 0.24, 5,   xf_ct
    xf_3p_1, n2,    ABCN,  1, Y,  true, 12.47, 300, xf_3p
    xf_3p_2, lv,    ABCN,  2, Yn, true, 0.48,  300, xf_3p
Table TransformerTank: mRID, percentImpedance, loadLoss (W), noLoadLoss (W), percentMagnetizingCurrent, PowerTransformer
    xf_ct_tank, {math.hypot(1.2, 1.7)}, 60,   10, 0.5, xf_ct
    xf_3p_tank, 4.5,                    , , , xf_3p
"""


def _tank_impedance(tmp_path):
    path = tmp_path / "tank.cimtbl"
    path.write_text(TANK_IMPEDANCE)
    return load_model(path)


def test_tank_impedance_center_tap_is_the_template_s(tmp_path):
    model = _model(_tank_impedance(tmp_path), "xf_ct")
    template = _model(_shape("transformer_by_template"), "xf_t2")
    assert model.form is TransformerForm.BY_TANK_IMPEDANCE
    assert [w.phases for w in model.windings] == [(B, N), (S1, N), (N, S2)]
    assert [w.end.mRID for w in model.windings] == ["xf_ct_1", "xf_ct_2", "xf_ct_2"]
    for field in ("rated_u", "rated_s", "r"):
        assert [getattr(w, field) for w in model.windings] == pytest.approx([getattr(w, field) for w in
                                                                             template.windings]), field
    assert [w.base_u for w in model.windings] == pytest.approx([4.16 / 3 ** 0.5, 0.12, 0.12])
    assert [w.base_s for w in model.windings[1:]] == pytest.approx([5, 5])
    assert _mesh(model) == CENTER_TAP_MESH
    assert (model.core, model.base_power) == (pytest.approx(template.core), pytest.approx(5))


def test_tank_impedance_two_windings_without_load_loss_is_a_pure_reactance(tmp_path):
    model = _model(_tank_impedance(tmp_path), "xf_3p")
    assert [w.phases for w in model.windings] == [ABC + (N,), ABC + (N,)]
    assert [w.r for w in model.windings] == [0.0, 0.0]
    assert _mesh(model) == {(1, 2): (None, 4.5)}
    assert model.core == CoreAdmittance(None, None)


def test_tank_impedance_on_a_system_base(tmp_path):
    model = _model(_tank_impedance(tmp_path), "xf_ct", impedance_unit="pu", base_power=10)
    assert [w.r for w in model.windings] == pytest.approx([0.012, 0.024, 0.024])
    assert model.mesh[(1, 2)].x == pytest.approx(0.0408)


def test_tank_load_loss_above_its_impedance_raises(tmp_path):
    network = _tank_impedance(tmp_path)
    _get(network, cim.TransformerTank, "xf_ct_tank").loadLoss = cim.ActivePower(200, "W")
    with pytest.raises(ValueError, match=r"loadLoss 200 W is 4 % of 5 kVA, above its percentImpedance 2.08"):
        _model(network, "xf_ct")


@pytest.mark.parametrize("held", ["r", "mesh"])
def test_tank_impedance_beside_an_end_or_mesh_impedance_raises(held, tmp_path):
    network = _tank_impedance(tmp_path)
    first, second = (_get(network, cim.PowerTransformerEnd, mrid) for mrid in ("xf_3p_1", "xf_3p_2"))
    if held == "r":
        first.r = cim.PerCent(0.5)
    else:
        mesh = cim.TransformerMeshImpedance(mRID="m", FromTransformerEnd=first, ToTransformerEnd=[second],
                                            x=cim.PerCent(4.5))
        first.FromMeshImpedance.append(mesh)
    with pytest.raises(ValueError, match="beside TransformerTank 'xf_3p_tank''s percentImpedance"):
        _model(network, "xf_3p")


def test_single_can_base_s_must_be_its_end_s(tmp_path):
    network = _tank_impedance(tmp_path)
    _get(network, cim.TransformerTank, "xf_3p_tank").baseS = cim.ApparentPower(250, "kVA")
    with pytest.raises(ValueError, match="baseS 250 kVA is not PowerTransformerEnd 'xf_3p_1''s ratedS 300 kVA"):
        _model(network, "xf_3p")


# banks of BY_TANK_IMPEDANCE cans (GETTERS_PLAN bank rules): cans in tank order onto end 1's phases, each on its baseS
BANKS = """Profile = cim18v17
Table PowerTransformer: mRID, name
    xf_yy,   yy
    xf_yd,   yd
    xf_oyod, oyod
Table PowerTransformerEnd: mRID, node, phases, endNumber, connectionKind, grounded, ratedU (kV), ratedS (kVA), PowerTransformer
    xf_yy_1,   p1, ABCN, 1, Y,  true, 12.47, 75,  xf_yy
    xf_yy_2,   s1, ABCN, 2, Yn, true, 0.208, 75,  xf_yy
    xf_yd_1,   p2, ABCN, 1, Y,  true, 12.47, 100, xf_yd
    xf_yd_2,   s2, ABCN, 2, D,  true, 0.24,  100, xf_yd
    xf_oyod_1, p3, ABN,  1, Y,  true, 12.47, 100, xf_oyod
    xf_oyod_2, s3, ABCN, 2, D,  true, 0.24,  100, xf_oyod
Table TransformerTank: mRID, baseS (kVA), percentImpedance, loadLoss (W), PowerTransformer
    xf_yy_a,   25, 2.0, 200, xf_yy
    xf_yy_b,   25, 2.0, 200, xf_yy
    xf_yy_c,   25, 2.0, 200, xf_yy
    xf_yd_a,   50, 2.0, 540, xf_yd
    xf_yd_b,   25, 2.0, 200, xf_yd
    xf_yd_c,   25, 2.0, 200, xf_yd
    xf_oyod_l, 50, 2.0, 540, xf_oyod
    xf_oyod_t, 50, 2.0, 540, xf_oyod
"""
C = cim.SinglePhaseKind.C


def _banks(tmp_path):
    path = tmp_path / "banks.cimtbl"
    path.write_text(BANKS)
    return load_model(path)


def _can(network, mrid):
    return get_transformer_model(_get(network, cim.TransformerTank, mrid), voltage_unit="kV", power_unit="kVA")


@pytest.mark.parametrize(("mrid", "phases", "base_u", "base_s"), [
    ("xf_yy_b", [(B, N), (B, N)], [12.47 / 3 ** 0.5, 0.208 / 3 ** 0.5], [25, 25]),  # wye-wye: phase i to N
    ("xf_yd_a", [(A, N), (A, N), (N, B)], [12.47 / 3 ** 0.5, 0.12, 0.12], [50, 50, 50]),  # the lighting leg
    ("xf_yd_b", [(B, N), (B, C)], [12.47 / 3 ** 0.5, 0.24], [25, 25]),  # YNd1: B drives b-c
    ("xf_yd_c", [(C, N), (C, A)], [12.47 / 3 ** 0.5, 0.24], [25, 25]),
    ("xf_oyod_l", [(A, N), (A, N), (N, B)], [12.47 / 3 ** 0.5, 0.12, 0.12], [50, 50, 50]),  # L: a-N-b
    ("xf_oyod_t", [(B, N), (B, C)], [12.47 / 3 ** 0.5, 0.24], [50, 50]),  # T: b-c, the power leg
])
def test_bank_can_lands_in_tank_order(mrid, phases, base_u, base_s, tmp_path):
    model = _can(_banks(tmp_path), mrid)
    assert model.form is TransformerForm.BY_TANK_IMPEDANCE
    assert [w.phases for w in model.windings] == phases
    assert [w.base_u for w in model.windings] == pytest.approx(base_u)
    assert [w.base_s for w in model.windings] == pytest.approx(base_s)
    assert model.base_power == pytest.approx(base_s[0])


def test_bank_can_impedance_is_on_its_own_kva(tmp_path):
    """The 25 kVA can's 200 W is 0.8 %, not 0.8 % of the bank's 100 kVA."""
    model = _can(_banks(tmp_path), "xf_yd_b")
    assert [w.r for w in model.windings] == pytest.approx([0.4, 0.4])
    assert model.mesh[(1, 2)].x == pytest.approx((2.0 ** 2 - 0.8 ** 2) ** 0.5)


def test_bank_tank_without_base_s_raises(tmp_path):
    network = _banks(tmp_path)
    _get(network, cim.TransformerTank, "xf_yy_c").baseS = None
    with pytest.raises(ValueError, match="TransformerTank 'xf_yy_c': a tank in a bank needs its baseS"):
        _can(network, "xf_yy_a")


def test_bank_cans_must_add_up_to_the_ends(tmp_path):
    network = _banks(tmp_path)
    _get(network, cim.TransformerTank, "xf_yy_c").baseS = cim.ApparentPower(50, "kVA")
    with pytest.raises(ValueError, match="its tanks' baseS add up to 100 kVA, not PowerTransformerEnd 'xf_yy_1''s "
                                         "ratedS 75 kVA"):
        _can(network, "xf_yy_a")


def test_two_cans_on_a_closed_wye_secondary_raise(tmp_path):
    network = _banks(tmp_path)
    _get(network, cim.PowerTransformerEnd, "xf_oyod_2").connectionKind = cim.WindingConnection.Yn
    with pytest.raises(ValueError, match="a bank of 2 cans is read onto a wye end with a neutral and one phase"):
        _can(network, "xf_oyod_l")


def test_bank_mixing_forms_raises(tmp_path):
    network = _banks(tmp_path)
    _get(network, cim.TransformerTank, "xf_yy_c").percentImpedance = None
    with pytest.raises(ValueError, match="a bank mixes tanks by percentImpedance with TransformerTank 'xf_yy_c'"):
        _can(network, "xf_yy_a")

def test_units():
    template = _shape("transformer_by_template")
    assert [unit.mRID for unit in get_transformer_units(_get(template, cim.PowerTransformer, "xf_t1"))] == ["xf_t1_tank"]
    ends = _shape("transformer_by_ends")
    assert get_transformer_units(_get(ends, cim.PowerTransformer, "xf_sub")) == (_get(ends, cim.PowerTransformer,
                                                                                      "xf_sub"),)


# bases ---------------------------------------------------------------------------------------------------------------


def test_unequal_ratings_move_to_winding_1(tmp_path):
    model = _model(_three_winding(tmp_path), "xf_3w")
    assert model.base_power == pytest.approx(10000)
    # 0.5 % on 5 MVA is 1.0 % on 10 MVA; mesh 2-3 is on its From end 2
    assert [w.r for w in model.windings] == pytest.approx([0.4, 1.0, 1.0])
    assert _mesh(model) == {(1, 2): (None, 8.0), (1, 3): (None, 10.0), (2, 3): (None, 8.0)}


def test_system_base_in_pu(tmp_path):
    network = _three_winding(tmp_path)
    model = _model(network, "xf_3w", impedance_unit="pu", base_power=100_000)
    assert model.base_power == pytest.approx(100000)
    assert [w.r for w in model.windings] == pytest.approx([0.04, 0.1, 0.1])
    assert model.mesh[(2, 3)].x == pytest.approx(0.8)


def test_network_base_power():
    network = _shape("transformer_by_ends")
    model = _model(network, "xf_sub", base_power=network.base_power)
    assert model.mesh[(1, 2)].x == pytest.approx(160.0)


def test_unrated_ends_read_on_a_declared_base_power(tmp_path):
    # a RAW 3-winding unit's ends have no ratedS (E4-1): the ohms on each end's ratedU go straight onto 100 MVA, the
    # same numbers as test_system_base_in_pu
    network = _three_winding(tmp_path)
    for end in network.graph[cim.PowerTransformerEnd].values():
        end.ratedS = None
    model = _model(network, "xf_3w", impedance_unit="pu", base_power=100_000)
    assert [w.r for w in model.windings] == pytest.approx([0.04, 0.1, 0.1])
    assert [w.rated_s for w in model.windings] == [None, None, None]
    assert model.mesh[(2, 3)].x == pytest.approx(0.8)
    with pytest.raises(ValueError, match="PowerTransformerEnd 'xf_3w_1': ratedS is unset"):
        _model(network, "xf_3w")


def test_zero_end_holds_no_core(tmp_path):
    # RAW writes end 2's g, b as 0 (CIM: the secondary end is zero, E4-2); the core is end 1's
    network = _three_winding(tmp_path)
    end_1, end_2 = (_get(network, cim.PowerTransformerEnd, mrid) for mrid in ("xf_3w_1", "xf_3w_2"))
    end_1.g, end_1.b = cim.Conductance(1e-4, "S"), cim.Susceptance(-2e-4, "S")
    end_2.g, end_2.b = cim.Conductance(0.0, "S"), cim.Susceptance(0.0, "S")
    model = _model(network, "xf_3w", impedance_unit="pu", base_power=100_000)
    z_base = 115e3 ** 2 / 100e6
    assert model.core == pytest.approx(CoreAdmittance(1e-4 * z_base, -2e-4 * z_base))
    end_1.g, end_1.b = cim.Conductance(0.0, "S"), cim.Susceptance(0.0, "S")
    assert _model(network, "xf_3w").core == CoreAdmittance(0.0, 0.0)  # zeros on two ends: one zero core


def test_phase_shift_of_an_end(tmp_path):
    network = _three_winding(tmp_path)
    _get(network, cim.PowerTransformerEnd, "xf_3w_2").phaseShift = cim.AngleDegrees(-30.0)
    assert [w.phase_shift for w in _model(network, "xf_3w").windings] == [None, pytest.approx(-30.0), None]


def test_core_on_an_end_moves_by_its_rating(tmp_path):
    network = _three_winding(tmp_path)
    end = _get(network, cim.PowerTransformerEnd, "xf_3w_2")
    end.g, end.b = (cls(value, "S") for cls, value in ((cim.Conductance, 1e-3), (cim.Susceptance, 5e-3)))
    model = _model(network, "xf_3w")
    # y on end 2's 13.8 kV, 5 MVA base, then onto 10 MVA
    z_base = 13.8e3 ** 2 / 5e6
    assert model.core == pytest.approx(CoreAdmittance(1e-3 * z_base * 100 / 2, 5e-3 * z_base * 100 / 2))


# raises --------------------------------------------------------------------------------------------------------------


def test_ohm_is_not_a_result_unit():
    network = _shape("transformer_by_ends")
    with pytest.raises(ValueError, match="impedance_unit must be one of"):
        get_transformer_model(_get(network, cim.PowerTransformer, "xf_sub"), "ohm")


def test_transformer_with_tanks_raises():
    network = _shape("transformer_by_template")
    with pytest.raises(ValueError, match="PowerTransformer 'xf_t1': has tanks"):
        get_transformer_model(_get(network, cim.PowerTransformer, "xf_t1"))


def test_template_bank_by_tank_ends_raises():
    network = _shape("transformer_by_template")
    transformer = _get(network, cim.PowerTransformer, "xf_t1")
    transformer.TransformerTanks.append(cim.TransformerTank(mRID="xf_t1_tank_2", PowerTransformer=transformer))
    with pytest.raises(ValueError, match="a bank of template tanks says which phases each tank serves only by lugs; "
                                         "TransformerTank 'xf_t1_tank' has none"):
        get_transformer_model(transformer.TransformerTanks[0])


# templates by GLM's %Z (S3b-5): percentImpedance and loadLoss on the configuration, no winding r and no mesh. The
# shapes' xc_xfm1 is R 1.1 %, X 2 % on 500 kVA (loadLoss 5.5 kW) and xc_ct5 R 1.2 %, X 1.7 % on 5 kVA (60 W), so
# both read back as their mesh forms, the centre tap by its Hopkinson split.
def _by_nameplate(network, config_mrid, r, x, kva):
    config = _get(network, cim.TransformerTankConfiguration, config_mrid)
    for winding in config.TransformerWinding:
        winding.r = None
        winding.FromMeshImpedance.clear()
    config.percentImpedance = cim.PerCent(math.hypot(r, x))
    config.loadLoss = cim.ActivePower(r / 100 * kva, "kW")
    return network


@pytest.mark.parametrize(("mrid", "config", "r", "x", "kva", "resistances", "mesh"), [
    ("xf_t1", "xc_xfm1", 1.1, 2.0, 500, [0.55, 0.55], {(1, 2): (None, 2.0)}),
    ("xf_t2", "xc_ct5", 1.2, 1.7, 5, [0.6, 1.2, 1.2], CENTER_TAP_MESH),
])
def test_template_percent_impedance_is_split_as_a_tank_s(mrid, config, r, x, kva, resistances, mesh):
    model = _model(_by_nameplate(_shape("transformer_by_template"), config, r, x, kva), mrid)
    assert model.form in (TransformerForm.BY_TANK_ENDS, TransformerForm.BY_LUGS)
    assert [w.r for w in model.windings] == pytest.approx(resistances)
    assert _mesh(model) == mesh
    assert model.base_power == pytest.approx(kva)


def test_template_load_loss_above_its_percent_impedance_raises():
    network = _by_nameplate(_shape("transformer_by_template"), "xc_xfm1", 1.1, 2.0, 500)
    _get(network, cim.TransformerTankConfiguration, "xc_xfm1").loadLoss = cim.ActivePower(20, "kW")
    with pytest.raises(ValueError, match="TransformerTankConfiguration 'xc_xfm1': loadLoss 20000 W is 4 % of 500 kVA, "
                                         "above its percentImpedance"):
        _model(network, "xf_t1")


# a bank of lugged template cans (GLM's unequal WYE_WYE, S3b-9): each lug names the bank's phase end it lands on,
# end 1 A B N = 1-3, end 2 = 4-6; can A 50 kVA, can B 25 kVA, both 2 % with 1 % load loss
LUGGED_BANK = """Profile = cim18v17
Object PowerTransformer: mRID=xf_lb, name=lb
Table PowerTransformerEnd: mRID, node, phases, endNumber, connectionKind, grounded, PowerTransformer=xf_lb
    xf_lb_1, p, ABN, 1, Y,  true
    xf_lb_2, s, ABN, 2, Yn, true
Table TransformerPhaseEnd: mRID, endNumber, sequenceNumber, phase, Terminal
    xf_lb_1_A, 1, 1, A, xf_lb_T1
    xf_lb_1_B, 1, 2, B, xf_lb_T1
    xf_lb_1_N, 1, 3, N, xf_lb_T1
    xf_lb_2_A, 2, 4, A, xf_lb_T2
    xf_lb_2_B, 2, 5, B, xf_lb_T2
    xf_lb_2_N, 2, 6, N, xf_lb_T2
Table TransformerTankConfiguration: mRID, name, percentImpedance, loadLoss (W)
    xc_lb_A, lb_A, 2.0, 500
    xc_lb_B, lb_B, 2.0, 250
Table TransformerLug: mRID, designation, sequenceNumber, TankConfiguration
    xc_lb_A_h1, H1, 1, xc_lb_A
    xc_lb_A_h2, H2, 3, xc_lb_A
    xc_lb_A_x1, X1, 4, xc_lb_A
    xc_lb_A_x2, X2, 6, xc_lb_A
    xc_lb_B_h1, H1, 2, xc_lb_B
    xc_lb_B_h2, H2, 3, xc_lb_B
    xc_lb_B_x1, X1, 5, xc_lb_B
    xc_lb_B_x2, X2, 6, xc_lb_B
Table TransformerWinding: mRID, ratedU (V), baseU (V), ratedS (kVA), baseS (kVA), FromTransformerLug, ToTransformerLug, TankConfiguration
    xc_lb_A_wdg_1, 12470, 7199.558, 50, 50, xc_lb_A_h1, xc_lb_A_h2, xc_lb_A
    xc_lb_A_wdg_2, 208,   120.089,  50, 50, xc_lb_A_x1, xc_lb_A_x2, xc_lb_A
    xc_lb_B_wdg_1, 12470, 7199.558, 25, 25, xc_lb_B_h1, xc_lb_B_h2, xc_lb_B
    xc_lb_B_wdg_2, 208,   120.089,  25, 25, xc_lb_B_x1, xc_lb_B_x2, xc_lb_B
Table TransformerTank: mRID, PowerTransformer, TankConfiguration
    xf_lb_tank_A, xf_lb, xc_lb_A
    xf_lb_tank_B, xf_lb, xc_lb_B
"""


@pytest.mark.parametrize(("mrid", "phase", "kva"), [("xf_lb_tank_A", A, 50), ("xf_lb_tank_B", B, 25)])
def test_lugged_template_bank_can_serves_its_lugs_phase(mrid, phase, kva, tmp_path):
    path = tmp_path / "bank.cimtbl"
    path.write_text(LUGGED_BANK)
    model = _can(load_model(path), mrid)
    assert model.form is TransformerForm.BY_LUGS
    assert [w.phases for w in model.windings] == [(phase, N), (phase, N)]
    assert [w.end.mRID for w in model.windings] == ["xf_lb_1", "xf_lb_2"]
    assert [w.r for w in model.windings] == pytest.approx([0.5, 0.5])
    assert _mesh(model) == {(1, 2): (None, math.sqrt(3))}
    assert model.base_power == pytest.approx(kva)


# an open wye - open delta bank of lugged template cans by %Z (CIMTBL-Models open_wye_open_delta_example): end 1
# A B N = 1-3, end 2 a b c N = 4-7; the lighting can L is X1-X2-X3 = a-N-b, the power can T X1-X3 = b-c
OPEN_DELTA_BANK = """Profile = cim18v17
Object PowerTransformer: mRID=xf_od, name=od
Table PowerTransformerEnd: mRID, node, phases, endNumber, connectionKind, grounded, PowerTransformer=xf_od
    xf_od_1, p, ABN,  1, Y, true
    xf_od_2, s, ABCN, 2, D, true
Table TransformerPhaseEnd: mRID, endNumber, sequenceNumber, phase, Terminal
    xf_od_1_A, 1, 1, A, xf_od_T1
    xf_od_1_B, 1, 2, B, xf_od_T1
    xf_od_1_N, 1, 3, N, xf_od_T1
    xf_od_2_A, 2, 4, A, xf_od_T2
    xf_od_2_B, 2, 5, B, xf_od_T2
    xf_od_2_C, 2, 6, C, xf_od_T2
    xf_od_2_N, 2, 7, N, xf_od_T2
Table TransformerTankConfiguration: mRID, percentImpedance, loadLoss (W)
    xc_od_l, 2.0808652046684, 600
    xc_od_t, 2.0808652046684, 300
Table TransformerLug: mRID, designation, sequenceNumber, TankConfiguration
    xc_od_l_h1, H1, 1, xc_od_l
    xc_od_l_h2, H2, 3, xc_od_l
    xc_od_l_x1, X1, 4, xc_od_l
    xc_od_l_x2, X2, 7, xc_od_l
    xc_od_l_x3, X3, 5, xc_od_l
    xc_od_t_h1, H1, 2, xc_od_t
    xc_od_t_h2, H2, 3, xc_od_t
    xc_od_t_x1, X1, 5, xc_od_t
    xc_od_t_x3, X3, 6, xc_od_t
Table TransformerWinding: mRID, ratedU (V), baseU (V), ratedS (kVA), baseS (kVA), FromTransformerLug, ToTransformerLug, TankConfiguration
    xc_od_l_wdg_h1h2, 12470, 7199.558, 50, 50, xc_od_l_h1, xc_od_l_h2, xc_od_l
    xc_od_l_wdg_x1x2, 240,   120,      25, 50, xc_od_l_x1, xc_od_l_x2, xc_od_l
    xc_od_l_wdg_x2x3, 240,   120,      25, 50, xc_od_l_x2, xc_od_l_x3, xc_od_l
    xc_od_t_wdg_h1h2, 12470, 7199.558, 25, 25, xc_od_t_h1, xc_od_t_h2, xc_od_t
    xc_od_t_wdg_x1x3, 240,   240,      25, 25, xc_od_t_x1, xc_od_t_x3, xc_od_t
Table TransformerTank: mRID, PowerTransformer, TankConfiguration
    xf_od_tank_l, xf_od, xc_od_l
    xf_od_tank_t, xf_od, xc_od_t
"""


def test_a_lighting_can_by_percent_impedance_is_split_as_a_centre_tap(tmp_path):
    path = tmp_path / "bank.cimtbl"
    path.write_text(OPEN_DELTA_BANK)
    network = load_model(path)
    lighting, power = _can(network, "xf_od_tank_l"), _can(network, "xf_od_tank_t")
    assert [w.phases for w in lighting.windings] == [(A, N), (A, N), (N, B)]
    assert [w.r for w in lighting.windings] == pytest.approx([0.6, 1.2, 1.2])
    assert _mesh(lighting) == CENTER_TAP_MESH
    assert [w.phases for w in power.windings] == [(B, N), (B, cim.SinglePhaseKind.C)]
    assert [w.r for w in power.windings] == pytest.approx([0.6, 0.6])


def test_three_windings_that_are_no_centre_tap_raise(tmp_path):
    path = tmp_path / "bank.cimtbl"
    path.write_text(OPEN_DELTA_BANK.replace("xc_od_l_x2, X2, 7,", "xc_od_l_x2, X2, 6,"))
    with pytest.raises(ValueError, match="'xc_od_l': percentImpedance on 3 windings"):
        _can(load_model(path), "xf_od_tank_l")


def test_own_windings_and_a_configuration_raise():
    network = _shape("transformer_by_template")
    tank = _get(network, cim.TransformerTank, "xf_t1_tank")
    tank.TransformerWindings.append(cim.TransformerWinding(mRID="w"))
    with pytest.raises(ValueError, match="has its own TransformerWindings and a TankConfiguration"):
        get_transformer_model(tank)


def test_tank_and_configuration_both_holding_a_loss_raise():
    network = _shape("transformer_by_template")
    tank = _get(network, cim.TransformerTank, "xf_t1_tank")
    tank.noLoadLoss = cim.ActivePower(5, "W")
    with pytest.raises(ValueError, match="TransformerTank 'xf_t1_tank': both it and TransformerTankConfiguration "
                                         "'xc_xfm1' set noLoadLoss"):
        get_transformer_model(tank)


def test_instance_and_template_connection_disagree():
    network = _shape("transformer_by_template")
    _get(network, cim.PowerTransformerEnd, "xf_t1_1").connectionKind = cim.WindingConnection.D
    with pytest.raises(ValueError, match="PowerTransformerEnd 'xf_t1_1' and TransformerTankEnd 'xc_xfm1_end_1': "
                                         "connectionKind"):
        get_transformer_model(_get(network, cim.TransformerTank, "xf_t1_tank"))


def test_core_admittance_on_the_core_raises():
    network = _shape("transformer_by_template")
    _get(network, cim.TransformerCore, "xc_xfm1_core").g = cim.Conductance(1e-6)
    with pytest.raises(ValueError, match="TransformerCore 'xc_xfm1_core': its g/b are not read"):
        get_transformer_model(_get(network, cim.TransformerTank, "xf_t1_tank"))


def test_lug_naming_no_phase_end_raises():
    network = _shape("transformer_by_template")
    _get(network, cim.TransformerLug, "xc_ct5_lug_x1").sequenceNumber = 9
    with pytest.raises(ValueError, match=r"FromTransformerLug names no instance TransformerPhaseEnd \(sequenceNumber 9"):
        get_transformer_model(_get(network, cim.TransformerTank, "xf_t2_tank"))


def test_coil_across_two_ends_raises():
    network = _shape("transformer_by_phase_ends")
    _get(network, cim.TransformerWinding, "xf_t3_wdg_1").ToTransformerEnd = _get(network, cim.TransformerPhaseEnd,
                                                                                 "xf_t3_2_N")
    with pytest.raises(ValueError, match=r"TransformerWinding 'xf_t3_wdg_1': its phase ends are on different ends"):
        get_transformer_model(_get(network, cim.TransformerTank, "xf_t3_tank"))


def test_star_impedance_of_two_windings_on_end_1():
    # behind_transformer: r, x = 0.35, 42.3 ohm on end 1 (230 kV, 150 MVA, z base 352.67 ohm); end 2 has none
    network = load_model(SHAPES / "behind_transformer.cimtbl", model_cls=BusBranchModel)
    model = get_transformer_model(_get(network, cim.PowerTransformer, "gen_g1_xf"), "pu")
    assert [w.r for w in model.windings] == [pytest.approx(0.35 * 150 / 230**2), None]
    assert _mesh(model) == {(1, 2): (None, pytest.approx(42.3 * 150 / 230**2))}
    on_system = get_transformer_model(_get(network, cim.PowerTransformer, "gen_g1_xf"), "pu",
                                      base_power=network.base_power)
    assert on_system.mesh[(1, 2)].x == pytest.approx(42.3 * 100 / 230**2)


def test_star_impedance_of_three_windings_adds_by_pair(tmp_path):
    path = tmp_path / "star.cimtbl"
    path.write_text(STAR_THREE_WINDING)
    model = _model(load_model(path), "xf_3w")
    assert _mesh(model) == {(1, 2): (None, 8.0), (1, 3): (None, 10.0), (2, 3): (None, 10.0)}


def test_three_windings_with_an_unset_star_x_raise(tmp_path):
    """Only two windings may hold the whole x on one end; a third winding's unset x is not a zero."""
    path = tmp_path / "star.cimtbl"
    path.write_text(STAR_THREE_WINDING.replace("0.5, 3\n", "0.5,\n"))
    with pytest.raises(ValueError, match=r"the star x of winding\(s\) \[3\] is unset; with 3 windings"):
        _model(load_model(path), "xf_3w")


def test_star_and_mesh_impedance_raise():
    network = _shape("transformer_by_ends")
    _get(network, cim.PowerTransformerEnd, "xf_sub_1").x = cim.Reactance(1.0)
    with pytest.raises(ValueError, match="both a star impedance .PowerTransformerEnd.x. and a mesh impedance"):
        get_transformer_model(_get(network, cim.PowerTransformer, "xf_sub"))


def test_unset_mesh_reactance_raises():
    network = _shape("transformer_by_ends")
    _get(network, cim.TransformerMeshImpedance, "xf_sub_mesh_12").x = None
    with pytest.raises(ValueError, match="TransformerMeshImpedance 'xf_sub_mesh_12': x is unset"):
        get_transformer_model(_get(network, cim.PowerTransformer, "xf_sub"))


def test_unrated_winding_1_raises():
    network = _shape("transformer_by_ends")
    _get(network, cim.PowerTransformerEnd, "xf_sub_1").ratedS = None
    with pytest.raises(ValueError, match="PowerTransformerEnd 'xf_sub_1': ratedS is unset"):
        get_transformer_model(_get(network, cim.PowerTransformer, "xf_sub"))


# S6c: a template's kind without grounding (T2), and a 1-phase TankEnd coil's direction (T3) -----------------------

# 1-phase delta-delta TankEnd template; the instance's end 2 runs C -> A (DSS tert.3.1), told by its phase ends
COIL_TEMPLATE = """Profile = cim18v17
Object TransformerTankConfiguration: mRID=xc_d, name=d
Table TransformerTankEnd: mRID, endNumber, connectionKind, TankConfiguration=xc_d
    xc_d_end_1, 1, Y
    xc_d_end_2, 2, D
Table TransformerWinding: mRID, ratedU (kV), baseU (kV), ratedS (kVA), baseS (kVA), FromTransformerEnd, TankConfiguration=xc_d
    xc_d_wdg_1, 12.47, 7.2, 333, 333, xc_d_end_1
    xc_d_wdg_2, 2.4,   2.4, 333, 333, xc_d_end_2
Object TransformerMeshImpedance: mRID=xc_d_mesh_12, FromWinding=xc_d_wdg_1, ToWinding=xc_d_wdg_2, x (percent)=3
Object PowerTransformer: mRID=xf_c, name=c
Object TransformerTank: mRID=xf_c_tank, PowerTransformer=xf_c, TankConfiguration=xc_d
Table PowerTransformerEnd: mRID, node, phases, endNumber, connectionKind, grounded, PowerTransformer=xf_c
    xf_c_1, hv,   CN, 1, Yn, true
    xf_c_2, tert, AC, 2, D,  false
Table TransformerPhaseEnd: mRID, endNumber, sequenceNumber, phase, Terminal
    xf_c_1_C, 1, 1, C, xf_c_T1
    xf_c_1_N, 1, 2, N, xf_c_T1
    xf_c_2_C, 2, 3, C, xf_c_T2
    xf_c_2_A, 2, 4, A, xf_c_T2
"""


def _coil_template(tmp_path):
    path = tmp_path / "coil.cimtbl"
    path.write_text(COIL_TEMPLATE)
    return load_model(path)


def test_template_wye_agrees_with_a_grounded_instance(tmp_path):
    model = _model(_coil_template(tmp_path), "xf_c")
    assert [winding.connection for winding in model.windings] == [cim.WindingConnection.Yn, cim.WindingConnection.D]


def test_tank_end_coil_runs_in_its_phase_end_order(tmp_path):
    model = _model(_coil_template(tmp_path), "xf_c")
    assert [winding.phases for winding in model.windings] == [(cim.SinglePhaseKind.C, N), (cim.SinglePhaseKind.C, A)]


def test_tank_end_phase_ends_other_than_the_terminal_raise(tmp_path):
    network = _coil_template(tmp_path)
    _get(network, cim.TransformerPhaseEnd, "xf_c_2_A").phase = B
    with pytest.raises(ValueError, match=r"its TransformerPhaseEnds \['C', 'B'\] are not its terminal's phases"):
        _model(network, "xf_c")


def test_dc_resistance_is_a_windings_and_an_end_has_none():
    """``r_dc`` is a TransformerWinding's rDC in ohm (a template's here), and None on a PowerTransformerEnd."""
    network = _shape("transformer_by_template")
    template = _get(network, cim.TransformerTankConfiguration, _get(network, cim.TransformerTank, "xf_t1_tank")
                    .TankConfiguration.mRID)
    for number, winding in enumerate(sorted(template.TransformerWinding, key=lambda w: w.mRID), start=1):
        winding.rDC = cim.Resistance(0.5 * number, "ohm")
    assert [w.r_dc for w in _model(network, "xf_t1").windings] == pytest.approx([0.5, 1.0])
    assert {w.r_dc for w in _model(_shape("transformer_by_ends"), "xf_sub").windings} == {None}

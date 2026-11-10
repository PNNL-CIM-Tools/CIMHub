"""cimhub_core.getters.transformer: one model of windings, mesh and core from each CIM transformer form."""

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


def test_regulator_by_ends():
    model = _model(_shape("regulator"), "xf_reg1")
    assert [(w.phases, w.connection, w.r) for w in model.windings] == [((A,), cim.WindingConnection.Y,
                                                                         pytest.approx(0.005))] * 2
    assert _mesh(model) == {(1, 2): (None, 0.01)}


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
    model = _model(network, "xf_3w", impedance_unit="pu", base_power=cim.ApparentPower(100, "MVA"))
    assert model.base_power == pytest.approx(100000)
    assert [w.r for w in model.windings] == pytest.approx([0.04, 0.1, 0.1])
    assert model.mesh[(2, 3)].x == pytest.approx(0.8)


def test_network_base_power():
    network = _shape("transformer_by_ends")
    model = _model(network, "xf_sub", base_power=network.base_power)
    assert model.mesh[(1, 2)].x == pytest.approx(160.0)


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


def test_template_bank_raises():
    network = _shape("transformer_by_template")
    transformer = _get(network, cim.PowerTransformer, "xf_t1")
    transformer.TransformerTanks.append(cim.TransformerTank(mRID="xf_t1_tank_2", PowerTransformer=transformer))
    with pytest.raises(ValueError, match="a bank of template tanks"):
        get_transformer_model(transformer.TransformerTanks[0])


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

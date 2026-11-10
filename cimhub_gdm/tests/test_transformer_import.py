"""DistributionTransformer → PowerTransformer on a TransformerTankConfiguration (tests/atoms/transformer)."""

import gdm_atoms
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import transformer
from gdm.distribution.components import DistributionTransformer
from gdm.distribution.enums import ConnectionType, Phase
from gdm.distribution.equipment import (
    DistributionTransformerEquipment,
    PowerTransformerEquipment,
    WindingEquipment,
)

from cimhub_gdm import gdm_to_cim

ABC, LL, LG = gdm_atoms.ABC, gdm_atoms.LL, gdm_atoms.LG
STAR, DELTA = ConnectionType.STAR, ConnectionType.DELTA


def test_transformers_match_golden():
    system = gdm_atoms.shell_system()
    gdm_atoms.add_transformers(system)
    gdm_atoms.assert_import_matches(system, gdm_atoms.ATOMS / "transformer" / "transformers.cimtbl")


@pytest.mark.parametrize("fields, cls", [
    (transformer.FIELDS_DistributionTransformer, DistributionTransformer),
    (transformer.FIELDS_DistributionTransformerEquipment, DistributionTransformerEquipment),
    (transformer.FIELDS_PowerTransformerEquipment, PowerTransformerEquipment),
    (transformer.FIELDS_WindingEquipment, WindingEquipment),
])
def test_fields_are_classified(fields, cls):
    check_fields(fields, cls)


def _catalog(*connections, pairs=((0, 1),), **extra):
    windings = [gdm_atoms.winding(4.16, LL, 100, 0.5, connection) for connection in connections]
    return gdm_atoms.transformer_catalog("x", windings, pairs, [5.0] * len(pairs), **extra)


@pytest.mark.parametrize("pairs, expected", [
    (((0, 1),), [(0, 1)]),
    (((1, 2),), [(0, 1)]),
    (((0, 1), (0, 2), (1, 2)), [(0, 1), (0, 2), (1, 2)]),
])
def test_coupling_pairs(pairs, expected):
    equipment = _catalog(*[STAR] * (1 + max(max(p) for p in pairs) - min(min(p) for p in pairs)), pairs=pairs)
    assert transformer.coupling_pairs(equipment) == expected


def test_out_of_range_coupling_pairs_raise():
    equipment = _catalog(STAR, STAR, pairs=((2, 3),))
    with pytest.raises(ValueError, match="out of range for 2 windings"):
        transformer.coupling_pairs(equipment)


@pytest.mark.parametrize("connections, expected", [
    ((DELTA, STAR), "Dy1"),
    ((STAR, STAR), "Yy0"),
    ((STAR, DELTA), "Yd1"),
    ((DELTA, DELTA), "Dd0"),
    ((STAR, STAR, DELTA), "Yy0d1"),
])
def test_vector_group(connections, expected):
    pairs = ((0, 1),) if len(connections) == 2 else ((0, 1), (0, 2), (1, 2))
    assert transformer.vector_group(_catalog(*connections, pairs=pairs)) == expected


def test_vector_group_mismatch_raises():
    system = gdm_atoms.shell_system()
    system.add_component(_catalog(DELTA, STAR, cls=PowerTransformerEquipment, vector_group="Dyn11"))
    with pytest.raises(ValueError, match="vector_group 'Dyn11', but the windings make 'Dy1'"):
        gdm_to_cim(system)


@pytest.mark.parametrize("tap, expected", [(1.0, (16, -16, 0)), (1.0375, (16, -16, 6)), (0.95, (16, -16, -8))])
def test_tap_step(tap, expected):
    high, low, increment, step = transformer.tap_step(tap, 32, 0.9, 1.1, "x")
    assert (high, low, step) == expected
    assert increment == pytest.approx(0.625)


@pytest.mark.parametrize("tap, total, low, high, match", [
    (1.003, 32, 0.9, 1.1, "not a whole step"),
    (1.0, 32, 0.9, 1.05, "not symmetric"),
    (1.0, 33, 0.9, 1.1, "not symmetric"),
])
def test_tap_step_raises(tap, total, low, high, match):
    with pytest.raises(ValueError, match=match):
        transformer.tap_step(tap, total, low, high, "x")


def test_loss_is_active_power_in_the_rating_prefix():
    assert transformer.loss(1.74408, gdm_atoms.ApparentPower(75, "kilova"), "x") == transformer.Qty(1.30806, "kW")


def _system_with(build):
    system = gdm_atoms.shell_system()
    gdm_atoms.add_transformers(system)
    build(system)
    return system


def test_instance_and_catalog_taps_that_differ_raise():
    def build(system):
        t3w = system.get_component(DistributionTransformer, "t3w")
        t3w.tap_positions = [[1.0] * 3, [1.025] * 3 + [1.0], [1.0] * 3]

    with pytest.raises(ValueError, match="instance taps .* and catalog taps .* differ"):
        gdm_to_cim(_system_with(build))


def test_taps_that_differ_by_phase_raise():
    def build(system):
        system.get_component(DistributionTransformer, "t_dy").tap_positions = [[1.0] * 3, [1.0, 1.025, 1.0, 1.0]]

    with pytest.raises(ValueError, match="taps differ by phase"):
        gdm_to_cim(_system_with(build))


def test_unequal_coupled_winding_ratings_raise():
    def build(system):
        catalog = system.get_component(DistributionTransformerEquipment, "yyd")
        catalog.windings[1].rated_power = gdm_atoms.ApparentPower(500, "kilova")

    with pytest.raises(ValueError, match="winding 2 is rated 500 kilova, not winding 1's"):
        gdm_to_cim(_system_with(build))


def test_open_delta_winding_raises():
    system = gdm_atoms.shell_system()
    system.add_component(_catalog(ConnectionType.OPEN_DELTA, STAR))
    with pytest.raises(ValueError, match="OPEN_DELTA"):
        gdm_to_cim(system)


def test_center_tap_half_off_nominal_raises():
    def build(system):
        system.get_component(DistributionTransformer, "t_ct").tap_positions = [[1.0], [1.025, 1.0], [1.0, 1.0]]

    with pytest.raises(ValueError, match="a center tap half is off nominal"):
        gdm_to_cim(_system_with(build))


def test_center_tap_with_three_phase_winding_raises():
    equipment = gdm_atoms.transformer_catalog(
        "bad", [gdm_atoms.winding(2.4018, LG, 25, 0.6), gdm_atoms.winding(0.12, LG, 25, 1.2, phases=1),
                gdm_atoms.winding(0.12, LG, 25, 1.2, phases=1)],
        [(0, 1), (0, 2), (1, 2)], [2.0, 2.0, 1.3], center_tap=True)
    with pytest.raises(ValueError, match="three single-phase wye windings"):
        transformer.check_center_tap(equipment, "x")


@pytest.mark.parametrize("connection, grounded, phases, expected", [
    (STAR, True, [Phase.A, Phase.B, Phase.C, Phase.N], ("Yn", True)),
    (STAR, False, [Phase.A, Phase.B, Phase.C, Phase.N], ("Yn", False)),
    (STAR, True, ["A", "B", "C"], ("Y", True)),
    (STAR, False, ["A", "B", "C"], ("Y", False)),
    (DELTA, False, ["A", "B", "C"], ("D", False)),
])
def test_end_connection_follows_gdm(connection, grounded, phases, expected):
    winding = gdm_atoms.winding(4.16, LL, 100, 0.5, connection, grounded=grounded)
    assert transformer.end_connection(winding, phases, "x") == expected


def test_grounded_delta_raises():
    winding = gdm_atoms.winding(4.16, LL, 100, 0.5, DELTA, grounded=True)
    with pytest.raises(ValueError, match="grounded delta"):
        transformer.end_connection(winding, ["A", "B", "C"], "x")


def test_center_tap_halves_grounded_differently_raise():
    def build(system):
        system.get_component(DistributionTransformerEquipment, "ct25").windings[2].is_grounded = False

    with pytest.raises(ValueError, match="one center tap half is grounded"):
        gdm_to_cim(_system_with(build))


def test_the_neutral_has_no_tap():
    def build(system):
        system.get_component(DistributionTransformer, "t_dy").tap_positions = [[1.0] * 3, [1.025] * 3 + [1.0]]

    model = gdm_to_cim(_system_with(build))
    assert model.find_by_mRID("xf_t_dy_2_tap").step == 4

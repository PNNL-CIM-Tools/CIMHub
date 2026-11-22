"""S2: the conductor, spacing and line configuration catalogs: classification, the atom, fail fast; the decks run in
test_cimtbl_sweep.py."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_core.getters.spacing import get_spacing_distances, get_spacing_xy
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.cimtbl import conductor, configuration, spacing
from cimhub_gridlabd.importer.cimtbl.configuration import triplex_spacing
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

ATOM = Path(__file__).parent / "atoms" / "catalog"
PARTS = ("overhead_line_conductor", "underground_line_conductor", "triplex_line_conductor", "line_spacing",
         "line_configuration", "triplex_line_configuration")
FIELDS = {**conductor.FIELDS, schema.LineSpacing: spacing.FIELDS, **configuration.FIELDS}


def read(path: Path, **kwargs):
    return GlmReader(path, **kwargs).read_all()


def parts(model, name: str) -> dict:
    return {part.name: part for part in GlmImporter(name).to_cimtbl(model).parts}


@pytest.mark.parametrize("native_cls", FIELDS, ids=lambda cls: cls.__name__)
def test_every_slot_is_classified(native_cls):
    check_fields(FIELDS[native_cls], native_cls)


def test_triplex_spacing():
    # triplex_line.cpp: D12 = (d + 2t) / 12 ft, D13 = (d + t) / 12 ft; here in the inputs' unit
    assert triplex_spacing(0.522, 0.08) == pytest.approx((0.682, 0.602))
    d12, d1n = triplex_spacing(0.522, 0.08)
    assert (d12 - d1n, 2 * d1n - d12) == pytest.approx((0.08, 0.522))  # the exporter's inverse


# -- tier 1 / 1b: the atom ----------------------------------------------------------------------------------------

def test_atom_goldens():
    documents = parts(read(ATOM / "catalog.glm"), "catalog")
    for name in PARTS:
        assert_matches_golden(documents[name], ATOM / f"catalog.{name}.cimtbl")


def test_atom_binds(scope):
    network = glm_to_cim(read(ATOM / "catalog.glm"), name="catalog")
    infos = {str(info.mRID): type(info).__name__ for cls in (cim.OverheadWireInfo, cim.ConcentricNeutralCableInfo,
                                                             cim.TapeShieldCableInfo)
             for info in network.list_by_class(cls)}
    assert infos == {"ohc_wire_acsr_556_5": "OverheadWireInfo", "ohc_overhead_line_conductor:3": "OverheadWireInfo",
                     "ugc_cncab_cn_250": "ConcentricNeutralCableInfo", "ugc_tscab_ts_1/0": "TapeShieldCableInfo",
                     "ugc_ugwire_cu_1/0": "OverheadWireInfo", "tpc_triplex_4/0 AA": "OverheadWireInfo"}
    [wire] = [w for w in network.list_by_class(cim.OverheadWireInfo) if str(w.mRID) == "ohc_wire_acsr_556_5"]
    assert float(wire.radius.to("in")) == pytest.approx(0.4635)
    assert float(wire.rAC50.to("ohm/mile")) == pytest.approx(0.18972)
    assert sorted(float(limit.normalValue.to("A")) for limit in wire.OperationalLimitSet.OperationalLimitValue) \
        == [730.0, 730.0]

    spacings = {str(s.mRID): s for s in network.list_by_class(cim.ConductorDistanceSpacing)}
    # the core getters read the spacing as written: distances, and positions from the heights
    distances = get_spacing_distances(spacings["spc_spc_601_ABCN"], "ft")
    assert distances[(1, 2)] == pytest.approx(2.5) and distances[(3, 4)] == pytest.approx(5.0)
    heights = [position.y for position in get_spacing_xy(spacings["spc_spc_601_ABCN"], "ft")]
    assert heights == pytest.approx([28.0, 28.0, 28.0, 24.0])
    triplex = {(row.sequenceNumber1, row.sequenceNumber2): float(row.distance.to("in"))
               for row in spacings["wc_triplex_line_configuration:1_spc"].ConductorDistance}
    assert triplex == pytest.approx({(1, 2): 0.682, (1, 3): 0.602, (2, 3): 0.602})
    phases = {str(row.mRID): (row.fromPhase.value, row.toPhase.value if row.toPhase else None)
              for row in spacings["spc_spc_601_ABCN"].ConductorDistance}
    assert phases["spc_spc_601_ABCN_CN"] == ("C", "N") and phases["spc_spc_601_ABCN_NE"] == ("N", None)

    [code] = network.list_by_class(cim.PerLengthPhaseImpedance)
    assert code.conductorCount == 2
    data = {(d.row, d.column): d for d in code.PhaseImpedanceData}
    assert float(data[(2, 1)].x.to("ohm/mile")) == pytest.approx(0.4591)
    assert float(data[(1, 1)].b.to("nS/mile")) == pytest.approx(2 * 3.141592653589793 * 60 * 4.7101)


# -- fail fast -------------------------------------------------------------------------------------------------------

NETWORK = """
object substation { name src; bustype SWING; phases ABCN; nominal_voltage 7200; }
object overhead_line_conductor { name w; geometric_mean_radius 0.03; resistance 0.2; %s }
object line_spacing { name s; distance_AN 5.0; }
"""


def raises(tmp_path, text: str, match: str):
    path = tmp_path / "model.glm"
    path.write_text(text)
    with pytest.raises(ValueError, match=match):
        GlmImporter("m").to_cimtbl(read(path))


def test_both_forms_raise(tmp_path):
    raises(tmp_path, NETWORK % "" + "object line_configuration { name c; spacing s; conductor_A w; conductor_N w; "
                                    "z11 0.3+1.0j; }\n", "line_configuration c: sets both a matrix")


def test_neither_form_raises(tmp_path):
    raises(tmp_path, NETWORK % "" + "object line_configuration { name c; }\n", "sets neither a matrix")


def test_conductors_without_spacing_raise(tmp_path):
    raises(tmp_path, NETWORK % "" + "object line_configuration { name c; conductor_A w; }\n",
           "geometry needs both spacing and conductors")


def test_conductor_of_the_wrong_class_raises(tmp_path):
    raises(tmp_path, NETWORK % "" + "object line_configuration { name c; spacing s; conductor_A w; conductor_N s; }\n",
           "conductor_N 's' is a line_spacing, not a overhead_line_conductor, underground_line_conductor")


def test_phases_other_than_the_spacing_raise(tmp_path):
    raises(tmp_path, NETWORK % "" + "object line_configuration { name c; spacing s; conductor_B w; conductor_N w; }\n",
           r"its conductors BN are not the phases AN its spacing s names \(S2-3\)")


def test_winter_rating_that_differs_raises(tmp_path):
    raises(tmp_path, NETWORK % "rating.summer.continuous 400; rating.winter.continuous 450;",
           r"rating.winter.continuous=450.0 differs from rating.summer.continuous=400.0")


def test_conductor_without_gmr_raises(tmp_path):
    raises(tmp_path, NETWORK % "" + "object overhead_line_conductor { name w2; resistance 0.2; }\n",
           "overhead_line_conductor w2: geometric_mean_radius unset")


def test_cable_with_strands_and_a_shield_raises(tmp_path):
    raises(tmp_path, NETWORK % "" + "object underground_line_conductor { name u; conductor_gmr 0.01; "
                                    "conductor_resistance 0.4; neutral_strands 13; shield_thickness 0.005; }\n",
           "sets both neutral_strands and shield_thickness")


def test_asymmetric_matrix_raises(tmp_path):
    raises(tmp_path, NETWORK % "" + "object line_configuration { name c; z11 0.3+1.0j; z22 0.3+1.0j; "
                                    "z12 0.1+0.4j; z21 0.1+0.5j; }\n", "z21=.* but z12=.*only a symmetric matrix")


def test_off_diagonal_without_its_diagonals_raises(tmp_path):
    raises(tmp_path, NETWORK % "" + "object line_configuration { name c; z11 0.3+1.0j; z12 0.1+0.4j; }\n",
           "z12 is set without z11 and z22")


def test_triplex_without_diameter_raises(tmp_path):
    raises(tmp_path, NETWORK % "" + """
object triplex_line_conductor { name t; resistance 0.48; geometric_mean_radius 0.0158; }
object triplex_line_configuration { name tc; conductor_1 t; conductor_2 t; conductor_N t; insulation_thickness 0.08; }
""", r"triplex_line_configuration tc: diameter unset \(triplex_line.cpp throws\)")


# -- the deck sweep's check (test_cimtbl_sweep.py) -----------------------------------------------------------------

def assert_catalogs(model, network) -> None:
    """Every conductor, spacing and line configuration is written once (S2)."""
    def count(*classes):
        return sum(len(network.list_by_class(cls)) for cls in classes)

    conductors = sum(model.count(cls) for cls, _, _ in conductor.CATALOGS)
    configurations = model.count(schema.LineConfiguration)
    triplex = model.count(schema.TriplexLineConfiguration)
    assert count(cim.OverheadWireInfo, cim.ConcentricNeutralCableInfo, cim.TapeShieldCableInfo) == conductors
    assert count(cim.ConductorDistanceSpacing) == model.count(schema.LineSpacing) + triplex
    assert count(cim.WireConfiguration) == configurations + triplex  # a matrix's holds its template

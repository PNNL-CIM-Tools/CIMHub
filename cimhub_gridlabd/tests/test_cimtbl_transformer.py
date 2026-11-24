"""S3b: transformers: classification, the atom, GridLAB-D's own ohms, fail fast; the decks run in
test_cimtbl_sweep.py."""
from __future__ import annotations

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.cimtbl import transformer, transformer_configuration
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

ATOM = Path(__file__).parent / "atoms" / "transformer"
PARTS = ("transformer_configuration", "transformer")
MODEL = "xfmr"  # not a part's name


def read(path: Path, **kwargs):
    return GlmReader(path, **kwargs).read_all()


def parts(model, name: str) -> dict:
    return {part.name: part for part in GlmImporter(name).to_cimtbl(model).parts}


@pytest.mark.parametrize("module", (transformer_configuration, transformer), ids=lambda module: module.__name__)
def test_every_slot_is_classified(module):
    check_fields(module.FIELDS, module.NATIVE_CLASS)


# -- GridLAB-D's ohms (GLM-16): from the configuration by the C++ formulas, against the bound tank fields ----------

def _glm_complex(config, slot: str) -> complex | None:
    value = getattr(config, slot)
    if value is not None:
        return complex(float(value.real or 0), float(value.imag or 0))
    real, imaginary = getattr(config, slot.replace("impedance", "resistance")), \
        getattr(config, slot.replace("impedance", "reactance"))
    return None if real is None and imaginary is None else complex(float(real or 0), float(imaginary or 0))


def _glm_kva(config) -> float:
    return float(config.power_rating) if config.power_rating else sum(
        float(getattr(config, f"power{p}_rating") or 0) for p in "ABC")


def _tank_impedance(tank_config) -> tuple[complex, float, float, float]:
    """``(R + jX per unit on the tank, g pu, b pu, S_tank VA)`` from the four nameplate fields."""
    s_tank = max(float(w.ratedS.to("VA")) for w in tank_config.TransformerWinding)
    r = float(tank_config.loadLoss.to("W")) / s_tank
    x = math.sqrt((float(tank_config.percentImpedance) / 100) ** 2 - r ** 2)
    g = 0.0 if tank_config.noLoadLoss is None else float(tank_config.noLoadLoss.to("W")) / s_tank
    b = 0.0 if tank_config.percentMagnetizingCurrent is None else float(tank_config.percentMagnetizingCurrent) / 100
    return complex(r, x), g, b, s_tank


def _winding(tank_config, end: int):
    for winding in tank_config.TransformerWinding:
        if winding.FromTransformerEnd is not None and winding.FromTransformerEnd.endNumber == end:
            return winding
        if winding.FromTransformerLug is not None and winding.FromTransformerLug.designation == ("H1", "X1")[end - 1]:
            return winding
    raise AssertionError(f"{tank_config.mRID}: no winding on end {end}")


def assert_gridlabd_ohms(model, network) -> None:
    """Every tank's %Z fields, turned back into ohms and siemens on its coils, equal GridLAB-D's ``zt`` and ``zc``
    (``transformer.cpp:266``) or its center-tap star ``z0``, ``z1`` and ``zc`` (``:784``)."""
    tanks = {str(t.mRID): t for t in network.list_by_class(cim.TransformerTank)}
    for xf in model.list_by_class(schema.Transformer):
        config = model.by_name(xf.configuration)
        mine = [t for name, t in tanks.items() if name.startswith(f"xf_{xf.name}_tank")]
        assert mine, xf.name
        shunt = _glm_complex(config, "shunt_impedance")
        if str(config.connect_type) == transformer_configuration.CENTER_TAP:
            [tank] = mine
            z, g, b, s = _tank_impedance(tank.TankConfiguration)
            v1, v2 = float(config.primary_voltage), float(config.secondary_voltage)
            given, half = _glm_complex(config, "impedance"), _glm_complex(config, "impedance1")
            z0 = given if half is not None else complex(0.5 * given.real, 0.8 * given.imag)
            z1 = half if half is not None else complex(given.real, 0.4 * given.imag)
            base1 = float(_winding(tank.TankConfiguration, 1).baseU.to("V")) ** 2 / s
            base2 = float(_winding(tank.TankConfiguration, 2).baseU.to("V")) ** 2 / s
            assert complex(0.5 * z.real, 0.8 * z.imag) * base1 == pytest.approx(z0 * v1 ** 2 / s, rel=1e-9), xf.name
            assert complex(z.real, 0.4 * z.imag) * base2 == pytest.approx(z1 * v2 ** 2 / s, rel=1e-9), xf.name
            if shunt is not None:
                assert g / base1 == pytest.approx(1 / (shunt.real * base1), rel=1e-9), xf.name
                assert b / base1 == pytest.approx(1 / (shunt.imag * base1), rel=1e-9), xf.name
            continue
        zt_base = float(config.secondary_voltage) ** 2 / (_glm_kva(config) * 1000)  # V_sec² / kVA_rating (:266)
        zt = _glm_complex(config, "impedance") * zt_base
        assert sum(max(float(w.ratedS.to("VA")) for w in t.TankConfiguration.TransformerWinding)
                   for t in mine) == pytest.approx(_glm_kva(config) * 1000), xf.name
        for tank in mine:
            z, g, b, _ = _tank_impedance(tank.TankConfiguration)
            secondary = _winding(tank.TankConfiguration, 2)
            coil = float(secondary.baseU.to("V"))
            if len(tank.TankConfiguration.TransformerWinding) == 3:  # a 240 V service as a center tap (S6-10): its
                coil *= 2  # %Z is the full winding's, X1 to X3, two halves; the star sums to GridLAB-D's zt on 240 V
            coil_base = coil ** 2 / float(secondary.baseS.to("VA"))
            delta = str(config.connect_type) == "DELTA_DELTA"
            per_phase = coil_base / 3 if delta else coil_base  # GridLAB-D's zt is the wye equivalent
            assert z * per_phase == pytest.approx(zt, rel=1e-9), tank.mRID
            if shunt is not None:
                assert g / per_phase == pytest.approx(1 / (shunt.real * zt_base), rel=1e-9), tank.mRID
                assert b / per_phase == pytest.approx(1 / (shunt.imag * zt_base), rel=1e-9), tank.mRID


# -- import and bind: the atom ------------------------------------------------------------------------------------

def test_atom_goldens():
    documents = parts(read(ATOM / "transformer.glm"), MODEL)
    for name in PARTS:
        assert_matches_golden(documents[name], ATOM / f"transformer.{name}.cimtbl")


def test_atom_binds(scope):
    model = read(ATOM / "transformer.glm")
    network = glm_to_cim(model, name=MODEL)
    assert_gridlabd_ohms(model, network)
    transformers = {str(x.mRID): x for x in network.list_by_class(cim.PowerTransformer)}

    def ends(name):
        return {e.endNumber: (str(e.Terminal.ConnectivityNode.mRID), e.connectionKind.value, e.grounded)
                for e in transformers[name].PowerTransformerEnd}

    def phase_ends(name):
        return sorted((p.sequenceNumber, p.phase.value) for e in transformers[name].PowerTransformerEnd
                      for p in e.Terminal.TransformerEnd if isinstance(p, cim.TransformerPhaseEnd))

    assert ends("xf_xf_dg") == {1: ("n2", "D", False), 2: ("m_dg", "Yn", True)}
    assert ends("xf_xf_dd") == {1: ("n2", "D", False), 2: ("m_dd", "D", False)}
    assert phase_ends("xf_xf_xfm1") == []  # a one-tank instance: the terminal phases say it (S3b-7)
    assert phase_ends("xf_xf_tpoletop") == [(1, "B"), (2, "N"), (3, "s1"), (4, "s2"), (5, "N")]
    # the bank: a tank per can, the cans' lugs on the bank's conductors (S3b-9)
    bank = transformers["xf_xf_bank3"]
    assert sorted(str(t.TankConfiguration.mRID) for t in bank.TransformerTanks) == [
        "xc_xc_bank3_A", "xc_xc_bank3_B", "xc_xc_bank3_C"]
    assert {str(t.TankConfiguration.BankConfiguration.mRID) for t in bank.TransformerTanks} == {"xb_xc_bank3"}
    assert phase_ends("xf_xf_bank3") == [(1, "A"), (2, "B"), (3, "C"), (4, "N"), (5, "A"), (6, "B"), (7, "C"),
                                         (8, "N")]
    can_c = next(t.TankConfiguration for t in bank.TransformerTanks if str(t.mRID).endswith("_C"))
    assert sorted((lug.designation, lug.sequenceNumber) for lug in can_c.TransformerLugs) == [
        ("H1", 3), ("H2", 4), ("X1", 7), ("X2", 8)]
    # 3 / n on a CN can: GridLAB-D's 0.00133+0.00667j on 480² / 75 kVA is 3 x on the can (S3b-4)
    can = next(c for c in network.list_by_class(cim.TransformerTankConfiguration)
               if str(c.mRID) == "xc_transformer_configuration:1")
    assert float(can.percentImpedance) == pytest.approx(3 * 100 * abs(complex(0.00133, 0.00667)))
    limits = sorted(float(v.normalValue.to("A")) for s in transformers["xf_xf_xfm1"].OperationalLimitSet
                    for v in s.OperationalLimitValue)
    assert limits == [76.33, 104.09]


# -- fail fast -------------------------------------------------------------------------------------------------------

def raises(tmp_path, text: str, match: str):
    """The atom plus ``text`` must raise ``match``."""
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "transformer.glm"}"\n'
                    "object meter { name mx; phases ABCN; nominal_voltage 277.13; }\n" + text)
    with pytest.raises(ValueError, match=match):
        GlmImporter(MODEL).to_cimtbl(read(path))


def _config(name: str, body: str) -> str:
    return (f"object transformer_configuration {{ name {name}; primary_voltage 4160; secondary_voltage 480; "
            f"power_rating 75; {body} }}\n")


def test_unset_impedance_raises(tmp_path):
    raises(tmp_path, _config("cx", "connect_type WYE_WYE;"), "cx: impedance None; resistance and reactance")


COIL_RATED = """
object meter { name m_s1; phases AN; nominal_voltage 120; }
object meter { name m_s1b; phases BN; nominal_voltage 120; }
object meter { name m_s3; phases ABCN; nominal_voltage 277.13; }
object meter { name m_s2; phases CN; nominal_voltage 120; }
object transformer_configuration { name xc_s1; connect_type SINGLE_PHASE; primary_voltage 2401.78;
                                   secondary_voltage 120; power_rating 25; impedance 0.01+0.02j; }
object transformer_configuration { name xc_s3; connect_type WYE_WYE; primary_voltage 2401.78;
                                   secondary_voltage 277.13; power_rating 150; impedance 0.01+0.02j; }
object transformer_configuration { name xc_s2; connect_type SINGLE_PHASE; primary_voltage 2401.78;
                                   secondary_voltage 240; power_rating 50; impedance 0.011+0.018j; }
object transformer { name xf_s1; phases AN; from n2; to m_s1; configuration xc_s1; }
object transformer { name xf_s1b; phases BN; from n2; to m_s1b; configuration xc_s1; }
object transformer { name xf_s3; phases ABCN; from n2; to m_s3; configuration xc_s3; }
object transformer { name xf_s2; phases CN; from n2; to m_s2; configuration xc_s2; }
"""


def test_coil_rated_wyes_keep_gridlabds_ohms(tmp_path, scope):
    """A wye whose voltages are its buses' nominal_voltage (phase to neutral, the Milsoft exports) is rated by the
    coil: baseU as written, ratedU on its bus's system, %Z x S_coil / S_total; SINGLE_PHASE is a WYE_WYE, and one
    template serves A and B (S6). A 120 V one-phase service is a split-phase leg: ratedU 240, its bus 240 V; a 240 V one is a center tap whose
    %Z is on the full winding (S6-10)."""
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "transformer.glm"}"\n' + COIL_RATED)
    model = read(path)
    network = glm_to_cim(model, name=MODEL)
    assert_gridlabd_ohms(model, network)
    templates = {str(c.mRID): c for c in network.list_by_class(cim.TransformerTankConfiguration)}

    def voltages(name):
        windings = sorted(templates[name].TransformerWinding, key=lambda w: str(w.mRID))
        return [(float(w.ratedU.to("V")), float(w.baseU.to("V"))) for w in windings]

    assert voltages("xc_xc_s1") == [(pytest.approx(4160.0, rel=1e-5), 2401.78), (240.0, 120.0)]
    assert voltages("xc_xc_s3") == [(pytest.approx(4160.0, rel=1e-5), 2401.78), (pytest.approx(480.0, rel=1e-4),
                                                                                    277.13)]
    z = 100 * abs(complex(0.01, 0.02))
    assert float(templates["xc_xc_s1"].percentImpedance) == pytest.approx(z)
    assert float(templates["xc_xc_s3"].percentImpedance) == pytest.approx(z / 3)
    nodes = {str(n.mRID): n for n in network.list_by_class(cim.ConnectivityNode)}
    assert float(nodes["m_s1"].BaseVoltage.nominalVoltage.to("V")) == 240.0
    ends = {str(end.mRID): end for end in network.list_by_class(cim.PowerTransformerEnd)}
    assert (ends["xf_xf_s1_2"].Terminal.phases.value, ends["xf_xf_s3_2"].Terminal.phases.value) == ("s1N", "ABCN")
    # the leg is one split-phase half, as a center tap's s1: kind I on the instance. A one-phase template is a can
    # by lugs (TankEnds are three-phase only), landing on the instance's own phase: s1 on A, B for xf_s1b
    assert ends["xf_xf_s1_2"].connectionKind is cim.WindingConnection.I
    assert not templates["xc_xc_s1"].TransformerTankEnd and templates["xc_xc_s3"].TransformerTankEnd
    phase_ends = {str(end.mRID): (end.sequenceNumber, end.phase.value)
                  for end in network.list_by_class(cim.TransformerPhaseEnd) if str(end.mRID).startswith("xf_xf_s1b_")}
    assert phase_ends == {"xf_xf_s1b_1_B": (1, "B"), "xf_xf_s1b_1_N": (2, "N"), "xf_xf_s1b_2_s1": (3, "s1"),
                          "xf_xf_s1b_2_N": (4, "N")}


def test_a_wye_off_its_bus_voltage_raises(tmp_path):
    raises(tmp_path, "object transformer_configuration { name cx; connect_type SINGLE_PHASE; primary_voltage 3000; "
                     "secondary_voltage 120; power_rating 25; impedance 0.01+0.02j; }\n"
                     "object meter { name my; phases AN; nominal_voltage 120; }\n"
                     "object transformer { name x; phases AN; from n2; to my; configuration cx; }",
           "primary_voltage 3 kV of cx is neither the 2.40178 kV nominal_voltage of its from bus n2")


def test_phase_ratings_that_miss_the_total_raise(tmp_path):
    raises(tmp_path, _config("cx", "connect_type WYE_WYE; impedance 0.01+0.02j; powerA_rating 50;"),
           r"phase ratings sum to 50.0, not power_rating 75.0")


def test_half_impedance_on_a_wye_raises(tmp_path):
    raises(tmp_path, _config("cx", "connect_type WYE_WYE; impedance 0.01+0.02j; impedance1 0.01+0.02j;"),
           "impedance1/impedance2 on WYE_WYE")


def test_a_center_tap_star_other_than_gridlabds_split_raises(tmp_path):
    raises(tmp_path, "object transformer_configuration { name cx; connect_type SINGLE_PHASE_CENTER_TAPPED; "
                     "primary_voltage 2400; secondary_voltage 120; powerA_rating 25; impedance 0.01+0.02j; "
                     "impedance1 0.01+0.02j; impedance2 0.01+0.02j; }",
           "is not GridLAB-D's split of one R \\+ jX")


def test_shunt_on_a_delta_raises(tmp_path):
    raises(tmp_path, _config("cx", "connect_type DELTA_DELTA; impedance 0.01+0.02j; shunt_impedance 500+400j;"),
           "a shunt on DELTA_DELTA")


def test_no_load_loss_raises(tmp_path):
    raises(tmp_path, _config("cx", "connect_type WYE_WYE; impedance 0.01+0.02j; no_load_loss 0.002;"),
           "no_load_loss set; not mapped")


def test_center_tap_on_an_unrated_phase_raises(tmp_path):
    raises(tmp_path, "object triplex_node { name tx; phases AS; nominal_voltage 120; }\n"
                     "object transformer { name x; phases AS; from n2; to tx; configuration xcon_ct5B; }",
           "wire it differently")


def test_wye_without_neutral_raises(tmp_path):
    raises(tmp_path, "object transformer { name x; phases ABC; from n2; to mx; configuration xc_unused; }",
           "phases ABC without N on the WYE_WYE xc_unused")


def test_two_wirings_of_one_configuration_raise(tmp_path):
    raises(tmp_path, "object meter { name my; phases AN; nominal_voltage 277.13; }\n"
                     "object transformer { name x; phases AN; from n5; to my; configuration xcon_xfm1; }",
           r"xcon_xfm1: transformers x \(on A\) and xf_xfm1 \(on ABC\) wire it differently")


# -- the deck sweep's check (test_cimtbl_sweep.py) -----------------------------------------------------------------

def assert_transformers(model, network) -> None:
    """Every transformer and every configuration is written (S3b-1), each tank with GridLAB-D's own ohms."""
    assert len(network.list_by_class(cim.PowerTransformer)) == model.count(schema.Transformer)
    configurations = {str(c.mRID) for c in network.list_by_class(cim.TransformerTankConfiguration)}
    banks = {str(b.mRID) for b in network.list_by_class(cim.TransformerBankConfiguration)}
    for config in model.list_by_class(schema.TransformerConfiguration):
        assert f"xc_{config.name}" in configurations or f"xb_{config.name}" in banks, config.name
    assert_gridlabd_ohms(model, network)

"""S3c: regulators: classification, the atom, GridLAB-D's tap and control math, fail fast; the decks run in
test_cimtbl_sweep.py."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden, record_diff
from cimtables.document import format_document
from cimhub_core.getters.transformer import TransformerForm, get_transformer_model
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.cimtbl import regulator
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

ATOM = Path(__file__).parent / "atoms" / "regulator"
MODEL = "reg"


def read(path: Path, **kwargs):
    return GlmReader(path, **kwargs).read_all()


def regulator_part(model, name: str):
    return next(part for part in GlmImporter(name).to_cimtbl(model).parts if part.name == "regulator")


@pytest.mark.parametrize("fields, native", ((regulator.FIELDS, regulator.NATIVE_CLASS),
                                            (regulator.CONFIGURATION_FIELDS, regulator.CONFIGURATION_CLASS)),
                         ids=("regulator", "regulator_configuration"))
def test_every_slot_is_classified(fields, native):
    check_fields(fields, native)


# -- GridLAB-D's math: from the configuration by the C++ formulas, against the bound units --------------------------

def assert_gridlabd_regulation(model, network) -> None:
    """Every unit's tap changer gives GridLAB-D's tap and step (``regulator.cpp:244``, ``:262``) and its control
    GridLAB-D's band (``:245``); a unit per wired phase on INDIVIDUAL, rated at its continuous rating x baseU, with
    the series ``regulator_resistance`` and the stand-in x as the transformer getter reads them (S3c-2)."""
    units = {str(vr.mRID): vr for vr in network.list_by_class(cim.VoltageRegulator)}
    for reg in model.list_by_class(schema.Regulator):
        config = model.by_name(reg.configuration)
        letters = "".join(letter for letter in "ABC" if letter in str(reg.phases))
        bank = str(config.control_level) == "BANK"
        names = [f"xf_{reg.name}"] if bank else [f"xf_{reg.name}_{letter}" for letter in letters]
        assert sorted(name for name in units if name.startswith(f"xf_{reg.name}")) == sorted(names), reg.name
        for name, letter in zip(names, letters):
            vr = units[name]
            assert vr.construction.value == f"type{config.Type or 'B'}"
            ends = sorted(vr.AutoTransformerEnd, key=lambda end: end.endNumber)
            read = get_transformer_model(vr)
            base_u = float(ends[0].baseU.to("V"))
            amps = float(getattr(reg, f"continuous_rating_{letters[0] if bank else letter}"))
            rated_s = amps * base_u * (3 ** 0.5 if bank and len(letters) == 3 else 1)
            assert [float(end.ratedS.to("VA")) for end in ends] == pytest.approx([rated_s] * 2), name
            ohms = 1e-4 if reg.regulator_resistance is None else float(reg.regulator_resistance)
            [mesh] = read.mesh.values()
            assert (read.form, list(read.mesh)) == (TransformerForm.AUTO, [(1, 2)]), name
            assert (mesh.r, mesh.x) == (pytest.approx(ohms / (base_u ** 2 / rated_s) * 100), pytest.approx(0.01))
            assert [winding.end for winding in read.windings] == ends
            assert [end.Terminal.phases.value for end in ends] == [f"{letters if bank else letter}N"] * 2
            tap = ends[1].RatioTapChanger
            given = getattr(reg, f"tap_{letter}")
            given = given if given is not None else getattr(config, f"tap_pos_{letter}")
            assert tap.step == (given or 0), name
            assert (tap.lowStep, tap.highStep) == (-config.lower_taps, config.raise_taps)
            assert float(tap.stepVoltageIncrement) / 100 == pytest.approx(float(config.regulation) / config.raise_taps)
            control = tap.TapChangerControl
            assert control.Terminal is ends[1].Terminal
            assert control.enabled is (str(config.Control or "MANUAL") != "MANUAL")
            if config.band_center is not None and str(config.Control) != "LINE_DROP_COMP":
                assert control.targetValue == pytest.approx(float(config.band_center))
                assert control.targetDeadband == pytest.approx(float(config.band_width))


# -- tier 1 / 1b: the atom ----------------------------------------------------------------------------------------

def test_atom_golden():
    assert_matches_golden(regulator_part(read(ATOM / "regulator.glm"), MODEL), ATOM / "regulator.regulator.cimtbl")


def test_atom_binds(scope):
    model = read(ATOM / "regulator.glm")
    network = glm_to_cim(model, name=MODEL)
    assert_gridlabd_regulation(model, network)
    controls = {str(c.mRID): c for c in network.list_by_class(cim.TapChangerControl)}
    # LINE_DROP_COMP: the band on the PT secondary, the compensator on 1 A CT secondary amps (regulator.cpp:1316)
    ldc = controls["rc_reg_ldc_A"]
    assert (ldc.targetValue, ldc.targetDeadband, ldc.lineDropCompensation) == (2440.0, 40.0, True)
    assert float(ldc.lineDropR.to("ohm")) == pytest.approx(3 * 20 / 700)
    # BANK: one gang unit on ABC at its line voltage, monitoring PT_phase
    bank = next(vr for vr in network.list_by_class(cim.VoltageRegulator) if str(vr.mRID) == "xf_reg_bank")
    assert controls["rc_reg_bank"].monitoredPhase.value == "B"
    assert float(bank.AutoTransformerEnd[0].baseU.to("kV")) == pytest.approx(2.40178 * 3 ** 0.5)
    # every tap change waits dwell_time + time_delay (regulator.cpp:598-611)
    tap = next(t for t in network.list_by_class(cim.RatioTapChanger) if str(t.mRID) == "rc_reg_output_A_tap")
    assert (float(tap.initialDelay.to("s")), float(tap.subsequentDelay.to("s"))) == (45.0, 45.0)


# -- fail fast -------------------------------------------------------------------------------------------------------

def raises(tmp_path, text: str, match: str):
    """The atom plus ``text`` must raise ``match``."""
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "regulator.glm"}"\n'
                    "object node { name rx; phases ABCN; nominal_voltage 2401.78; }\n" + text)
    with pytest.raises(ValueError, match=match):
        GlmImporter(MODEL).to_cimtbl(read(path))


RATED = "continuous_rating_A 300; continuous_rating_B 300; continuous_rating_C 300;"


def _regulator(body: str, phases: str = "ABCN", regulator_body: str = RATED) -> str:
    return (f"object regulator_configuration {{ name cx; raise_taps 16; lower_taps 16; {body} }}\n"
            f"object regulator {{ name x; from n2; to rx; phases {phases}; configuration cx; {regulator_body} }}\n")


def test_unrated_regulator_raises(tmp_path):
    """GLM has no kVA and GridLAB-D's 1000 A default is not the regulator's: glm-repair rates the deck (S3c-2)."""
    raises(tmp_path, _regulator("connect_type WYE_WYE;", phases="BN", regulator_body=""),
           r"regulator x: no continuous_rating_B; ratedS is the continuous rating x baseU")


def test_delta_connection_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type CLOSED_DELTA;"), "connect_type CLOSED_DELTA; WYE_WYE is mapped")


def test_unset_taps_raise(tmp_path):
    raises(tmp_path, "object regulator_configuration { name cx; connect_type WYE_WYE; raise_taps 16; }\n"
                     "object regulator { name x; from n2; to rx; phases ABCN; configuration cx; }",
           "raise_taps 16, lower_taps None; both must be positive")


def test_automatic_control_without_regulation_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; Control OUTPUT_VOLTAGE;"), "regulation unset or 0")


def regulator_text(tmp_path, text: str) -> str:
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "regulator.glm"}"\n'
                    "object node { name rx; phases ABCN; nominal_voltage 2401.78; }\n" + text)
    return format_document(regulator_part(read(path), MODEL))


def test_remote_node_on_its_own_output_is_output_voltage(tmp_path):
    """GridLAB-D reads the voltages OUTPUT_VOLTAGE reads (regulator.cpp:1376-1420), S6."""
    band = "connect_type WYE_WYE; regulation 0.1; band_center 2401; band_width 20;"
    remote = regulator_text(tmp_path, _regulator(f"{band} Control REMOTE_NODE;",
                                                 regulator_body=f"{RATED} sense_node rx;"))
    output = regulator_text(tmp_path, _regulator(f"{band} Control OUTPUT_VOLTAGE;"))
    assert record_diff(output, remote) == []


def test_remote_node_elsewhere_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; Control REMOTE_NODE; regulation 0.1;", regulator_body=
                                f"{RATED} sense_node r1;"), "REMOTE_NODE senses r1, not its own output rx")


def test_sense_node_on_another_control_is_listed(tmp_path):
    text = regulator_text(tmp_path, _regulator("connect_type WYE_WYE; Control OUTPUT_VOLTAGE; regulation 0.1;",
                                               regulator_body=f"{RATED} sense_node rx;"))
    assert "ignored on Control OUTPUT_VOLTAGE: sense_node rx" in text


def test_reverse_flow_control_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; reverse_flow_control LOCK_NEUTRAL;"),
           "reverse_flow_control LOCK_NEUTRAL; not mapped")


def test_phase_selection_on_individual_is_listed(tmp_path):
    """GridLAB-D reads each phase on INDIVIDUAL (regulator.cpp:1328, :1378), S6."""
    text = regulator_text(tmp_path, _regulator("connect_type WYE_WYE; PT_phase ABC; CT_phase ABC;"))
    assert "ignored on INDIVIDUAL (GridLAB-D reads each phase): PT_phase ABC, CT_phase ABC" in text


def test_bank_on_its_one_phase_is_one_unit(tmp_path, scope):
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "regulator.glm"}"\n'
                    "object node { name rx; phases ABCN; nominal_voltage 2401.78; }\n"
                    + _regulator("connect_type WYE_WYE; control_level BANK; PT_phase B; CT_phase B;", phases="BN"))
    network = glm_to_cim(read(path), name=MODEL)
    units = {str(vr.mRID): vr for vr in network.list_by_class(cim.VoltageRegulator)
             if str(vr.mRID) == "xf_x" or str(vr.mRID).startswith("xf_x_")}
    assert list(units) == ["xf_x"]
    assert {end.Terminal.phases.value for end in units["xf_x"].AutoTransformerEnd} == {"BN"}


def test_bank_taps_that_differ_raise(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; control_level BANK; PT_phase A; CT_phase A; tap_pos_A 1;"),
           r"BANK taps \[0, 1\] differ")


def test_tap_outside_the_range_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; tap_pos_A 17;"), "tap_pos_A 17 is outside -16..\\+16")


def test_compensator_without_ratios_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; compensator_r_setting_A 3;"),
           "compensator settings on A without power_transducer_ratio")


def test_split_phase_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE;", phases="AS"), "phases AS are not all on its from")

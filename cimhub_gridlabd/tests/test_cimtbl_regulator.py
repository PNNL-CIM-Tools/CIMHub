"""S3c: regulators: classification, the atom, GridLAB-D's tap and control math, fail fast, decks."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from conftest import BIND_STOPS, deck, deck_params, defines
from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_gridlabd.glm_reader import GlmParseError, GlmReader
from cimhub_gridlabd.importer.cimtbl import regulator
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

ATOM = Path(__file__).parent / "atoms" / "regulator"
GOLDENS = Path(__file__).parent / "goldens"
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
    GridLAB-D's band (``:245``); a unit per wired phase on INDIVIDUAL, all ideal (no mesh)."""
    units = {str(vr.mRID): vr for vr in network.list_by_class(cim.VoltageRegulator)}
    assert not network.list_by_class(cim.TransformerMeshImpedance) or all(
        not isinstance(m.FromTransformerEnd, cim.AutoTransformerEnd)
        for m in network.list_by_class(cim.TransformerMeshImpedance))
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


def _regulator(body: str, phases: str = "ABCN", regulator_body: str = "") -> str:
    return (f"object regulator_configuration {{ name cx; raise_taps 16; lower_taps 16; {body} }}\n"
            f"object regulator {{ name x; from n2; to rx; phases {phases}; configuration cx; {regulator_body} }}\n")


def test_delta_connection_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type CLOSED_DELTA;"), "connect_type CLOSED_DELTA; WYE_WYE is mapped")


def test_unset_taps_raise(tmp_path):
    raises(tmp_path, "object regulator_configuration { name cx; connect_type WYE_WYE; raise_taps 16; }\n"
                     "object regulator { name x; from n2; to rx; phases ABCN; configuration cx; }",
           "raise_taps 16, lower_taps None; both must be positive")


def test_automatic_control_without_regulation_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; Control OUTPUT_VOLTAGE;"), "regulation unset or 0")


def test_remote_node_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; Control REMOTE_NODE; regulation 0.1;", regulator_body=
                                "sense_node n3;"), "sense_node n3; REMOTE_NODE is not mapped")


def test_reverse_flow_control_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; reverse_flow_control LOCK_NEUTRAL;"),
           "reverse_flow_control LOCK_NEUTRAL; not mapped")


def test_phase_selection_on_individual_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; PT_phase A;"), "PT_phase on INDIVIDUAL; not mapped")


def test_bank_taps_that_differ_raise(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; control_level BANK; PT_phase A; CT_phase A; tap_pos_A 1;"),
           r"BANK taps \[0, 1\] differ")


def test_tap_outside_the_range_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; tap_pos_A 17;"), "tap_pos_A 17 is outside -16..\\+16")


def test_compensator_without_ratios_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE; compensator_r_setting_A 3;"),
           "compensator settings on A without power_transducer_ratio")


def test_split_phase_raises(tmp_path):
    raises(tmp_path, _regulator("connect_type WYE_WYE;", phases="AS"), "phases AS; A, B, C and N are mapped")


# -- decks -------------------------------------------------------------------------------------------------------

def test_ieee13_cdpsm_golden():
    model = read(deck("IEEE/IEEE13_cdpsm.glm"), defines=defines("IEEE/IEEE13_cdpsm.glm"))
    assert_matches_golden(regulator_part(model, "IEEE13_cdpsm"), GOLDENS / "IEEE13_cdpsm" / "regulator.cimtbl")


@pytest.mark.parametrize("relative, stop", deck_params(BIND_STOPS))
def test_every_regulator_binds_with_gridlabds_taps(relative, stop, scope):
    if stop is not None:
        with pytest.raises((GlmParseError, ValueError), match=stop):
            glm_to_cim(read(deck(relative), defines=defines(relative)), name=Path(relative).stem)
        return
    model = read(deck(relative), defines=defines(relative))
    network = glm_to_cim(model, name=Path(relative).stem)
    assert_gridlabd_regulation(model, network)

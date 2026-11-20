"""GLM import -> CIM -> DSS export, solved in the engine: the transformer forms the GLM importer writes (S3b) export
and solve. A synthetic deck (no utility data): a template unit by %Z (3-phase WYE_WYE), a 2-phase WYE_WYE and an
unequal bank, both lugged cans (TankEnds are three-phase only), and a center tap, each loaded, behind a recloser at
the feeder head.

GridLAB-D's per unit is on ``secondary_voltage``² / ``power_rating``; each tank's %Z is that moved to its own
nameplate by ``k = 3 S_coil / S_total`` (S3b-4), which DSS reads per phase: 1 on the 3-phase unit, 1.5 on each 25
kVA can of the 2-phase one and on the 50 kVA can of the 100 kVA bank.
"""
from __future__ import annotations

import opendssdirect as dss
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim
from cimhub_opendss import DssReader
from cimhub_opendss.exporter.cim_to_dss import cim_to_dss
from cimhub_opendss.schema import opendss_schema as schema

DECK = """
object substation { name src; bustype SWING; phases ABCN; nominal_voltage 7200; }
object node { name p; phases ABCN; nominal_voltage 7200; }
object recloser { name rc1; phases ABCN; from src; to p; status CLOSED; }
object transformer_configuration { name c3; connect_type WYE_WYE; power_rating 150; primary_voltage 12470;
    secondary_voltage 480; impedance 0.01+0.05j; }
object transformer_configuration { name c2; connect_type WYE_WYE; power_rating 50; primary_voltage 12470;
    secondary_voltage 480; impedance 0.01+0.05j; }
object transformer_configuration { name cct; connect_type SINGLE_PHASE_CENTER_TAPPED; powerA_rating 25;
    primary_voltage 7200; secondary_voltage 120; impedance 0.006+0.0136j; impedance1 0.012+0.0068j;
    impedance2 0.012+0.0068j; }
object transformer_configuration { name cbank; connect_type WYE_WYE; powerA_rating 50; powerB_rating 25;
    powerC_rating 25; primary_voltage 12470; secondary_voltage 208; impedance 0.01+0.02j; }
object node { name s3; phases ABCN; nominal_voltage 277.128; }
object node { name s2; phases BCN; nominal_voltage 277.128; }
object triplex_node { name h; phases AS; nominal_voltage 120; }
object node { name sb; phases ABCN; nominal_voltage 120.089; }
object transformer { name t3; phases ABCN; from p; to s3; configuration c3; }
object transformer { name t2; phases BCN; from p; to s2; configuration c2; }
object transformer { name tct; phases AS; from p; to h; configuration cct; }
object transformer { name tb; phases ABCN; from p; to sb; configuration cbank; }
object load { name l3; parent s3; phases ABCN; nominal_voltage 277.128; constant_power_A 20000+5000j;
    constant_power_B 20000+5000j; constant_power_C 20000+5000j; }
object load { name l2; parent s2; phases BCN; nominal_voltage 277.128; constant_power_B 10000+2000j;
    constant_power_C 10000+2000j; }
object triplex_load { name lh; parent h; phases AS; nominal_voltage 120; constant_power_1 3000+500j;
    constant_power_2 3000+500j; }
object load { name lb; parent sb; phases ABCN; nominal_voltage 120.089; constant_power_A 20000+4000j;
    constant_power_B 10000+2000j; constant_power_C 10000+2000j; }
object transformer_configuration { name c120; connect_type SINGLE_PHASE; power_rating 25; primary_voltage 7200;
    secondary_voltage 120; impedance 0.01+0.02j; }
object transformer_configuration { name c240; connect_type SINGLE_PHASE; power_rating 25; primary_voltage 7200;
    secondary_voltage 240; impedance 0.01+0.02j; }
object node { name v120; phases CN; nominal_voltage 120; }
object node { name v240; phases BN; nominal_voltage 240; }
object transformer { name t120; phases CN; from p; to v120; configuration c120; }
object transformer { name t240; phases BN; from p; to v240; configuration c240; }
object load { name l120; parent v120; phases CN; nominal_voltage 120; constant_power_C 4000+1000j; }
object load { name l240; parent v240; phases BN; nominal_voltage 240; constant_power_B 6000+1500j; }
"""
#: XfmrCode -> (phases, kVs, kVAs, %Rs, X): GLM's z x k, %R split over the windings (a center tap by Hopkinson's rule)
CODES = {
    "c3": (3, [12.47, 0.48], [150, 150], [0.5, 0.5], {"Xhl": 5.0}),
    # an unrated 2-phase wye's cans are named by place, as every instance shares them whatever its phases
    "c2_1": (1, [12.47 / 3 ** 0.5, 0.48 / 3 ** 0.5], [25, 25], [0.75, 0.75], {"Xhl": 7.5}),
    "c2_2": (1, [12.47 / 3 ** 0.5, 0.48 / 3 ** 0.5], [25, 25], [0.75, 0.75], {"Xhl": 7.5}),
    "cbank_a": (1, [12.47 / 3 ** 0.5, 0.208 / 3 ** 0.5], [50, 50], [0.75, 0.75], {"Xhl": 3.0}),
    "cct": (1, [7.2, 0.12, 0.12], [25, 25, 25], [0.6, 1.2, 1.2], {"Xhl": 2.04, "Xht": 2.04, "Xlt": 1.36}),
    # the services, k = 1 (GridLAB-D's base is the coil's): the 240 V coil is a center tap's full winding
    "c120": (1, [7.2, 0.12], [25, 25], [0.5, 0.5], {"Xhl": 2.0}),
    "c240": (1, [7.2, 0.12, 0.12], [25, 25, 25], [0.5, 1.0, 1.0], {"Xhl": 2.4, "Xht": 2.4, "Xlt": 1.6}),
}
BUSES = {"t2_b": ["p.2.0", "s2.2.0"], "t2_c": ["p.3.0", "s2.3.0"], "t3": ["p.1.2.3", "s3.1.2.3"], "tb_a": ["p.1.0", "sb.1.0"],
         "tb_b": ["p.2.0", "sb.2.0"], "tb_c": ["p.3.0", "sb.3.0"], "tct": ["p.1.0", "h.1.0", "h.0.2"],
         "t120": ["p.3.0", "v120.1.0"], "t240": ["p.2.0", "v240.1.0", "v240.0.2"]}
#: a one-phase service (the user's rule): 120 V is the s1 leg to N, 240 V a center tap across s1-s2, both on 240 V
#: systems
SERVICE_LOADS = {"l120": ("v120.1", 0.12), "l240": ("v240.1.2", 0.24)}


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    folder = tmp_path_factory.mktemp("glm_to_dss")
    (folder / "deck.glm").write_text(DECK)
    with cim_scope():
        network = glm_to_cim(GlmReader(folder / "deck.glm").read_all(), name="deck")
        cim_to_dss(network, folder / "deck.dss", name_source="name")
    return folder / "deck.dss"


def test_template_units_export_with_their_percent_impedance(exported):
    model = DssReader(exported).read_all()
    codes = {str(code.name).lower(): code for code in model.list_by_class(schema.Xfmrcode)}
    for name, (phases, kvs, kvas, resistances, reactances) in CODES.items():
        code = codes[name]
        assert (code.phases, code.kVs, code.kVAs, code.pct_Rs) == (phases, pytest.approx(kvs), pytest.approx(kvas),
                                                                   pytest.approx(resistances)), name
        assert {slot: getattr(code, slot) for slot in reactances} == pytest.approx(reactances), name
    transformers = {str(record.name).lower(): record for record in model.list_by_class(schema.Transformer)}
    assert {name: [bus.lower() for bus in record.buses] for name, record in transformers.items()} == BUSES


def test_deck_solves_near_nominal(exported):
    dss.Text.Command(f"compile [{exported}]")
    dss.Text.Command("solve")
    assert dss.Solution.Converged()
    for bus, nominal in (("s3", 277.128), ("s2", 277.128), ("h", 120.0), ("sb", 120.089), ("v120", 120.0),
                         ("v240", 120.0)):
        dss.Circuit.SetActiveBus(bus)
        assert dss.Bus.VMagAngle()[::2] == pytest.approx([nominal] * len(dss.Bus.Nodes()), rel=0.02), bus


def test_one_phase_services_are_split_phase(exported):
    model = DssReader(exported).read_all()
    loads = {str(record.name).lower(): record for record in model.list_by_class(schema.Load)}
    assert {name: (str(loads[name].bus1).lower(), loads[name].kV) for name in SERVICE_LOADS} == SERVICE_LOADS
    [options] = model.list_by_class(schema.Options)
    assert 0.24 in options.voltagebases and 0.12 not in options.voltagebases

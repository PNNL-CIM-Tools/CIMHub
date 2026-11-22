"""S4a: loads: classification, the atoms, GridLAB-D's per-phase power through the load getter, fail fast; the decks run in
test_cimtbl_sweep.py."""
from __future__ import annotations

import math
import re
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimprofiles.units import units

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_core.getters.load import get_load_response, get_phase_loads
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl import load
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

ATOM = Path(__file__).parent / "atoms" / "load"
MODEL = "atom"
SCHEDULED = re.compile(r"^\w+\.value\*([-+.\deE]+)$")
#: a GLM phase suffix -> the consumer's phase child (a delta child is its branch's from-phase), and the consumer
WYE = {"A": ("", "A"), "B": ("", "B"), "C": ("", "C")}
TRIPLEX = {"1": ("", "s1"), "2": ("", "s2"), "12": ("_12", "s1")}


def read(path: Path, **kwargs):
    return GlmReader(path, **kwargs).read_all()


def part(model, name: str, artifact: str):
    return next(document for document in GlmImporter(name).to_cimtbl(model).parts if document.name == artifact)


@pytest.mark.parametrize("native", (schema.Load, schema.TriplexLoad), ids=("load", "triplex_load"))
def test_every_slot_is_classified(native):
    check_fields(load.FIELDS[native], native)


# -- GridLAB-D's math, written out again here: the native record's power per phase against the getter's ------------

def gridlabd_phase_power(model, record, slot_power: str, suffix: str) -> complex:
    """GridLAB-D's constant power of one phase at nominal voltage (load.cpp:940-1073), in VA."""
    text = model.expressions.get((str(record.name), f"base_power_{suffix}"))
    base = getattr(record, f"base_power_{suffix}", None)
    if text is not None:
        base = float(SCHEDULED.match(text).group(1))
    elif base is not None:
        base = units.Quantity(base, registry_unit(model.unit(record, f"base_power_{suffix}"))).to("VA").magnitude
    if base:
        fractions = {kind: getattr(record, f"{kind}_fraction_{suffix}") or 0.0 for kind in load.KINDS}
        if not math.isclose(sum(fractions.values()), 1.0):
            fractions["power"] = 1 - fractions["current"] - fractions["impedance"]
        total = 0j
        for kind, fraction in fractions.items():
            pf = getattr(record, f"{kind}_pf_{suffix}")
            pf = 1.0 if pf is None else pf
            p = 0.0 if pf == 0 else base * fraction * abs(pf)
            q = base * fraction if pf == 0 else math.copysign(p * math.sqrt(1 / pf ** 2 - 1), pf)
            total += complex(p, q)
        return total
    value = getattr(record, slot_power.format(suffix))
    if value is None:
        return 0j
    factor = units.Quantity(1.0, registry_unit(model.unit(record, slot_power.format(suffix)))).to("VA").magnitude
    return complex(value.real, value.imag) * factor


def all_consumers(network) -> dict:
    """mRID -> consumer, a scheduled load's ConformLoad included (the graph is keyed by exact class)."""
    return {str(consumer.mRID): consumer for cls in (cim.EnergyConsumer, cim.ConformLoad)
            for consumer in network.list_by_class(cls)}


def assert_gridlabd_loads(model, network) -> int:
    """Every record's per-phase power is its consumers' (get_phase_loads); returns the consumers checked."""
    consumers = all_consumers(network)
    checked = 0
    for load_class in load.LOAD_CLASSES:
        for record in model.list_by_class(load_class.native):
            if type(record) is not load_class.native:
                continue
            if load_class is load.TRIPLEX_NODE and all(getattr(record, f"power_{suffix}") is None
                                                       for suffix in load_class.suffixes):
                continue  # a plain triplex_node is only a bus
            table = WYE if load_class is load.LOAD else TRIPLEX
            expected: dict[str, dict] = {}
            for suffix, (consumer_suffix, phase) in table.items():
                power = gridlabd_phase_power(model, record, load_class.power, suffix)
                if power:
                    expected.setdefault(consumer_suffix, {})[phase] = power
            for consumer_suffix, phases in expected.items():
                consumer = consumers[f"ld_{record.name}{consumer_suffix}"]
                read = get_phase_loads(consumer)
                assert get_load_response(consumer) is not None
                total = sum(phases.values())
                assert (read.total.p, read.total.q) == (pytest.approx(total.real, abs=1e-6),
                                                        pytest.approx(total.imag, abs=1e-6)), consumer.mRID
                checked += 1
                if len(consumer.EnergyConsumerPhase) < 2:  # one delta branch or the 240 V part: the total is it
                    continue
                for phase, power in phases.items():
                    got = read.per_phase[cim.SinglePhaseKind(phase)]
                    assert (got.p, got.q) == (pytest.approx(power.real, abs=1e-6),
                                              pytest.approx(power.imag, abs=1e-6)), (consumer.mRID, phase)
            if not expected:  # no power: one consumer of p = q = 0
                read = get_phase_loads(consumers[f"ld_{record.name}"])
                assert (read.total.p, read.total.q) == (0.0, 0.0), record.name
    return checked


# -- tier 1 / 1b: the atoms -----------------------------------------------------------------------------------------

def test_atom_goldens():
    model = read(ATOM / "triplex.glm")
    for artifact in ("load", "triplex_load", "triplex_node"):
        assert_matches_golden(part(model, MODEL, artifact), ATOM / f"triplex.{artifact}.cimtbl")


def test_atom_binds(scope):
    model = read(ATOM / "triplex.glm")
    network = glm_to_cim(model, name=MODEL)
    assert assert_gridlabd_loads(model, network) == 9
    consumers = all_consumers(network)
    # ld_delta: GLM's C on a delta load is the CA branch, the binder's child C on AC
    delta = consumers["ld_ld_delta"]
    assert get_phase_loads(delta).connection is cim.PhaseShuntConnectionKind.D
    assert [child.phase.value for child in delta.EnergyConsumerPhase] == ["C"]
    # the mixed fractions: their own zip_ row, which the getter reads as summing to 1
    response = get_load_response(consumers["ld_ld_zip"])
    assert (response.p_power, response.p_current, response.p_impedance) == pytest.approx((65 / 113.5, 28.5 / 113.5,
                                                                                         20 / 113.5), abs=1e-6)
    # the 240 V part is a delta consumer across the legs
    assert get_phase_loads(consumers["ld_tn_load_12"]).connection is cim.PhaseShuntConnectionKind.D
    # no power on any phase: still a consumer (one service), p = q = 0 on its wired phase
    none = consumers["ld_ld_none"]
    assert (float(none.p), float(none.q), none.customerCount) == (0.0, 0.0, 1)
    assert [child.phase.value for child in none.EnergyConsumerPhase] == ["A"]
    # each record is one service: its first consumer counts it, a split-phase record's 240 V part does not again
    assert (consumers["ld_tl_legs"].customerCount, consumers["ld_tl_legs_12"].customerCount) == (1, None)
    # a base zipsched.value*K: a ConformLoad of zipsched's group, which has no schedule (no such player, S8-5)
    for scheduled in ("ld_ld_sched", "ld_tl_house"):
        assert isinstance(consumers[scheduled], cim.ConformLoad)
        assert consumers[scheduled].LoadGroup.name == "zipsched"
        assert consumers[scheduled].LoadGroup.ConformLoadSchedules == []


# -- fail fast -------------------------------------------------------------------------------------------------------

def raises(tmp_path, text: str, match: str):
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "load.glm"}"\n' + text)
    with pytest.raises(ValueError, match=match):
        GlmImporter(MODEL).to_cimtbl(read(path))


def test_base_and_constant_power_on_one_phase_raise(tmp_path):
    raises(tmp_path, "object load { name x; parent n2; phases AN; base_power_A 1000; constant_power_A 10+1j; }",
           "base_power_A and constant_power_A are both set")


@pytest.mark.parametrize("slot", ("constant_current_A", "constant_impedance_A", "constant_power_AN",
                                  "constant_power_A_real"))
def test_explicit_forms_raise(tmp_path, slot):
    raises(tmp_path, f"object load {{ name x; parent n2; phases AN; {slot} 10; }}", f"{slot}.*not mapped")


def test_other_expression_raises(tmp_path):
    raises(tmp_path, "object load { name x; parent n2; phases AN; base_power_A zipsched.value*2+1; }",
           r"only <player>.value\*<number> and <schedule>\*<number> are mapped")


def test_split_phase_load_raises(tmp_path):
    raises(tmp_path, "object load { name x; parent n2; phases AS; constant_power_A 10+1j; }",
           "a split-phase load is a triplex_load")


@pytest.mark.parametrize("record", ("object node { name x; parent n2; phases AN; power_A 10+1j; }",
                                    "object triplex_meter { name x; parent tm1; phases AS; power_12 10+1j; }",
                                    "object triplex_node { name x; parent tm1; phases AS; current_12 1+0j; }"),
                         ids=("node", "triplex_meter", "triplex_node current"))
def test_a_load_on_a_bus_itself_raises(tmp_path, record):
    raises(tmp_path, record, "is a load on the bus itself; not mapped")

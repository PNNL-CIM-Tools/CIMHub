"""Every shape-catalog example loads under cim18v17 (rewrite plan Phase 1c)."""

from __future__ import annotations

from pathlib import Path

import pytest
from cimgraph.models import BusBranchModel
from cimtables import load_model
from cimtables.document import format_document

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.load_response import zip_fractions

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"
BUS_BRANCH = {"line_bus_branch", "behind_transformer"}


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _load(stem: str):
    return load_model(SHAPES / f"{stem}.cimtbl", model_cls=BusBranchModel if stem in BUS_BRANCH else None)


@pytest.mark.parametrize("stem", sorted(path.stem for path in SHAPES.glob("*.cimtbl")))
def test_shape_loads(stem):
    network = _load(stem)
    assert sum(len(objects) for objects in network.graph.values()) > 0


CATALOG = Path(__file__).parents[2] / ".claude" / "skills" / "cimtbl-shapes" / "SKILL.md"


def test_catalog_lists_every_shape():
    catalog = CATALOG.read_text()
    missing = [path.name for path in SHAPES.glob("*.cimtbl") if f"`{path.name}`" not in catalog]
    assert not missing, f"the cimtbl-shapes skill does not list {missing}"


def test_instance_by_template_reaches_its_template():
    network = _load("transformer_by_template")
    tanks = {tank.mRID: tank for tank in network.graph[network.cim.TransformerTank].values()}
    assert tanks["xf_t1_tank"].TankConfiguration.mRID == "xc_xfm1"
    assert tanks["xf_t2_tank"].TankConfiguration.mRID == "xc_ct5"


def test_line_by_impedance_units():
    network = _load("line_by_impedance")
    [sequence] = network.graph[network.cim.PerLengthSequenceImpedance].values()
    assert float(sequence.bch.to("uS/km")) == pytest.approx(3.93235)
    data = {(d.row, d.column): d
            for d in network.graph[network.cim.PhaseImpedanceData].values()}
    assert float(data[(2, 1)].r.to("ohm/mi")) == pytest.approx(0.2066)


def test_bus_branch_per_unit_converts_on_the_system_base():
    network = _load("line_bus_branch")
    [line] = network.graph[network.cim.ACLineSegment].values()
    z_base = 115.0**2 / 100.0  # ohm, 115 kV on 100 MVA
    assert float(line.r.to("ohm")) == pytest.approx(0.0194 * z_base)


def test_common_zip_rows_are_the_core_zip_fractions(tmp_path):
    document = zip_fractions()
    path = tmp_path / f"{document.name}.cimtbl"
    path.write_text(format_document(document), encoding="utf-8")

    def fractions(network):
        return {zip_model.mRID: (zip_model.exponentModel, zip_model.pConstantPower, zip_model.pConstantCurrent,
                                 zip_model.pConstantImpedance, zip_model.qConstantPower, zip_model.qConstantCurrent,
                                 zip_model.qConstantImpedance)
                for zip_model in network.graph[network.cim.LoadResponseCharacteristic].values()}

    assert fractions(_load("common")) == fractions(load_model(path))


def test_behind_transformer_puts_the_equipment_on_the_internal_node():
    """The step-up / converter transformer joins the bus to the internal node, which only it and the equipment touch
    (plan C8)."""
    network = _load("behind_transformer")
    ends = {end.mRID: end for end in network.graph[network.cim.PowerTransformerEnd].values()}
    [converter] = network.graph[network.cim.CsConverter].values()
    [machine] = network.graph[network.cim.SynchronousMachine].values()
    assert converter.Terminals[0].TopologicalNode is ends["cs_c1_xf_2"].Terminal.TopologicalNode
    assert machine.Terminals[0].TopologicalNode.mRID == "gen_g1_int"
    assert ends["cs_c1_xf_1"].Terminal.TopologicalNode.mRID == "bus_1"
    assert float(ends["cs_c1_xf_1"].x.to("ohm")) == pytest.approx(12.9)

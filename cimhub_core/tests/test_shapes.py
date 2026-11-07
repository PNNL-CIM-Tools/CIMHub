"""Every shape-catalog example loads under cim18v17 (rewrite plan Phase 1c)."""

from __future__ import annotations

from pathlib import Path

import pytest
from cimgraph.models import BusBranchModel
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"
BUS_BRANCH = {"line_bus_branch"}


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

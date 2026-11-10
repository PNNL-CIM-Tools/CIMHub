"""ditto (DSS → GDM) over the vendored public DSS decks: each imports, or stops only at pending classes.

The stop list shrinks phase by phase (TEST_DESIGN.md). Opt-in: ``CIMHUB_GDMLOADER=1`` adds the gdmloader systems,
run as ``uv run --with gdmloader pytest``; it downloads, so it never runs in CI.
"""

import os
from pathlib import Path

import opendssdirect
import pytest

from cimhub_gdm import gdm_to_cim

opendssdirect.Basic.AllowChangeDir(False)
opendssdirect.Basic.AllowEditor(False)

DECKS = Path(__file__).parents[2] / "cimhub_opendss" / "tests" / "decks"
DITTO_FAILS = pytest.mark.xfail(reason="ditto 0.1.8 cannot read this deck (GDM_MAPPING.md §14)", strict=True)

DITTO_DECKS = [
    "IEEE/IEEE13_original/IEEE13Nodeckt.dss",
    "IEEE/IEEE123/IEEE123Master.dss",
    "IEEE/IEEE37/ieee37.dss",
    "IEEE/IEEE4_xfmrs/4bus-OYOD-UnBal.dss",
    pytest.param("IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss", marks=DITTO_FAILS),
    pytest.param("IEEE/IEEE13_assets/IEEE13_Assets.dss", marks=DITTO_FAILS),
]

GDMLOADER_SYSTEMS = ["testcasev1", "three_feeder_switch", "three_feeder_variable_load_switch",
                     "three_feeder_variable_load_no_switch", "three_feeder_variable_load_switch_v2",
                     "three_feeder_variable_load_no_switch_v2", "p5r", "p1rhs7_1247"]


def assert_imports_or_stops_at_pending(system, name: str) -> None:
    """Every stop must be a pending class; anything else (unclassified, orphan, fail-fast) is a bug."""
    system.name = name
    try:
        gdm_to_cim(system)
    except ValueError as error:
        lines = str(error).splitlines()
        assert lines[0] == "GDM system cannot be imported:", str(error)
        unexpected = [line for line in lines[1:] if ": pending, " not in line]
        assert unexpected == [], str(error)


@pytest.mark.parametrize("deck", DITTO_DECKS)
def test_ditto_deck(deck):
    reader = pytest.importorskip("ditto.readers.opendss.reader")
    assert_imports_or_stops_at_pending(reader.Reader(DECKS / deck).get_system(), Path(deck).stem)


@pytest.mark.skipif(os.environ.get("CIMHUB_GDMLOADER") != "1", reason="opt-in: CIMHUB_GDMLOADER=1 (downloads)")
@pytest.mark.parametrize("dataset", GDMLOADER_SYSTEMS)
def test_gdmloader_system(dataset):
    source = pytest.importorskip("gdmloader.source")
    constants = pytest.importorskip("gdmloader.constants")
    from gdm.systems.distribution import DistributionSystem
    loader = source.SystemLoader()
    loader.add_source(constants.GCS_CASE_SOURCE)
    system = loader.load_dataset(system_type=DistributionSystem, source_name=constants.GCS_CASE_SOURCE.name,
                                 dataset_name=dataset, version="2_4_1")
    assert_imports_or_stops_at_pending(system, dataset)

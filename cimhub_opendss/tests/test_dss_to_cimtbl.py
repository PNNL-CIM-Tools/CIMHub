"""The orchestrator: master document, Import order, and the IEEE13_CDPSM artifacts binding (S0 exit)."""

from __future__ import annotations

import pytest

from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_opendss import DssImporter, DssReader, dss_to_cim
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.dss_to_cimtbl import MAPPING_ORDER
from cimhub_opendss.schema import opendss_schema as schema

from conftest import DECKS

IEEE13 = DECKS / "IEEE" / "IEEE13_CDPSM" / "IEEE13_CDPSM.dss"
GOLDENS = DECKS.parent / "goldens" / "IEEE13_CDPSM"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def ieee13():
    return DssReader(IEEE13).read_all()


def test_master_matches_golden(ieee13):
    documents = DssImporter("IEEE13_CDPSM").to_cimtbl(ieee13)
    assert_matches_golden(documents.master, GOLDENS / "IEEE13_CDPSM.cimtbl")


def test_parts_follow_the_mapping_order(ieee13):
    documents = DssImporter("IEEE13_CDPSM").to_cimtbl(ieee13)
    assert [part.name for part in documents.parts] == ["linecode"]
    assert len(MAPPING_ORDER) == len({native_class for native_class, _ in MAPPING_ORDER})


def test_a_class_with_no_records_writes_no_part(tmp_path):
    deck = tmp_path / "bare.dss"
    deck.write_text("New Circuit.bare basekv=12.47\n")
    documents = DssImporter("bare").to_cimtbl(DssReader(deck).read_all())
    assert documents.parts == [] and documents.master.statements == []


def test_ieee13_binds_under_cim18v17(ieee13, tmp_path):
    network = dss_to_cim(ieee13, name="IEEE13_CDPSM", artifact_dir=tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["IEEE13_CDPSM.cimtbl", "linecode.cimtbl"]
    impedances = network.graph[network.cim.PerLengthPhaseImpedance]
    assert len(impedances) == 7
    [mtx601] = [z for z in impedances.values() if z.name == "mtx601"]
    data = {(d.row, d.column): d for d in mtx601.PhaseImpedanceData}
    assert float(data[(2, 1)].r.to("ohm/mi")) == pytest.approx(0.1535)  # verbatim from the deck
    assert float(data[(3, 3)].x.to("ohm/mi")) == pytest.approx(1.0348)


def test_dss_defaults_are_typed_as_deck_text():
    defaults = dss_defaults(schema.Load)
    assert defaults["model"].text == "ConstantPQ"  # int(1) on an enum slot is DSS code 1
    assert (defaults["pf"], defaults["CVRwatts"], defaults["CVRvars"]) == (0.88, 1.0, 2.0)
    assert dss_defaults(schema.Options)["defaultbasefreq"] == 60.0

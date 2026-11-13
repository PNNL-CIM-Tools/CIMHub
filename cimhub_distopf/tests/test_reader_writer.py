"""DistopfReader / DistopfWriter on the public DistOPF cases: counts, and read -> write -> read equality."""

from dataclasses import asdict
from pathlib import Path

import pytest
from cimhub_core.base import FormatReader, FormatWriter

import cimhub_distopf.schema.distopf as schema
from cimhub_distopf import DistopfReader, DistopfWriter
from cimhub_distopf.csv_layout import CSV_FILES

CASES = Path(__file__).parent / "cases"


def test_contract():
    assert issubclass(DistopfReader, FormatReader)
    assert issubclass(DistopfWriter, FormatWriter)


@pytest.mark.parametrize(
    ("case", "counts"),
    [
        ("ieee13", {schema.BusRecord: 16, schema.BranchRecord: 15, schema.CapacitorRecord: 2,
                    schema.RegulatorRecord: 3}),
        ("ieee123_30der", {schema.BusRecord: 130, schema.BranchRecord: 129, schema.GeneratorRecord: 30,
                           schema.CapacitorRecord: 4, schema.BatteryRecord: 2, schema.RegulatorRecord: 5,
                           schema.ScheduleRecord: 24}),
        ("triplex_pv", {schema.BusRecord: 11, schema.BranchRecord: 10, schema.GeneratorRecord: 4}),
    ],
)
def test_counts(case, counts):
    model = DistopfReader(CASES / case).read_all()
    for record_cls in CSV_FILES:
        assert len(model.list_by_class(record_cls)) == counts.get(record_cls, 0), record_cls.__name__


@pytest.mark.parametrize("case", ["ieee13", "ieee123_30der", "triplex_pv"])
def test_round_trip(case, tmp_path):
    first = DistopfReader(CASES / case).read_all()
    DistopfWriter().write(first, tmp_path)
    second = DistopfReader(tmp_path).read_all()
    for record_cls in CSV_FILES:
        assert [asdict(r) for r in second.list_by_class(record_cls)] == [
            asdict(r) for r in first.list_by_class(record_cls)
        ], record_cls.__name__


def test_bad_cell_names_the_line(tmp_path):
    (tmp_path / "cap_data.csv").write_text("id,name,q_a,q_b,q_c,phases\n3,675,x,0.2,0.2,abc\n")
    with pytest.raises(ValueError, match="line 2 of cap_data.csv"):
        DistopfReader(tmp_path).read_all()


def test_unbound_source_raises():
    with pytest.raises(ValueError, match="requires a source directory"):
        DistopfReader().read_all()

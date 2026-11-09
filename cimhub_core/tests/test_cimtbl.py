"""Tests for cimhub_core.cimtbl: the native -> .cimtbl helpers and cimtbl_to_cim."""

from __future__ import annotations

import dataclasses
import math
from typing import Optional

import pytest
from cimtables.document import Column, Document, DocumentSet, Import, Row, Table
from pydantic import BaseModel

from cimhub_core import CimtblImporter
from cimhub_core.cimtbl_testing import atom_documents, cim_scope, record_diff
from cimhub_core.cimtbl import (
    CIM_PROFILE,
    Field,
    cell,
    check_fields,
    cimtbl_to_cim,
    copied_columns,
    field_names,
    fill_defaults,
    fields_stub,
    fields_table,
    lookup,
    mrid,
    parse_default,
    untranscribed_names,
    untranscribed_values,
)


@pytest.fixture
def cim18_scope():
    with cim_scope():
        yield


# --- cell -------------------------------------------------------------------

@pytest.mark.parametrize("value, text", [
    (None, None),
    (True, "true"),
    (False, "false"),
    (3, "3"),
    (500.001020, "500.00102"),
    (4.160000, "4.16"),
    (0.1, "0.1"),
    ("4.160000", "4.160000"),  # reader text is kept as written
    ("", ""),
    ("wire_#2", "wire_#2"),
])
def test_cell_is_verbatim(value, text):
    assert cell(value) == text


def test_cell_float_reads_back_identically():
    value = 1.100017550601472
    assert float(cell(value)) == value


def test_cell_drops_str_subclass():
    class LinecodeName(str):
        pass

    text = cell(LinecodeName("mtx601"))
    assert text == "mtx601" and type(text) is str


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_cell_rejects_non_finite(value):
    with pytest.raises(ValueError):
        cell(value)


def test_cell_rejects_lists():
    with pytest.raises(TypeError, match="map it in the mapper"):
        cell([0.3465, 0.1535])


def test_cell_enum_text():
    from linkml_runtime.linkml_model.meta import EnumDefinition, PermissibleValue
    from linkml_runtime.utils.enumerations import EnumDefinitionImpl

    class ConnectionType(EnumDefinitionImpl):
        wye = PermissibleValue(text="wye")
        _defn = EnumDefinition(name="ConnectionType")

    assert cell(ConnectionType("wye")) == "wye"


# --- mrid / lookup ------------------------------------------------------------

def test_mrid_keeps_source_case():
    assert mrid("xc_", "T1") == "xc_T1"
    assert mrid("xc_", "Spare (DC)") == "xc_Spare (DC)"


def test_mrid_lowercase_for_opendss():
    assert mrid("lc_", "MTX601", lowercase=True) == "lc_mtx601"


@pytest.mark.parametrize("native_id", [None, "", "  "])
def test_mrid_rejects_missing_id(native_id):
    with pytest.raises(ValueError, match="native ID is missing"):
        mrid("xc_", native_id)


def test_lookup():
    table = {"Yg": "Yn", "D": "D"}
    assert lookup(table, "Yg", slot="conn", record_id="T1") == "Yn"
    with pytest.raises(ValueError, match=r"T1: conn='Zg' has no mapping \(known: D, Yg\)"):
        lookup(table, "Zg", slot="conn", record_id="T1")


# --- Field / classification ---------------------------------------------------

@dataclasses.dataclass
class NativeRecord:
    code: str = None
    rated_kva: Optional[float] = None
    primary_kv: Optional[float] = None
    insulation: Optional[str] = None


class PydanticRecord(BaseModel):
    name: str
    rated_power: float = 0.0


FIELDS = {
    "code": Field("copied", (("TransformerTankConfiguration", "name", None),)),
    "rated_kva": Field("copied", (("TransformerWinding", "ratedS", "kVA"),
                                         ("TransformerWinding", "baseS", "kVA"))),
    "primary_kv": Field("structural", note="end 1 winding ratedU (kV)"),
    "insulation": Field("untranscribed"),
}


def test_field_rejects_unknown_kind():
    with pytest.raises(ValueError, match="'TODO' is not one of"):
        Field("TODO")


def test_copied_field_needs_targets():
    with pytest.raises(ValueError, match="names its targets"):
        Field("copied")


def test_copied_columns():
    assert copied_columns(FIELDS, "TransformerWinding") == [
        ("rated_kva", Column("ratedS", "kVA")),
        ("rated_kva", Column("baseS", "kVA")),
    ]
    assert copied_columns(FIELDS, "TransformerCore") == []


def test_copied_columns_fills_unit_words():
    fields = {"r1": Field("copied", (("PerLengthSequenceImpedance", "r", "ohm/{length}"),))}
    assert copied_columns(fields, "PerLengthSequenceImpedance", length="km") == [("r1", Column("r", "ohm/km"))]
    with pytest.raises(KeyError, match="length"):
        copied_columns(fields, "PerLengthSequenceImpedance")


def test_copied_columns_rejects_per_row_values():
    fields = {
        "primary_kv": Field("copied", (("TransformerWinding", "ratedU", "kV"),)),
        "secondary_kv": Field("copied", (("TransformerWinding", "ratedU", "kV"),)),
    }
    with pytest.raises(ValueError, match=r"copied from more than one slot: \['ratedU'\]"):
        copied_columns(fields, "TransformerWinding")


def test_field_names_dataclass_and_pydantic():
    assert field_names(NativeRecord) == ["code", "rated_kva", "primary_kv", "insulation"]
    assert field_names(PydanticRecord) == ["name", "rated_power"]


def test_check_fields_complete():
    check_fields(FIELDS, NativeRecord)


def test_check_fields_reports_missing_and_stale():
    fields = {key: value for key, value in FIELDS.items() if key != "insulation"}
    fields["Gone"] = Field("untranscribed")
    with pytest.raises(AssertionError, match=r"missing \['insulation'\], stale \['Gone'\]"):
        check_fields(fields, NativeRecord)


def test_fields_table_and_stub():
    records = [NativeRecord("T1", 500.00102, 4.16), NativeRecord("T2", 1000.0, 24.9)]
    table = fields_table(NativeRecord, records)
    assert "| `code` | `str` | `T1`, `T2` |  |  |" in table
    assert "| `insulation` | `Optional[str]` |  |  |  |" in table
    assert "| `rated_power` | `float` |" in fields_table(PydanticRecord)
    filled = fields_table(NativeRecord, records, fields=FIELDS)
    assert ("| `rated_kva` | `Optional[float]` | `500.00102`, `1000.0` | copied | "
            "`TransformerWinding.ratedS` (kVA), `TransformerWinding.baseS` (kVA) |") in filled
    assert "| `primary_kv` | `Optional[float]` | `4.16`, `24.9` | structural | end 1 winding ratedU (kV) |" in filled

    stub = fields_stub(NativeRecord, records)
    assert "'primary_kv': Field('TODO', note='4.16, 24.9')," in stub
    namespace = {"Field": Field}
    with pytest.raises(ValueError, match="'TODO' is not one of"):
        exec(stub, namespace)


# --- cimtbl_to_cim / CimtblImporter -------------------------------------------

def _documents(profile=CIM_PROFILE) -> DocumentSet:
    part = Document(
        name="base_voltage",
        profile=CIM_PROFILE,
        statements=[Table("BaseVoltage", [Column("mRID"), Column("nominalVoltage", "kV")],
                          [Row(["bv_4_16kv", "4.16"]), Row(["bv_0_48kv", "0.48"])])],
    )
    master = Document(name="atom", profile=profile, authority="cimhub-test", model="atom",
                      statements=[Import("base_voltage")])
    return DocumentSet(master=master, parts=[part])


def _nominal_kv(network):
    cim = network.cim
    return sorted(float(bv.nominalVoltage.to("kV")) for bv in network.graph[cim.BaseVoltage].values())


def test_cimtbl_to_cim_in_memory(cim18_scope):
    network = cimtbl_to_cim(_documents())
    assert _nominal_kv(network) == [0.48, 4.16]


def test_cimtbl_to_cim_writes_artifact(cim18_scope, tmp_path):
    network = cimtbl_to_cim(_documents(), artifact_dir=tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["atom.cimtbl", "base_voltage.cimtbl"]
    assert "    bv_4_16kv, 4.16" in (tmp_path / "base_voltage.cimtbl").read_text()
    assert _nominal_kv(network) == [0.48, 4.16]


def test_cimtbl_to_cim_onto_network(cim18_scope):
    network = cimtbl_to_cim(_documents())
    second = _documents()
    second.parts[0].statements[0].rows[:] = [Row(["bv_12_47kv", "12.47"])]
    assert cimtbl_to_cim(second, network=network) is network
    assert _nominal_kv(network) == [0.48, 4.16, 12.47]


def test_cimtbl_to_cim_requires_cim18_master():
    with pytest.raises(ValueError, match="declares Profile=None"):
        cimtbl_to_cim(_documents(profile=None))


def test_cimtbl_importer(cim18_scope, tmp_path):
    class AtomImporter(CimtblImporter):
        def to_cimtbl(self, model):
            return _documents()

    network = AtomImporter().to_cim(None, artifact_dir=tmp_path)
    assert _nominal_kv(network) == [0.48, 4.16]
    assert (tmp_path / "atom.cimtbl").exists()


# --- untranscribed (D5) -------------------------------------------------------

def test_untranscribed_values_lists_non_empty_values():
    record = NativeRecord("T1", 500.00102, 4.16, "Liquid")
    assert untranscribed_values(FIELDS, record) == "untranscribed: insulation=Liquid"
    assert untranscribed_values(FIELDS, NativeRecord("T1")) is None
    assert untranscribed_names(FIELDS) == "untranscribed: insulation"


def test_untranscribed_values_wrap():
    fields = {f"Slot{n}": Field("untranscribed") for n in range(20)}
    record = type("Record", (), {f"Slot{n}": "value" for n in range(20)})()
    lines = untranscribed_values(fields, record).splitlines()
    assert len(lines) > 1 and all(len(line) <= 116 for line in lines)


def test_cell_of_a_permissible_value():
    from linkml_runtime.linkml_model.meta import PermissibleValue
    assert cell(PermissibleValue(text="ConstantPQ")) == "ConstantPQ"


# --- native defaults ----------------------------------------------------------

@pytest.mark.parametrize("expression, value", [
    ("float(1.0)", 1.0), ("int(3)", 3), ("integer(2)", 2), ('string("abc")', "abc"), ("true", True),
    ('"false"', "\"false\""), ("False", False), ("Deri", "Deri"), (60.0, 60.0), (True, True),
])
def test_parse_default(expression, value):
    assert parse_default(expression) == value


def test_fill_defaults_fills_unset_read_slots_only():
    record = NativeRecord("T1", None, 4.16, None)
    defaults = {"rated_kva": 500.0, "primary_kv": 12.47, "insulation": "Liquid"}
    filled, comment = fill_defaults(FIELDS, record, defaults)
    assert (filled.rated_kva, filled.primary_kv, filled.insulation) == (500.0, 4.16, None)
    assert comment == "defaulted: rated_kva=500.0"
    assert record.rated_kva is None  # the original is not changed


def test_fill_defaults_keeps_attributes_outside_the_fields():
    """A reader's composite ``record.ID`` is no dataclass field, so ``dataclasses.replace`` alone would drop it."""
    record = NativeRecord("T1", None)
    record.ID = "T1_1"
    filled, _ = fill_defaults(FIELDS, record, {"rated_kva": 500.0})
    assert filled.ID == "T1_1"


def test_fill_defaults_with_nothing_to_fill():
    record = NativeRecord("T1", 500.0)
    assert fill_defaults(FIELDS, record, {"rated_kva": 1.0}) == (record, None)


# --- atom harness -------------------------------------------------------------

def test_atom_documents_skips_empty_parts():
    empty = Document(name="empty", profile=CIM_PROFILE, statements=[])
    documents = atom_documents(_documents().parts[0], empty)
    assert documents.master.statements == [Import("base_voltage")]
    assert [part.name for part in documents.parts] == ["base_voltage"]


def test_record_diff():
    expected = "Profile = cim18v17\nTable BaseVoltage: mRID, nominalVoltage (kV)\n    bv_1, 4.16\n    bv_2, 0.48\n"
    actual = "Profile = cim18v17\n# moved\nTable BaseVoltage: nominalVoltage (V), mRID\n    4160, bv_1\n    12.47, bv_3\n"
    assert record_diff(expected, expected) == []
    assert record_diff(expected, actual) == [
        "missing BaseVoltage bv_2",
        "extra BaseVoltage bv_3",
        "BaseVoltage bv_1.nominalVoltage (kV): expected '4.16', got '<no column>'",
        "BaseVoltage bv_1.nominalVoltage (V): expected '<no column>', got '4160'",
    ]

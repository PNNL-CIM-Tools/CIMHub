"""Every schema slot has the type of the OpenDSS property it reads, as the engine's own property schema gives it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from dss import DSS

from cimhub_opendss.dss_name_map import get_class_map
from cimhub_opendss.schema import opendss_schema as schema

SCHEMA_DIR = Path(schema.__file__).parent / "linkml"

#: engine property type -> (the slot ranges that read it, multivalued, dss_format: matrix); "enum" is any enum
#: in common_enums.yaml. Complex values are written as [real imag] arrays. Not listed: DeprecatedAn, which the
#: engine reads and ignores, so there is no type to match.
ENGINE_TYPES = {
    "Double": (("float",), False, False),
    "DoubleOnArray": (("float",), False, False),  # LineGeometry x/h of the active cond=
    "DoubleOnStructArray": (("float",), False, False),  # the active wdg='s value
    "Integer": (("integer",), False, False),
    "IntegerOnStructArray": (("integer",), False, False),
    "Boolean": (("boolean",), False, False),
    "Enabled": (("boolean",), False, False),
    "BooleanAction": (("boolean",), False, False),
    "String": (("string",), False, False),
    "DSSObjectReference": (("string",), False, False),
    "Bus": (("string",), False, False),
    "BusOnStructArray": (("string",), False, False),
    "MakeLike": (("string",), False, False),
    "StringEnumAction": (("string",), False, False),
    "StringSilentROFunction": (("string",), False, False),
    "MappedStringEnum": (("enum", "string"), False, False),
    "MappedStringEnumOnStructArray": (("enum", "string"), False, False),
    "MappedIntEnum": (("enum", "integer"), False, False),  # an integer code: the enum's dss_value, or the number
    "MappedStringEnumArray": (("enum", "string"), True, False),
    "MappedStringEnumArrayOnStructArray": (("enum", "string"), True, False),
    "StringList": (("string",), True, False),
    "DSSObjectReferenceArray": (("string",), True, False),
    "BusesOnStructArray": (("string",), True, False),
    "IntegerArray": (("integer",), True, False),
    "DoubleArray": (("float",), True, False),
    "DoubleVArray": (("float",), True, False),
    "DoubleDArray": (("float",), True, False),
    "DoubleFArray": (("float",), True, False),
    "DoubleArrayOnStructArray": (("float",), True, False),
    "Complex": (("float",), True, False),
    "ComplexParts": (("float",), True, False),
    "DoubleSymMatrix": (("float",), True, True),
    "ComplexPartSymMatrix": (("float",), True, True),
}
UNTYPED = {"DeprecatedAn"}

#: schema classes with no engine class in DSS C-API
NOT_IN_ENGINE = {
    "Buscoords": "a bus-coordinate file, not a DSS class",
    "Options": "the deck's Set options, checked by test_dss_options_match_the_engine",
    "Fmonitor": "an OpenDSS (EPRI) class DSS C-API does not have",
    "Generic5": "an OpenDSS (EPRI) class DSS C-API does not have",
    "Pycontrol": "a Python control, not a DSS class",
    "Windgen": "an OpenDSS (EPRI) class DSS C-API does not have",
}

#: "Class.slot" that deliberately differs from the engine's type
ALLOWED = {
    "Transformer.RdcOhms": "the reader collects each wdg='s RdcOhms into one per-winding array (no DSS array form)",
    "Xfmrcode.RdcOhms": "the reader collects each wdg='s RdcOhms into one per-winding array (no DSS array form)",
}


@pytest.fixture(scope="module")
def engine_classes() -> dict[str, dict]:
    api = DSS._api_util
    text = api.ffi.string(api.lib_unpatched.DSS_ExtractSchema(api.ctx, 0)).decode()
    return {_key(cls["name"]): cls for cls in json.loads(text)["classes"]}


def _key(class_name: str) -> str:
    return class_name.lower().replace("_", "")  # TCC_Curve is TccCurve


def _schema_classes() -> dict[str, dict]:
    classes = {}
    for path in sorted(SCHEMA_DIR.rglob("*.yaml")):
        classes.update(yaml.safe_load(path.read_text()).get("classes") or {})
    return classes


def _slot_type(attribute: dict, enums: set[str]) -> tuple[str, bool, bool]:
    """``(range, multivalued, matrix)`` of a YAML attribute; any enum range is ``"enum"``."""
    range_ = attribute.get("range", "string")
    return ("enum" if range_ in enums else range_, bool(attribute.get("multivalued")),
            (attribute.get("annotations") or {}).get("dss_format") == "matrix")


def _describe(range_: str, multivalued: bool, matrix: bool) -> str:
    return range_ + ("[]" if multivalued else "") + (" matrix" if matrix else "")


def test_schema_types_match_the_engine(engine_classes):
    enums = set(yaml.safe_load((SCHEMA_DIR / "common_enums.yaml").read_text())["enums"])
    classes = _schema_classes()
    assert {name for name in classes if _key(name) not in engine_classes} == set(NOT_IN_ENGINE)
    mismatches = {}
    for class_name, definition in classes.items():
        if class_name in NOT_IN_ENGINE:
            continue
        param_to_field = get_class_map(getattr(schema, class_name)).param_to_field
        attributes = definition["attributes"]
        for prop in engine_classes[_key(class_name)]["properties"]:
            slot = param_to_field.get(prop["name"].lower()) or param_to_field.get(prop["altName"].lower())
            if slot is None or prop["type"] in UNTYPED:
                continue
            ranges, multivalued, matrix = ENGINE_TYPES[prop["type"]]
            range_, slot_multivalued, slot_matrix = _slot_type(attributes[slot], enums)
            if range_ not in ranges or (slot_multivalued, slot_matrix) != (multivalued, matrix):
                mismatches[f"{class_name}.{slot}"] = (f"engine {prop['type']} wants "
                                                      f"{_describe('|'.join(ranges), multivalued, matrix)}, "
                                                      f"slot is {_describe(range_, slot_multivalued, slot_matrix)}")
    assert {slot: why for slot, why in mismatches.items() if slot not in ALLOWED} == {}
    assert set(ALLOWED) <= set(mismatches), "an allowed difference is gone; drop it from ALLOWED"

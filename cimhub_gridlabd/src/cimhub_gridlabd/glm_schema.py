"""What the GLM LinkML schema says about each class: its GLM type name, its slots' GLM property names, declared
units and ``glm_default`` values, inherited slots included.

The YAML keys classes by their GLM type name (``node``, ``triplex_meter``) and the generated dataclasses by
PascalCase (``Node``), so the core annotation lookup, which matches ``__name__``, finds nothing here. This index
matches each dataclass by its ``class_name`` and walks ``is_a``, so an inherited slot (``nominal_voltage`` on a
``triplex_node``, from ``node``) carries its annotations.
"""

from __future__ import annotations

import dataclasses
import functools
import re
from pathlib import Path
from typing import NamedTuple

import yaml

from cimhub_gridlabd.schema import gridlabd

_LINKML = Path(__file__).parent / "schema" / "linkml"
#: The unit suffix the scrape left on some native names (``primary_voltage[V]``); the unit is in ``unit``.
_UNIT_SUFFIX = re.compile(r"\[[^\]]*\]$")


class SlotInfo(NamedTuple):
    native_name: str
    """The property name in a ``.glm`` (``from`` for the slot ``from_node``)."""
    unit: str | None
    """The declared unit (``unit.ucum_code``): the unit GridLAB-D stores the property in."""
    default: object | None
    """The ``glm_default`` annotation, as written in the YAML (``float(0.0001)``), or ``None``."""


@functools.cache
def _yaml_classes() -> dict[str, dict]:
    classes: dict[str, dict] = {}
    for path in sorted(_LINKML.rglob("*.yaml")):
        for name, definition in (yaml.safe_load(path.read_text()).get("classes") or {}).items():
            if name in classes:
                raise ValueError(f"GLM schema class {name!r} is defined twice (second in {path})")
            classes[name] = definition or {}
    return classes


@functools.cache
def class_registry() -> dict[str, type]:
    """GLM type name (``overhead_line``) -> dataclass, for every object class (``glm_object`` subclasses)."""
    registry = {}
    for value in vars(gridlabd).values():
        if isinstance(value, type) and issubclass(value, gridlabd.GlmObject) and value is not gridlabd.GlmObject:
            registry[value.class_name] = value
    return registry


@functools.cache
def slots(native_cls: type) -> dict[str, SlotInfo]:
    """``{slot: SlotInfo}`` for every dataclass field of ``native_cls``, from its class and its ancestors."""
    classes = _yaml_classes()
    attributes: dict[str, dict] = {}
    name = native_cls.class_name
    while name is not None:
        for slot, spec in (classes[name].get("attributes") or {}).items():
            attributes.setdefault(slot, spec or {})
        name = classes[name].get("is_a")
    info = {}
    for field in dataclasses.fields(native_cls):
        spec = attributes[field.name]
        annotations = spec.get("annotations") or {}
        unit = (spec.get("unit") or {}).get("ucum_code")
        native_name = _UNIT_SUFFIX.sub("", str(annotations.get("native_name", field.name))).strip()
        info[field.name] = SlotInfo(native_name, unit,
                                    annotations.get("glm_default"))
    return info


@functools.cache
def slot_for_property(native_cls: type) -> dict[str, str]:
    """GLM property name -> slot (``from`` -> ``from_node``)."""
    return {info.native_name: slot for slot, info in slots(native_cls).items()}


#: GridLAB-D unit names (its ``unitfile.txt``) that the CIM unit registry spells differently. Only the spelling
#: changes: the number stays as written (I2).
_REGISTRY_SPELLING = {"Ohm": "ohm", "Ohm/mile": "ohm/mile"}


def registry_unit(unit: str | None) -> str | None:
    """A GridLAB-D unit as a ``.cimtbl`` header unit: ``Ohm/mile`` is ``ohm/mile``; others are the same."""
    return _REGISTRY_SPELLING.get(unit, unit)

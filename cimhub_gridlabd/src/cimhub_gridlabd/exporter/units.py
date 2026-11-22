"""The unit the exporter asks a getter for: the GLM slot's own (decision X8).

GridLAB-D stores each property in one fixed unit (ft, ohm/mile, V, kVA, ...), which the schema declares
(``unit.ucum_code``). The exporter reads every value in that unit, so the deck carries numbers only and no spoke code
converts a unit.
"""

from __future__ import annotations

from cimprofiles.units import units

from cimhub_gridlabd import glm_schema


def glm_unit(native_class: type, slot: str) -> str:
    """The pint unit of ``native_class.slot`` (``Ohm/mile`` -> ``ohm/mile``); a slot with no declared unit raises."""
    unit = glm_schema.registry_unit(glm_schema.slots(native_class)[slot].unit)
    if unit is None:
        raise ValueError(f"GLM {native_class.class_name}.{slot} declares no unit")
    return unit


def from_percent(value: float | None, native_class: type, slot: str) -> float | None:
    """A percent number (``get_qty(..., 'percent')``, CIM's PerCent) in the GLM slot's unit, a fraction."""
    if value is None:
        return None
    return units.Quantity(value, "percent").to(glm_unit(native_class, slot)).magnitude

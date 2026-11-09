"""Compare two GDM systems field by field (EXPORT_PLAN.md §4, the GDM-level check).

Top-level components are matched by class and name. Each field is compared unless the importer's ``FIELDS`` marks it
``untranscribed`` (CIM never held it), or it is the uuid. An inline component is compared field by field; any other
referenced component by name. Quantities are compared in the original's unit at rel 1e-9.
"""

from __future__ import annotations

import numpy as np
from infrasys import Component
from pint import Quantity

from cimhub_gdm.importer.gdm_to_cim import INLINE, ORDER, SHELL
from cimhub_gdm.importer.shared import components

IMPORT_FIELDS = {**SHELL, **{cls: fields for cls, _, fields in ORDER}, **INLINE}
TOP_LEVEL = (*SHELL, *dict.fromkeys(cls for cls, _, _ in ORDER))
REL_TOL = 1e-9


def gdm_differences(original, exported) -> list[str]:
    """``'<class> <name>.<field>: <original> -> <exported>'`` for every difference, sorted."""
    found: list[str] = []
    for cls in TOP_LEVEL:
        before = {component.name: component for component in components(original, cls)}
        after = {component.name: component for component in components(exported, cls)}
        for name in sorted(before.keys() | after.keys()):
            label = f"{cls.__name__} {name}"
            if name not in after:
                found.append(f"{label}: not exported")
            elif name not in before:
                found.append(f"{label}: only in the export")
            else:
                _compare(before[name], after[name], label, found)
    return sorted(found)


def _compare(before, after, path: str, found: list[str]) -> None:
    if type(before) is not type(after):
        found.append(f"{path}: {type(before).__name__} -> {type(after).__name__}")
        return
    for field, spec in IMPORT_FIELDS[type(before)].items():
        if field != "uuid" and spec.kind != "untranscribed":
            _compare_value(getattr(before, field), getattr(after, field), f"{path}.{field}", found)


def _compare_value(before, after, path: str, found: list[str]) -> None:
    if isinstance(before, list | tuple) and isinstance(after, list | tuple) and len(before) == len(after):
        for index, (item_before, item_after) in enumerate(zip(before, after)):
            _compare_value(item_before, item_after, f"{path}[{index}]", found)
    elif isinstance(before, Component) and type(before) in INLINE:
        _compare(before, after, path, found)
    elif isinstance(before, Component):
        if not isinstance(after, Component) or before.name != after.name:
            found.append(f"{path}: {_text(before)} -> {_text(after)}")
    elif isinstance(before, Quantity):
        if not isinstance(after, Quantity) or not np.allclose(after.to(before.units).magnitude, before.magnitude,
                                                              rtol=REL_TOL, atol=0):
            found.append(f"{path}: {_text(before)} -> {_text(after)}")
    elif before != after:
        found.append(f"{path}: {_text(before)} -> {_text(after)}")


def _text(value) -> str:
    if isinstance(value, Component):
        return value.name
    if isinstance(value, list):
        return "[" + ", ".join(_text(item) for item in value) + "]"
    if isinstance(value, Quantity):
        return f"{value.magnitude:.6g} {value.units:~}"
    return str(getattr(value, "value", value))

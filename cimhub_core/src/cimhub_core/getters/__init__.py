"""Export getters: one function per CIM concept, plain floats in the caller's unit (skill `export-getters`)."""

from cimtables.graph_write import get_qty


def describe(obj) -> str:
    """``ClassName 'mRID'``, the subject of every getter error message."""
    return f"{type(obj).__name__} {obj.mRID!r}"


def required_qty(obj, attribute: str, unit: str) -> float:
    """``get_qty(obj, attribute, unit)``, raising when the attribute is unset."""
    value = get_qty(obj, attribute, unit)
    if value is None:
        raise ValueError(f"{describe(obj)}: {attribute} is unset")
    return value

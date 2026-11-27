"""Export getters: one function per CIM concept, plain floats in the caller's unit (skill `export-getters`)."""

from cimtables.graph_write import get_qty


def describe(obj) -> str:
    """``ClassName 'mRID'``, the subject of every getter error message. A state variable (``Sv*``) is not an
    IdentifiedObject and has no mRID: it is named by its ``uri()``."""
    identity = obj.mRID if hasattr(obj, "mRID") else obj.uri()
    return f"{type(obj).__name__} {identity!r}"


def required_qty(obj, attribute: str, unit: str, **bases) -> float:
    """``get_qty(obj, attribute, unit, **bases)``, raising when the attribute is unset."""
    value = get_qty(obj, attribute, unit, **bases)
    if value is None:
        raise ValueError(f"{describe(obj)}: {attribute} is unset")
    return value

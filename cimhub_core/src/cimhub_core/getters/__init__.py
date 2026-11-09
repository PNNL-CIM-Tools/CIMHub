"""Export getters: one function per CIM concept, plain floats in the caller's unit (skill `export-getters`)."""


def describe(obj) -> str:
    """``ClassName 'mRID'``, the subject of every getter error message."""
    return f"{type(obj).__name__} {obj.mRID!r}"

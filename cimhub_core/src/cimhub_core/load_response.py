"""The shared ZIP load models: ``zip_fractions.cimtbl``, written by every distribution spoke (DSS-7).

Three fixed ``LoadResponseCharacteristic`` rows, constant power, impedance and current, with
``exponentModel=false``. A spoke's loads name them; a spoke writes its exponential models in its own load file.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE

ZIP_CONSTANT_PQ = "zip_constant_pq"
ZIP_CONSTANT_Z = "zip_constant_z"
ZIP_CONSTANT_I = "zip_constant_i"

#: ``(mRID, (power, current, impedance))``: the same fractions for p and q.
_FRACTIONS = (
    (ZIP_CONSTANT_PQ, ("1", "0", "0")),
    (ZIP_CONSTANT_Z, ("0", "0", "1")),
    (ZIP_CONSTANT_I, ("0", "1", "0")),
)

COLUMNS = ["mRID", "exponentModel", "pConstantPower", "pConstantCurrent", "pConstantImpedance",
           "qConstantPower", "qConstantCurrent", "qConstantImpedance"]


def zip_fractions() -> Document:
    """``zip_fractions.cimtbl``: the three constant ZIP models."""
    rows = [Row([load_response, "false", *fractions, *fractions]) for load_response, fractions in _FRACTIONS]
    table = Table("LoadResponseCharacteristic", [Column(name) for name in COLUMNS], rows)
    return Document(name="zip_fractions", statements=[table], profile=CIM_PROFILE,
                    comment="Constant power, impedance and current load models, shared by every distribution "
                            "spoke (cimhub_core.load_response).")

"""RAW Inter-area transfer: no artifact. cim18v17 has no scheduled-transfer class (CIM 18 gap), so each record is
listed verbatim on the ``ControlArea`` table comment of ``area_interchange.cimtbl`` (R5).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#inter-area-transfer``.
"""

from __future__ import annotations

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import Field, schema_defaults

NATIVE_CLASS = schema.InterareaTransferRecord

_LISTED = "listed on area_interchange.cimtbl's ControlArea comment (no scheduled-transfer class, CIM 18 gap)"
FIELDS = {
    "from_area": Field("untranscribed", note=f"ARFROM: {_LISTED}; with no area-interchange record raises"),
    "to_area": Field("untranscribed", note="ARTO: as ARFROM"),
    "transfer_id": Field("untranscribed", note="TRID: as ARFROM; blank: 1 (defaulted)"),
    "power_transfer": Field("untranscribed", note="PTRAN (MW, positive = ARFROM selling to ARTO): as ARFROM; blank: "
                                                  "0 (defaulted)"),
}


def transfer_lines(native, control_areas: set[int]) -> list[str]:
    """One ``ARFROM -> ARTO 'TRID' PTRAN MW`` entry per record, in file order, a blank TRID or PTRAN shown with its
    ``raw_default`` and listed as defaulted; an area with no area-interchange record raises.

    ``fill_defaults`` leaves untranscribed slots alone, so the listing fills its own."""
    defaults = schema_defaults(NATIVE_CLASS, "raw_default")
    lines = []
    for record in native.list_by_class(NATIVE_CLASS):
        values = {slot: getattr(record, slot) for slot in FIELDS}
        blank = [slot for slot, value in values.items() if value is None and slot in defaults]
        values.update({slot: defaults[slot] for slot in blank})
        for slot in ("from_area", "to_area"):
            if values[slot] not in control_areas:
                raise ValueError(f"inter-area transfer {values['from_area']} -> {values['to_area']} "
                                 f"'{values['transfer_id']}': {slot} {values[slot]} has no area-interchange record")
        line = (f"{values['from_area']} -> {values['to_area']} '{values['transfer_id']}' "
                f"{float(values['power_transfer'])!r} MW")
        lines.append(f"{line} (defaulted: {', '.join(blank)})" if blank else line)
    return lines

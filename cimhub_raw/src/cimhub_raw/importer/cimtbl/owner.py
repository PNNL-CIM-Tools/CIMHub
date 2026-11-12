"""RAW Owner: no artifact. Ownership is an asset-management concept in CIM (CIM 18 gap), so the Owner table and
every owner field on other records are untranscribed; the master counts the owners.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#owner``.
"""

from __future__ import annotations

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import Field

NATIVE_CLASS = schema.OwnerRecord

FIELDS = {
    "owner_number": Field("untranscribed", note="ownership is an asset concept (CIM 18 gap); no owner.cimtbl is "
                                                "written"),
    "owner_name": Field("untranscribed", note="as I"),
}

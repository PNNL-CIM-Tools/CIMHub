# cimhub_raw

PSS/E RAW v34 ↔ CIM (cim18v17) converter for CIMHub. RAW records map to `.cimtbl` text, and cimtables builds the
CIM from it. Plan: `.development/RAW_REWRITE_PLAN.md`; mapping spec: `docs/CIMTBL_MAPPING.md`.

```python
from cimhub_raw.raw34_reader import Raw34Reader

model = Raw34Reader("case.raw").read_all()   # GraphModel of RAW v34 records
```

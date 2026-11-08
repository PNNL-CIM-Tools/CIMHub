# cimhub_opendss

OpenDSS converter for CIMHub. `DssReader` parses a deck into native LinkML dataclasses, `DssImporter` maps them to
`.cimtbl` artifacts (one per DSS class), and cimtables builds the cim18v17 model from those artifacts.

```python
from cimhub_opendss import DssReader, dss_to_cim

network = dss_to_cim(DssReader("Master.dss").read_all(), artifact_dir="out")
```

The mapping spec is [`docs/CIMTBL_MAPPING.md`](docs/CIMTBL_MAPPING.md).

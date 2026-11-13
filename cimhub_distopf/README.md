# cimhub_distopf

CIMHub converter for [DistOPF](https://pypi.org/project/distopf/) CSV cases (`bus_data.csv`, `branch_data.csv`,
`gen_data.csv`, `cap_data.csv`, `bat_data.csv`, `reg_data.csv`, `schedules.csv`).

Status: wave started. The LinkML schema, `DistopfReader` and `DistopfWriter` are seeded; the `.cimtbl` importer
waits for the approved mapping spec, [docs/CIMTBL_MAPPING.md](docs/CIMTBL_MAPPING.md).

```python
from cimhub_distopf import DistopfReader, DistopfWriter

model = DistopfReader("path/to/case").read_all()
DistopfWriter().write(model, "out_dir")
```

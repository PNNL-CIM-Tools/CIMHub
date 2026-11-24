# cimhub-raw

PSS/E RAW v34 importer for CIMHub: RAW cases to CIM (cim18v17). `Raw34Reader` parses a case into native records.
`RawImporter` maps them to `.cimtbl` text (one file per RAW table, values copied verbatim in the case's units),
and cimtables builds the CIM model from that text. `Raw34Writer` writes native records back to a `.raw` file.
There is no CIM to RAW exporter yet.

```bash
pip install --pre cimhub-raw      # also installs cimhub-core
```

Python 3.11 or later. Version 2.1 is in alpha.

## Quickstart

```python
import cimprofiles.cim18.cim18v17 as cim

from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.raw34_writer import Raw34Writer

# IEEE_14_bus.raw: cimhub_raw/tests/cases/IEEE14/ in the repository
model = Raw34Reader("IEEE_14_bus.raw").read_all()
network = raw_to_cim(model, name="IEEE14", artifact_dir="ieee14_cimtbl")
print(len(network.graph[cim.TopologicalNode]), "buses")   # 14 buses
Raw34Writer().write(model, "ieee14_copy.raw")
```

`raw_to_cim(model, *, name, authority=..., network=None, artifact_dir=None)` returns the CIM network. Without
`artifact_dir` the `.cimtbl` files go to a temporary directory. `name` is the model name and the master file stem.

## What is supported

| RAW data | Import |
|---|---|
| Case identification, system-wide data, zones, areas, interarea transfers, owners | yes (owners are untranscribed: CIM has no home for them) |
| Buses, substations and node-breaker data (nodes, switching devices, equipment terminals) | yes |
| Branches, system switching devices, multi-section lines | yes |
| Loads, fixed shunts, switched shunts | yes |
| Generators (including renewable models and implicit step-up transformers) | yes |
| Two- and three-winding transformers, phase shifters, impedance correction tables | yes |
| Two-terminal DC lines, VSC DC lines, FACTS devices | yes |
| Multi-terminal DC lines, GNE devices, induction machines | raise `NotImplementedError` when the case has any |

`Raw34Writer` raises for a section of those phase-2 record types. Blank or missing fields take the schema's default
and are listed on the row comment (`# defaulted: ...`).

The repository carries three public cases: IEEE 14 bus, IEEE 118 bus (with four node-breaker substations) and the
WECC 240 bus case. Other cases are not distributed.

## Documentation

- [RAW v34 to `.cimtbl` mapping spec](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_raw/docs/CIMTBL_MAPPING.md)
- [CIMHub architecture](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/developer/architecture.md) and [converter API](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/developer/converter-api.md)

BSD 3-Clause. Source and issues: <https://github.com/PNNL-CIM-Tools/CIMHub>.

## License and attribution

BSD 3-Clause. See [LICENSE](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_raw/LICENSE). Contributors are listed in [AUTHORS](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/AUTHORS).

This software was created under a project sponsored by the U.S. Department of Energy's Office of Electricity, an
agency of the United States Government. Neither the United States Government nor the United States Department of
Energy, nor Battelle, nor any of their employees, nor any jurisdiction or organization that has cooperated in the
development of these materials, makes any warranty, express or implied, or assumes any legal liability or
responsibility for the accuracy, completeness, or usefulness or any information, apparatus, product, software, or
process disclosed, or represents that its use would not infringe privately owned rights.

PACIFIC NORTHWEST NATIONAL LABORATORY\
operated by BATTELLE\
for the UNITED STATES DEPARTMENT OF ENERGY\
under Contract DE-AC05-76RL01830

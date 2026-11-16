# cimhub-core

The shared layer of CIMHub, which converts power-system model formats to and from CIM (cim18v17 only). Core holds
only what the format packages share and no upstream library provides: the `.cimtbl` import contract
(`CimtblImporter`), the abstract reader, writer, importer and exporter classes, a typed store for native records
(`GraphModel`), the export getters (`cimhub_core.getters`), canonical `.cimtbl` table shapes
(`cimhub_core/shapes/`), derived-value helpers (`cimhub_core.derived`) and a test harness
(`cimhub_core.cimtbl_testing`). You install it as a dependency of a format package; install it directly to write
a new one.

```bash
pip install cimhub-core
```

Python 3.11 or later.

## Quickstart

Getters read one CIM concept and return plain floats in the unit you ask for. This example imports an OpenDSS deck
(needs `cimhub-opendss`) and reads a load's power in kW and kVAr.

```python
import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters.load import get_phase_loads
from cimhub_opendss import DssReader, dss_to_cim

deck = "IEEE13Nodeckt.dss"   # copy the files in cimhub_opendss/tests/decks/IEEE/IEEE13_original/ next to it
network = dss_to_cim(DssReader(deck).read_all(), name="IEEE13")
consumer = next(iter(network.graph[cim.EnergyConsumer].values()))
print(consumer.name, get_phase_loads(consumer, "kW", "kVAr").total)   # 611 PhasePower(p=170.0, q=80.0)
```

## What core provides

| Module | Purpose |
|---|---|
| `cimhub_core.base` | `FormatReader`, `FormatWriter`, `FormatImporter`, `CimtblImporter`, `FormatExporter` |
| `cimhub_core.graph_model` | `GraphModel`: indexed store for native LinkML dataclasses |
| `cimhub_core.cimtbl` | mapper helpers: `Field`, `fill_defaults`, `check_fields`, `fields_table`, `cimtbl_to_cim` |
| `cimhub_core.getters` | one getter per CIM concept (terminals, load, switch state, line impedance, tap changer, ...) |
| `cimhub_core.names` | export naming: `name`, `mrid` or `uri`, chosen by argument or `CIMHUB_NAME_SOURCE` |
| `cimhub_core.cimtbl_testing` | `cim_scope`, `assert_matches_golden`; `CIMHUB_UPDATE_GOLDENS=1` regenerates goldens |
| `cimhub_core.scaffold` | `scaffold_package`: generate a new format package |
| `cimhub_core.time_points` | the Parquet sidecar of nc_schedule time points beside the CIM XML (`write_time_points`, `read_time_points`, `rows_by_schedule`); install `cimhub-core[time-points]` |

Topology (spanning trees, islands, voltage zones) comes from `cimtopology`, not from core.

## Documentation

- [Architecture](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/ARCHITECTURE.md)
- [Converter API](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/CONVERTER_API.md)
- [Units](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/UNITS.md)
- [Testing](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/TESTING.md)
- [Repository README](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/README.md)

BSD 3-Clause. Source and issues: <https://github.com/PNNL-CIM-Tools/CIMHub>.

## License and attribution

BSD 3-Clause. See [LICENSE](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/LICENSE). Contributors are listed in [AUTHORS](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/AUTHORS).

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

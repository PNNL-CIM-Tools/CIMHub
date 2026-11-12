# cimhub-gdm

grid-data-models (GDM) converter for CIMHub: a GDM `DistributionSystem` to and from CIM (cim18v17).

GDM has no file format of its own. Its native model is typed pydantic objects with pint quantities. So this package
is **builder-native**: `GdmImporter().to_cim(system)` calls CIM-Builder's keyword methods directly and writes no
`.cimtbl` file. The tests compare the result with reviewed `.cimtbl` goldens. The exporter reads every value
through the `cimhub-core` getters.

```bash
pip install cimhub-gdm      # also installs cimhub-core
```

Python 3.11 or later.

## Quickstart

```python
from cimhub_gdm import gdm_to_cim, read_gdm

system = read_gdm("system.json")             # a GDM DistributionSystem saved as JSON
system.name = system.name or "my_feeder"     # the CIM Model name; a system saved without one has none
network = gdm_to_cim(system)
```

## Time series

Load time series map onto nc_schedule `EnergyConnectionSchedule`s when you pass a `time_points` dict. The schedules go
in the CIM XML; their points go in Parquet beside it, one row per point keyed by the schedule's uri, never as graph
objects. See [`docs/TIMESERIES_NEEDS.md`](docs/TIMESERIES_NEEDS.md).

```python
from cimgraph.utils import write_xml
from cimhub_gdm import GdmExporter, gdm_to_cim, read_time_points, write_time_points

time_points = {}  # filled: {"EnergyConnectionTimePoint": pyarrow.Table}
feeder_model = gdm_to_cim(system, time_points=time_points)
write_xml(feeder_model, "feeder.xml")
write_time_points(time_points, "feeder.xml")

time_points = read_time_points("feeder.xml", reloaded_model)
system = GdmExporter(time_points).to_model(reloaded_model)
```

Export goes the other way:

| Function | Purpose |
|---|---|
| `GdmExporter().to_model(network, *, name_source=None, system_name=None)` | returns a GDM `DistributionSystem` |
| `cim_to_gdm(network, destination, **opts)` | the same, written as GDM JSON |
| `read_gdm(path)`, `write_gdm(system, path)` | GDM JSON in and out |

`name_source` is `'name'`, `'mrid'` or `'uri'` (default `$CIMHUB_NAME_SOURCE`, else `'mrid'`). `system_name` names the
system; without it the model's one Feeder names it, and a model with several Feeders raises.

## What is supported

| Family | Import | Export |
|---|---|---|
| Network shell (feeders, substations) and buses | yes | yes |
| Voltage sources | yes | yes |
| Switches, fuses, reclosers | yes | yes |
| Lines: matrix, sequence and geometry impedance, with wire and cable catalogs | yes | yes (bare and concentric-neutral wire) |
| Loads | yes | yes |
| Capacitors and their controllers | yes | yes |
| Transformers (tank-configuration templates, center taps, off-nominal taps) | yes | yes |
| Regulators, tap changers and controls | yes | yes |
| Solar and battery DER with inverter and battery data | yes | yes (one GDM DER per unit of a hybrid inverter) |
| Series reactors | yes | yes |

What raises or is dropped:

- Import: inverter controllers, the daily-timed capacitor controller and earthing switches raise as pending, naming
  what they wait for. Other time series, and load time series imported without a `time_points` dict, are dropped with
  one warning. GDM fields with no cim18v17 home are untranscribed (logged at `DEBUG`); the list is in
  [GDM_MAPPING.md](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gdm/docs/GDM_MAPPING.md) section 10.
- Export: a tape-shield cable raises, because GDM has no class for one. Exporting a model that `gdm_to_cim` built can
  raise on its current limits, because CIM-Builder's `add_limit_type` has no `durationKind` yet (see
  [GDM_MAPPING.md](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gdm/docs/GDM_MAPPING.md) section 14, item B22 b).
- The exported system writes and solves through ditto's OpenDSS writer, which has no battery writer.

The import needs CIM-Builder's `add_transformer_tank_end` method, `SeriesCompensatorBuilder` and
`EnergyConnectionScheduleBuilder`. The output survives a cim18v17 XML round trip unchanged.

## Documentation

- [GDM to CIM mapping spec](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gdm/docs/GDM_MAPPING.md)
- [CIM to GDM export spec](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gdm/docs/EXPORT_MAPPING.md)
- [Tap assumptions both directions make](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gdm/docs/TAP_ASSUMPTIONS.md)
- [Rewrite plan](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gdm/docs/GDM_REWRITE_PLAN.md) and [export plan](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gdm/docs/EXPORT_PLAN.md)
- [CIMHub architecture](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/ARCHITECTURE.md) and [converter API](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/CONVERTER_API.md)

BSD 3-Clause. Source and issues: <https://github.com/PNNL-CIM-Tools/CIMHub>.

## License and attribution

BSD 3-Clause. See [LICENSE](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gdm/LICENSE). Contributors are listed in [AUTHORS](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/AUTHORS).

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

# Time series and schedules

A CIM schedule can have thousands of points, and CIM XML would give each point its own object. CIMHub keeps the
schedule objects in the CIM XML and puts their points in Parquet files beside it, one row per point. The module is
`cimhub_core.time_points`, and it needs the `time-points` extra ([Installation](installation.md)).

```text
ieee13.xml                                  the schedules
ieee13.RegularTimePoint.parquet             points of RegularIntervalSchedules (load groups)
ieee13.EnergyConnectionTimePoint.parquet    points of EnergyConnectionSchedules (one device each)
```

The first column of every table is the owning schedule's `uri()`, so a row finds its schedule in the network read from
the XML.

## The two tables

`TIME_POINT_TABLES` maps a class name to a `TimePointTable` NamedTuple with three fields: the pyarrow `schema`, the
`schedule_class` the first column points at (subclasses included), and the `position` column that orders a schedule's
points.

| Table | For | Columns after the schedule | Position |
|---|---|---|---|
| `EnergyConnectionTimePoint` | an `EnergyConnectionSchedule`: one device's series | `atTime`, `p`, `q` (SI, W and VAr) | `atTime` |
| `RegularTimePoint` | a `RegularIntervalSchedule`, a `ConformLoadSchedule` or `NonConformLoadSchedule` included | `sequenceNumber`, `value1`, `value2`, `value3` | `sequenceNumber` |

A regular point's time is the schedule's `startTime` + `sequenceNumber` × `timeStep`, so the first point is number 0.
Its values are in the schedule's `value1Unit`, `value2Unit` and `value3Unit`. A `ConformLoadSchedule` has
`value1Unit` `none`, so its `value1` is a multiplier of each load's own `p` and `q` in CIMHub's load-schedule shape; a
`NonConformLoadSchedule` is in the units its `value1Unit` names.

## The model for the examples

The page uses [`feeder.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/docs/guide/feeder.cimtbl)
from the [quick start](quickstart.ipynb). Its load `ld_c1` is a `ConformLoad` in the group `lg_daily`, whose
`ConformLoadSchedule` `ls_daily` starts at midnight and steps one hour. The file holds the schedule and no points.

```python
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import cimtables
from cimbuilder.object_builder.schedule import EnergyConnectionScheduleBuilder
from cimgraph.utils import write_xml

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.time_points import (add_device_time_points, add_regular_time_points, read_time_points,
                                     rows_by_schedule, time_points_path, write_time_points)

with cim_scope():
    network = cimtables.load_model('feeder.cimtbl')


def find(cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)
```

## Build the tables

A table is a dict `{class name: pyarrow table}`. The `add_*` functions put one table into a dict you own, keyed by
the schedule's mRID in the network and stored by its uri.

### Regular points

`add_regular_time_points(time_points, network, values, value2=None)` takes `{schedule mRID: [value1 per point]}`,
numbers the points from 0 and adds the `RegularTimePoint` table.

```python
time_points = {}
add_regular_time_points(time_points, network, {'ls_daily': [0.4, 0.35, 0.3, 0.5]})
```

`value2` gives the second value of the schedules it names. A `value2` list of another length than its `value1`
raises, and so does an mRID, in `values` or in `value2`, that no `RegularIntervalSchedule` of the network has (a
`value2` mRID that has no `value1` raises too). Adding a second `RegularTimePoint` table to the same dict raises as well.

`regular_time_points(values, value2=None)` is the pure core: the same, keyed by uri, with no network.

### Device points

`add_device_time_points(time_points, network, points)` takes `{schedule mRID: (times, p, q)}`. Times are when each
point takes effect, `p` is in kW and `q` in kVAr in the load sign, and `None` is a column the schedule does not
carry. The function calls CIM-Builder's `EnergyConnectionScheduleBuilder.time_points`, which stores SI. The schedule
has to exist in the network already, so create it as a spoke does:

```python
builder = EnergyConnectionScheduleBuilder(network=network, container=network.container)
schedule = builder.create(mRID='pv_p1_pq', name='p1')
builder.add_schedule(schedule, EnergyConnection='pv_p1', timeSeriesKind='actual')

hours = [datetime(2020, 1, 1) + timedelta(hours=hour) for hour in range(3)]
add_device_time_points(time_points, network, {'pv_p1_pq': (hours, [-100.0, -200.0, -150.0], None)})
print(sorted(time_points))    # ['EnergyConnectionTimePoint', 'RegularTimePoint']
```

## Write and read

`write_time_points(time_points, xml_path)` writes each table next to the XML path, replacing any there, and returns
the paths written. It checks each table against its class's schema first, and an unknown class name raises.
`time_points_path(xml_path, class_name)` is the file name rule: the XML's stem, the class name, `.parquet`.

```python
xml_path = Path(tempfile.mkdtemp()) / 'guide_feeder.xml'
write_xml(network, xml_path)
for path in write_time_points(time_points, xml_path):
    print(path.name)    # guide_feeder.RegularTimePoint.parquet, then guide_feeder.EnergyConnectionTimePoint.parquet
```

`read_time_points(xml_path, network)` reads the tables that exist beside the XML and returns them as the same dict.
A class with no file has no entry. It checks what it reads against the network, and raises on:

| Problem | Message begins |
|---|---|
| a table off its schema | `<class> table schema is not its TimePoint schema` |
| rows for a schedule that is not in the network | `<file>: rows for N schedule(s) not in the XML` |
| two points of one schedule at one position | `<file>: N repeated (schedule, <position>) pairs` |

A schedule with no rows does not raise. It gets one `WARNING` from the `cimhub_core.time_points` logger that names the
schedules.

```python
read = read_time_points(xml_path, network)
print({name: table.num_rows for name, table in read.items()})
# {'EnergyConnectionTimePoint': 3, 'RegularTimePoint': 4}
```

## Split by schedule

`rows_by_schedule(table)` splits a table into `{schedule uri: its rows}`, in the order the table has them. The getters
take that dict.

```python
regular = rows_by_schedule(read['RegularTimePoint'])
device = rows_by_schedule(read['EnergyConnectionTimePoint'])
```

## Read the schedules

### Load groups and their schedules

`get_load_schedule(consumer)` finds a load's group and its time series. It returns a `LoadSchedule` NamedTuple, or
`None` for a plain `EnergyConsumer` or a load with no group.

| Field | Holds |
|---|---|
| `conform` | `True` for a `ConformLoad` (a multiplier), `False` for a `NonConformLoad` |
| `group` | the `LoadGroup` |
| `schedule` | the one time series, or `None` when the group has only days, or only a name |
| `start` | the schedule's `startTime` as written, ISO 8601 with its offset |
| `step` | the schedule's `timeStep` in seconds |
| `days` | for a group built from `Season` or `DayType` schedules, those schedules, sorted by mRID |

A group holds one time series, or day schedules by season and day type. A mix raises.
`get_schedule_points(schedule, rows_by_schedule)` then reads the points as a `SchedulePoints` with a `value1` list
and a `value2` list (`None` when `value2` is unset at every point), or `None` when the schedule has no rows.

```python
from cimhub_core.getters.load_schedule import get_load_schedule, get_schedule_points

found = get_load_schedule(find(cim.ConformLoad, 'ld_c1'))
print(found.conform, found.group.name, found.start, found.step)   # True daily 2009-07-21T00:00:00-04:00 3600.0
print(get_schedule_points(found.schedule, regular))               # SchedulePoints(value1=[0.4, 0.35, 0.3, 0.5], value2=None)
```

The rows must be numbered 0, 1, 2, ... and stored in that order. Any other numbering or order, a `value1` that is unset at
some point, or a `value2` set at only some points raises.

`log_dropped_schedules(consumers, target)` is for an exporter whose target format has no schedules. It logs one
`WARNING` naming the groups it will not write.

### A device's schedule

`get_device_schedule(equipment, rows_by_schedule, p_unit, q_unit, *, sign)` reads the one
`EnergyConnectionSchedule` of a device that has points, and returns a `DeviceSchedule`, or `None` when the device has
none.

| Field | Holds |
|---|---|
| `schedule` | the `EnergyConnectionSchedule` |
| `times` | when each point takes effect, as UTC `datetime` |
| `step` | the one interval between points in seconds, or `None` when uneven or a single point |
| `p`, `q` | lists in your unit and sign, or `None` when the schedule has no such column |

```python
from cimhub_core.getters.device_schedule import get_device_schedule

pv = find(cim.PowerElectronicsConnection, 'pv_p1')
series = get_device_schedule(pv, device, 'kW', 'kVAr', sign='generation')
print(series.times[0], series.step, series.p, series.q)
# 2020-01-01 00:00:00+00:00 3600.0 [100.0, 200.0, 150.0] None
```

`sign=` is `'load'` or `'generation'`, as in [Units, bases and signs](units.md). The stored points are in the load sign,
so `'generation'` negates them. Two schedules with points on one device raise, as do an interpolation other than
`previous` (a sample holds until the next one), a `p` or `q` column that is null at some points only, and a schedule
with neither column.

`get_load_schedule` and `get_device_schedule` import no pyarrow themselves: they take the dict that `rows_by_schedule` returns. Both are in the [loads reference](../reference/loads.md), with the other getters of loads and schedules.

## Where to see it used

- [`test_time_points.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/tests/test_time_points.py) builds, writes and reads both tables, and checks each error above.
- [`cimhub_gridlabd/src/cimhub_gridlabd/exporter/schedule.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gridlabd/src/cimhub_gridlabd/exporter/schedule.py) turns load groups and their points into GridLAB-D schedules, taking `time_points` from the caller.

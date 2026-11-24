# Installation

```bash
pip install --pre cimhub-core
```

`cimhub-core` is imported as `cimhub_core`. It needs Python 3.11 or newer, and `--pre` is required for now: it is an
alpha release and depends on pre-release versions of [cim-graph](https://github.com/PNNL-CIM-Tools/CIM-Graph),
[cim-profiles](https://github.com/PNNL-CIM-Tools/CIM-Profiles),
[cim-tables](https://pnnl-cim-tools.github.io/CIM-Tables/) and cim-topology.

With [uv](https://docs.astral.sh/uv/):

```bash
uv add --prerelease allow cimhub-core
```

## The time-points extra

The getters need nothing beyond the base install. The Parquet files of schedule points
([Time series and schedules](time-points.md)) need two more packages, which the `time-points` extra adds:

| Package | Why |
|---|---|
| `cim-builder` | its `TIME_POINT_SCHEMA` and the schedule builder that `add_device_time_points` calls |
| `pyarrow` (18 or newer) | reading and writing the Parquet tables |

```bash
pip install --pre "cimhub-core[time-points]"
```

`import cimhub_core.time_points` raises `ModuleNotFoundError` without the extra. Nothing else in core imports
pyarrow.

## Check it works

```python
import cimtables
from cimhub_core.getters.terminals import get_terminal_phases

print(cimtables.__version__)
print(get_terminal_phases.__module__)
```

The CIM profile is `cim18v17`. Core supports no other.

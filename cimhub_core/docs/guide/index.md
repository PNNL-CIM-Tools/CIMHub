# User guide

This guide is for reading a CIM model from Python with the getters in `cimhub_core.getters`. The model can come
from CIM XML or from `.cimtbl`. To write a converter, start with the [developer docs](../developer/index.md).

<div class="grid cards" markdown>

-   __Getting started__

    ---

    [Installation](installation.md) and a [quick start](quickstart.ipynb) notebook that loads a small feeder and
    reads its line, transformer, loads and terminals.

-   __Reading CIM__

    ---

    [Using the getters](getters.md): units, NamedTuples, `None`, errors and the arguments that carry a decision.
    [Units, bases and signs](units.md) covers per-unit, percent and generator sign.

-   __Time series__

    ---

    [Time series and schedules](time-points.md): the Parquet files beside the CIM XML, and how load groups and
    device schedules are read.

-   __Getter reference__

    ---

    Every getter by concept: [lines](../reference/lines.md), [transformers](../reference/transformers.md),
    [loads](../reference/loads.md), [DER](../reference/der.md) and [topology](../reference/topology.md).

</div>

## The idea in four lines

- Load a model into cim-graph: `cimtables.load_model` for `.cimtbl`, or cim-graph's own reader for CIM XML.
- Pass the CIM object to a getter: `get_phase_loads(load, 'kW', 'kVAr')`.
- Name the unit. CIM holds SI; the getter converts once.
- Read the result by field name. A `None` means CIM leaves it unset; an exception means the model cannot be read as
  asked.

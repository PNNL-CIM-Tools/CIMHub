# Export: CIM to DSS

```python
from cimhub_opendss import DssExporter, DssWriter, cim_to_dss

cim_to_dss(network, "out/IEEE13_CDPSM.dss")                 # export and write in one call

model = DssExporter().to_model(network, name_source="name")  # records only, no files
DssWriter().write(model, "out/IEEE13_CDPSM.dss")
```

`network` is any cim18v17 network, for example the result of [`dss_to_cim`](import.md). The exporter reads it through
the [getters in `cimhub_core`](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/) and returns a `DssModel`,
the same shape `DssReader.read_all()` returns, so the deck the writer produces reads back through the reader and the
importer. Only `DssWriter` touches the filesystem.

## Options

`DssExporter(time_points=None).to_model(network, *, name_source=None, circuit_source="source",
switch_state="actual")`. `cim_to_dss(network, destination, *, per_class=False, time_points=None, **opts)` passes
`opts` to `to_model`.

| Argument | Meaning |
|---|---|
| `name_source` | What a DSS name comes from: `'name'`, `'mrid'` or `'uri'`. Without it, `$CIMHUB_NAME_SOURCE`, else `'mrid'`. Any other value raises. |
| `circuit_source` | Which `EnergySource` becomes `New Circuit` when the network has several. Matched, ignoring case, against the exported name. Default `"source"`. |
| `switch_state` | `'actual'` (default) writes each switch's `State` and `Open` command from `Switch.open`. `'normal'` reads `Switch.normalOpen`, for a model whose `open` is unset. `Normal` always reads `normalOpen`. Any other value raises. |
| `time_points` | The TimePoint tables of the network's schedules (see [time points](#load-shapes-and-time-points)). |
| `per_class` | `cim_to_dss` and `DssWriter.write` only. Write each DSS class to its own file beside the deck (`line.dss`, `load.dss`, ...), which the master `Redirect`s. |

## Names

Every DSS name is the CIM object's `name`, `mRID` or `uri()`, as `name_source` says, with each run of characters DSS
cannot parse (white space, quotes, `<>[]{}(),=~|`) replaced by `_`.

| `name_source` | Use it when |
|---|---|
| `'mrid'` (default) | the model came from `dss_to_cim`: the importer compiled each mRID from the DSS name, so names are unique |
| `'name'` | you want the names a person gave the objects. A model with duplicate names raises (below) |
| `'uri'` | names must be stable and of fixed length across tools. `mRID` is a free-form string in cim18v17, so it is not a safe join key; `uri()` is |

Rules:

- Two objects of one DSS class that end up with the same name, compared ignoring case as DSS does, raise:
  `ACLineSegment 'ln_b' and 'ln_a' are both named 'a' in DSS Line (name source 'name')`. Buses are one namespace of their own,
  and a `.` in a bus name becomes `_` because `.` is DSS's node delimiter.
- An object with no `name` (or `mRID`, or `uri()`) to export it under raises, naming its class and mRID.
- The circuit is named for the one `Feeder`. Several Feeders with equipment are one circuit when they share a
  `NormalEnergizingSubstation`, and the Substation names it. No Feeder, or several without one Substation, raises. A
  Feeder with no equipment is not counted when there are several.
- The circuit's source is always written as `Vsource.source`, whatever the naming, because that is DSS's name for
  `New Circuit`'s source.

## The circuit source

A deck has one `New Circuit`. With one `EnergySource` in the network it is the circuit's source. With several, the
one whose exported name matches `circuit_source` is, and the others become `Vsource` records:

```python
cim_to_dss(network, "out/feeder.dss", name_source="name", circuit_source="substation_a")
```

Several `EnergySource`s and no single match raises: `2 EnergySources and 0 exported as 'source' (name source 'name');
pass circuit_source= to name the circuit's`.

## What is written

The deck is written in this order: `Clear`, `Set defaultbasefreq`, `New Circuit`, `Set earthmodel` (when the
`WireConfiguration`s name one, or, in a model without line geometry, the network's one `EarthResistivity`), the records, `Set voltagebases` and `CalcVoltageBases`, one `Open` per open switch
terminal, then `Buscoords` or `LatLongCoords` naming the CSV files written beside the deck (`<stem>_buscoords.csv`,
`<stem>_latlongcoords.csv`). Records go catalogs first: `LoadShape`, the wire catalogs, `LineSpacing`, `LineGeometry`,
`LineCode`, `XfmrCode`, then the equipment, each class after what it references. The writer creates the destination's
folders.

Quantities are converted with `CIMUnit.to()` into the unit the DSS property expects. Line lengths and wire
dimensions are written in metres (a line with only lumped values is written per km, `units=km`).

Which CIM class becomes which DSS class, and where each slot comes from, is in the
[export mapping](../EXPORT_MAPPING.md). [What converts](coverage.md) lists the classes.

## Switches

A CIM switch is written as a `Line` with `Switch=y` and a small invented impedance (`r1=r0=0.001` ohm over `length=1` `units=m`), because CIM holds none. The
control depends on the class: a `Fuse` and a `Recloser` get their own control; any other switch class gets a
`SwtControl`, written only when the switch is open in either state (`normalOpen` or the state `switch_state` reads). The `Fuse` and
`Recloser` controls are written with `enabled=false`, because cim18v17 holds no trip settings or curve and the engine's defaults
would trip them. With `switch_state='actual'`, an open switch also gets an
`Open Line.<name> 1` line. A switch whose `open` is unset raises under `'actual'`, since there is no silent fallback; use
`switch_state='normal'` for an as-built model. A switch whose `normalOpen` is unset raises under both: `LoadBreakSwitch 'sw_671692': normalOpen is unset`.

## Bus coordinates

Each `Location` of the network's equipment gives its Terminals' buses their coordinates, as the import's inverse. A bus
no located equipment touches has none. Two different points for one bus raise, naming both pieces of equipment. The
`CoordinateSystem` picks the file: `urn:ogc:def:crs:OGC:1.3:CRS84` is written as `LatLongCoords` (latitude first, as
the engine reads it), and the importer's own `OpenDSSLocalBusCoordinates` as `BusCoords`. Another system, or two
systems in one model, raises.

## Load shapes and time points

A `ConformLoadSchedule` with points becomes a `LoadShape`, named for its group, and each load of the group names it as
`yearly`. The same holds for the `EnergyConnectionSchedule` of a PV, battery or machine. The points are not in the
network, so pass the tables the importer filled, or `read_time_points`:

```python
from pathlib import Path
from cimhub_opendss import DssExporter, DssReader, DssWriter, dss_to_cim

time_points = {}
model = DssReader("cimhub_opendss/tests/atoms/loadshape/loadshapes.dss").read_all()
network = dss_to_cim(model, name="loadshapes", time_points=time_points)

exported = DssExporter(time_points).to_model(network, name_source="name")
DssWriter().write(exported, "/tmp/loadshapes_out/loadshapes.dss")
print([line[:60] for line in Path("/tmp/loadshapes_out/loadshapes.dss").read_text().splitlines() if "Loadshape" in line])
```

This needs the [`time-points` extra](installation.md). A schedule with no points, a load group with no schedule, and a
`NonConformLoad` are written as static loads, and one warning names their groups. Shapes with the same name, interval
and multipliers are shared; another shape of that name with other points takes a suffix (`_2`, `_3`). `startTime` is
not written, because DSS has no date. An hourly `interval=1` comes back as `sinterval=3600`, which is the same
interval.

## What raises

| Cause | Message starts |
|---|---|
| Conducting equipment of a CIM class no exporter module handles | `no DSS export yet for {'<Class>': <count>}` |
| More than one `EnergySource` with none exported under `circuit_source` | `<n> EnergySources and 0 exported as 'source'` |
| Two objects on one DSS name | `<Class> '<mRID>' and '<mRID>' are both named '<name>' in DSS <namespace>` |
| An object with no `name`, `mRID` or `uri()` to export | `<Class> '<mRID>': has no <name_source> to export it under` |
| No Feeder, or several without one Substation | `the model has <n> Feeders with equipment ...; a DSS deck is one circuit` |
| A bad `name_source` or `switch_state` | `name source must be one of ...`, `switch_state must be one of ...` |
| A value a DSS property needs that the model does not hold | for example a `WireConfiguration` with no `WireSpacing`, a wire with neither `Rdc` nor `Rac`, or a switch with no state |
| Two earth models in one network | `WireConfigurations over earth models ...; a DSS deck has one earthmodel` |
| A `BaseVoltage` with no `nominalVoltage` | `a BaseVoltage has no nominalVoltage` |
| A `per_class` file that would overwrite the master | `the master <name> would be overwritten by the <Class> file` |

## What does not survive a round trip

Some DSS and CIM distinctions are lossy by design:

- Every switch class other than `Fuse` and `Recloser` comes back as a `LoadBreakSwitch`.
- A DSS protection setting with no home in cim18v17 is written as the engine's default. The export mapping marks each
  such slot `unset` or `rule`.
- A CIM `AutoTransformer` is written as a DSS `Transformer`.
- Settings the model does not hold come back as the engine's defaults: `Load.Vminpu` and `Vmaxpu`, the
  `Transformer.ppm_antifloat` setting and the deck's tap and capacitor states that an in-deck `Solve` moved.

[Round trip](roundtrip.md) shows how to see which of these a given deck hit.

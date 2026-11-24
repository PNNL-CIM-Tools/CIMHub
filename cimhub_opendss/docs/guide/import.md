# Import: DSS to CIM

```python
from cimhub_opendss import DssReader, dss_to_cim

model = DssReader("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss").read_all()
network = dss_to_cim(model, name="IEEE13_CDPSM", artifact_dir="artifacts/IEEE13_CDPSM")
```

`network` is a cim18v17 cim-graph model. `artifact_dir` keeps the `.cimtbl` text it was built from.

## What happens

1. `DssReader(path).read_all()` follows `Redirect`s and `~` continuation lines, evaluates RPN values, and returns a
   `DssModel` of typed records. `Edit`, dotted edits, `Open`/`Close` and batch edits are applied as the engine would.
2. `DssImporter(name).to_cimtbl(model)` walks the deck's topology once (with `cimtopology`), then runs one mapper per
   DSS class. Each mapper turns records into a `.cimtbl` document. It does not build CIM objects.
3. `dss_to_cim` writes the documents and cimtables binds them into a network. A last part, `buscoords.cimtbl`, is
   mapped from the bound network because it needs the equipment's terminals.

The `.cimtbl` text is the only input to CIM. If a value is wrong in the network, it is wrong in the text, and you can
read it there.

## Options

`dss_to_cim(model, *, name, authority=..., length_unit=None, device_geometry="point", network=None,
artifact_dir=None, time_points=None)`. `DssImporter` takes the same keywords except `network` and `artifact_dir`,
which go to its `to_cim` method.

| Argument | Meaning |
|---|---|
| `name` | Required. The master document's `Model` and file stem. |
| `artifact_dir` | Keep the `.cimtbl` files here. Without it they go to a temporary directory that is removed after loading. |
| `network` | An existing cim18v17 network to bind onto, to merge several decks. A bus the decks share by name must have the same base voltage in both, or binding raises. |
| `authority` | The master's `Authority`. Defaults to `https://github.com/PNNL-CIM-Tools/CIMHub`. |
| `length_unit` | The per-length unit (`'km'`, `'kft'`, ...) for a `LineCode` that has no units of its own and whose lines set none. It overrides the importer's magnitude check (see [lines](../reference/lines.md)). |
| `device_geometry` | `"point"` (default) places a two-terminal device, such as a switch or transformer, as a point midway between its buses; `"linestring"` draws it from bus to bus. Any other value raises when the importer is made. |
| `time_points` | A dict the importer fills with the points of the deck's yearly `LoadShape`s. See [Load shapes and time points](#load-shapes-and-time-points). |

To get the documents without binding them, call `DssImporter(name).to_cimtbl(model)`. It returns a `DocumentSet`
with a `master` and a list of `parts`, and touches no files.

## The artifacts

For the IEEE 13-node deck, `artifact_dir` holds one file per DSS table, plus the master:

```
IEEE13_CDPSM.cimtbl   bus.cimtbl        zip_fractions.cimtbl   linegeometry.cimtbl
linecode.cimtbl       xfmrcode.cimtbl   vsource.cimtbl         line.cimtbl
transformer.cimtbl    regcontrol.cimtbl load.cimtbl            capacitor.cimtbl
pvsystem.cimtbl       storage.cimtbl    buscoords.cimtbl
```

The master holds the Substation and Feeder (named for the deck's circuit), the `BaseFrequency`, one `BaseVoltage` per
bus voltage and per `voltagebases` value, and one `Import` per part, in this order:

| File | From | Notes |
|---|---|---|
| `<name>.cimtbl` | the deck | the master; its comment lists the DSS classes no mapper reads (`not mapped: Relay 1`) |
| `bus.cimtbl` | the topology walk | one `ConnectivityNode` per bus, with its `BaseVoltage` |
| `zip_fractions.cimtbl` | always | the shared load-response rows (`zip_constant_pq`, ...) that loads name |
| `wiredata.cimtbl`, `cndata.cimtbl`, `tsdata.cimtbl` | `WireData`, `CNData`, `TSData` | wire and cable catalogs |
| `linespacing.cimtbl`, `linegeometry.cimtbl` | `LineSpacing`, `LineGeometry`, `Set earthmodel` | geometry, as `XYSpacing` and `WireConfiguration`, and the deck's `EarthResistivity`. A deck without geometry that sets `earthmodel` (IEEE 13) gets a `linegeometry.cimtbl` with the `EarthResistivity` alone |
| `linecode.cimtbl` | `LineCode` | |
| `xfmrcode.cimtbl` | `XfmrCode` | |
| `vsource.cimtbl` | `Vsource` | |
| `line.cimtbl` | `Line`, with its `Fuse`, `Recloser` and `SwtControl` | |
| `reactor.cimtbl` | `Reactor` | |
| `transformer.cimtbl`, `regcontrol.cimtbl` | `Transformer`, `RegControl` | |
| `loadshape.cimtbl` | `LoadShape` | only shapes a `Load` names as `yearly` |
| `load.cimtbl` | `Load` | |
| `capacitor.cimtbl`, `capcontrol.cimtbl` | `Capacitor`, `CapControl` | |
| `pvsystem.cimtbl`, `storage.cimtbl`, `generator.cimtbl` | `PVSystem`, `Storage`, `Generator` | |
| `buscoords.cimtbl` | `BusCoords`, `LatLongCoords` files | always last: it reads the bound Terminals |

Catalogs come before the equipment that uses them. A class with no records writes no part and no `Import`. Values
keep the deck's units, and the unit sits in the column header, for example `p (kW)`. A comment above a row says what
the importer defaulted (`# defaulted: NumCust=1, enabled=true`). The per-field rules are in the
[import mapping](../CIMTBL_MAPPING.md); how a table is written is in the
[`.cimtbl` contract](https://pnnl-cim-tools.github.io/CIMHub/core/developer/cimtbl/).

## Bus coordinates

`BusCoords` and `LatLongCoords` commands name CSV files of `bus, x, y` (or `bus, lat, long`) rows, separated by commas
or white space. The reader reads them; the importer gives each piece of equipment a CIM `Location`. A line is a
`LINESTRING` through its buses. Any other equipment is a `POINT` at its bus, or at the midpoint of its buses.
Equipment gets a `Location` only if every one of its buses has coordinates, and the file's comment counts the rest
(`not located: <n> of <m> equipment`). A row naming a bus the circuit does not have is ignored, as the engine does,
and listed in the file's comment (`no such bus: <n> (<first names>)`). A row that is not `bus, x, y` raises with its file and line. A deck that uses both
directives raises.

## Load shapes and time points

A `LoadShape` that a `Load` names as `yearly` becomes a `ConformLoadGroup` and a `ConformLoadSchedule`. One that a
`PVSystem`, `Storage` or `Generator` names becomes that device's own `EnergyConnectionSchedule`. The schedule is in the
model; its points are not, because a year of points is too many CIM objects. They go to a dict of Arrow tables
that you pass in:

```python
from cimhub_opendss import DssReader, dss_to_cim

time_points = {}
model = DssReader("cimhub_opendss/tests/atoms/loadshape/loadshapes.dss").read_all()
network = dss_to_cim(model, name="loadshapes", time_points=time_points)
print(list(time_points), time_points["RegularTimePoint"].num_rows)
```

This needs the [`time-points` extra](installation.md). It prints `['RegularTimePoint'] 11`. The tables are written
beside a CIM XML file by `cimhub_core.time_points.write_time_points`; see
[Time series and schedules](https://pnnl-cim-tools.github.io/CIMHub/core/guide/time-points/) in core. Without
`time_points=`, the importer logs one warning that names the dropped shapes and goes on. The master's comment counts
a shape nothing names as `yearly` (`not mapped: Loadshape 1`). To write the points back, see [Export](export.md).

## What raises

The importer fails rather than guessing. Each message names the DSS object.

| Cause | What you get |
|---|---|
| A file the deck redirects to is missing, or a line does not parse | `DssParseError` with the file and line: `Redirect target not found: <path> in <deck> at line 2` |
| A property the schema does not have | `DssParseError`: `unknown property 'bogusprop' on Line: <the command> in <deck> at line 3` |
| A DSS class the schema does not have | `DssParseError`: `Wibble.x: unknown DSS class 'Wibble' in <deck> at line 3` |
| A deck with no `New Circuit` | `ValueError`: `the deck has no New Circuit` |
| A second `New Circuit` | `DssParseError`: `a second New Circuit (the first is 'a'); a deck is one circuit` |
| A property the mapper classifies as raising when set | `ValueError`: `Line l1: Seasons, Ratings not mapped yet (no deck in the sweep sets them)` |
| Equipment on a bus the topology walk does not reach | `ValueError`: `Load ld2: bus zz has no voltage (the topology walk did not reach it)`. A `Vsource` and a `Transformer` say `Vsource <name>: no bus voltage for <bus>` |
| A `Line` whose `phases` differ from its `LineCode`'s `nphases` | `ValueError`: `Line <name>: phases=1 with LineCode <code> (nphases=3); the engine's rule is not pinned yet (DSS-10)`. The EPRI K1 and M1 feeders stop here |
| A line code with no units, whose lines give none and whose median `r` fits no unit | `ValueError`: `LineCodes with no units: median r <x> per unit fits no length unit ...`; pass `length_unit=` |
| A `device_geometry` other than `"point"` or `"linestring"` | `ValueError` when the importer is made |

`DssParseError` has `file_path` and `line_number` attributes. The `ValueError`s of the mappers come from the
classification of each DSS property: copied, mapped, structural, derived, untranscribed, or raising when set. A
property that raises says in the [import mapping](../CIMTBL_MAPPING.md) which deck would justify mapping it. The ones
users meet most:

| Class | Properties | Why |
|---|---|---|
| `Line`, `WireData`, `CNData`, `TSData` | `Seasons`, `Ratings` | An indexed rating array that names no calendar season. |
| `WireData`, `CNData`, `TSData` | `GMRac` unset; both or neither of `radius` and `diam` set; a unit (`Runits`, `GMRunits`, `radunits`) unset; neither `Rac` nor `Rdc` set | The engine's default, or the last property set, is not recorded by the reader. |
| `WireData`, `CNData`, `TSData` | `Capradius` | No mapping yet. |
| `Transformer`, `XfmrCode` | `RdcOhms` on some windings only, or on a 3-phase inline transformer or a regulator; `Seasons` without `Ratings`, or a `Ratings` count other than `Seasons` | The engine's default for an unset winding is not recorded; a balanced end or an `AutoTransformerEnd` has no winding `rDC`; the engine keeps only `Seasons` ratings and pads the rest with zeros. |
| `CNData` | `SemiconLayer` | No mapping yet. |
| `LoadShape` | `UseActual=Yes`, `hour`, `csvfile`, `sngfile`, `dblfile`, `PQCSVFile`, `Pmult`, `Pbase`, `Qbase`; an `npts` other than the number of values | No deck uses them, or the result depends on command order. |
| `Load` | a `yearly` that names no shape in the deck | The reference does not resolve: `Load ld: yearly=nope names no LoadShape of the deck`. |

## What is skipped, loudly

A DSS class no mapper reads (monitors, meters, curves, and so on) is not an error. The master's comment lists it as
`not mapped: <Class> <count>`, so nothing disappears silently. [What converts](coverage.md) has the list. What the
class would have configured is absent from the CIM network.

## Next

[Export](export.md) goes the other way. [Round trip](roundtrip.md) checks that a deck survives both.

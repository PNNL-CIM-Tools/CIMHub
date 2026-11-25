# Sources, options and coordinates

The deck's circuit, its `Set` options, its buses and its bus coordinates. These are the parts of a DSS deck that are
not a piece of equipment, plus the one source every deck has. How to read the tables is on the
[reference landing page](index.md).

| DSS | CIM (cim18v17) | Import | Export |
|---|---|---|---|
| `New Circuit`, `Vsource` | `EnergySource` | `vsource.cimtbl` (shape `source`) | `Vsource`; the circuit's is `New Circuit` |
| `New Circuit` name, `Set defaultbasefreq`, `Set voltagebases` | `Substation`, `Feeder`, `BaseFrequency`, `BaseVoltage` | the master `.cimtbl` | the deck's `Options` record |
| `Set earthmodel` | `EarthResistivity` | `linegeometry.cimtbl`, when the deck has geometry or sets `earthmodel` | `Set earthmodel` |
| `Open`, `Close` | `Switch.open` | `line.cimtbl` | `Open Line.<name> 1` |
| the walk's buses | `ConnectivityNode` with a `BaseVoltage` | `bus.cimtbl` | bus names `<bus>.<node>...` |
| `BusCoords`, `LatLongCoords` | `CoordinateSystem`, `Location` | `buscoords.cimtbl` (shape `location`) | `Buscoords` rows and a CSV beside the deck |

The shapes are described on the core site's [shapes page](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/).

## Circuit and Vsource

`New Circuit.<name>` is `New Vsource.source` with the circuit's name kept on the deck's `Options`, so the circuit and
every `Vsource` map alike: one `EnergySource` per source, in the Substation. The mRID is `src_` plus the name,
lowercased. The three ways DSS gives a source's Thevenin impedance map as follows, and a source that sets two of them
raises, because DSS keeps the one set last and the reader does not record the order.

| Impedance group | Import | Export |
|---|---|---|
| `R1 X1 R0 X0` (ohm) | copied to `r`, `x`, `r0`, `x0`; all four must be set | written for a 3-phase source |
| `MVAsc3 MVAsc1` with `x1r1`, `x0r0` | derived by `thevenin_from_short_circuit`; an unset value takes its DSS default (2000, 2100, 4, 3) and is listed as `defaulted` | written for a 1-phase source, by the exact inverse `short_circuit_from_thevenin` |
| `Isc3 Isc1` (A) | the short-circuit power in kVA by `kvasc_from_isc` (kV x A), then as above; kV squared over kVA is kohm, so these rows have their own table with `r (kohm)` ... `x0 (kohm)` | never written |
| none set | all four MVAsc defaults, as the engine does | not applicable |

| property | import | export |
|---|---|---|
| `name` | copied to `EnergySource.name`; mRID = src_ + name, lowercased | written: Names; the circuit's source is always `source` |
| `bus1` | structural: node, and phases from its conductors; default sourcebus | written: bus_ref(get_terminal_nodes, get_source.phases) |
| `basekv` | copied to `EnergySource.nominalVoltage` (kV) | written: get_source.nominal_u (kV) |
| `pu` | derived: voltageMagnitude (kV) = basekv x pu | written: get_source.magnitude_pu |
| `angle` | copied to `EnergySource.voltageAngle` (deg) | written by rule: get_source.angle (deg); unset -> 0, the reference angle |
| `phases` | structural: 3 = ABC, 1 = the phase of bus1's conductor | written: the phase conductors: 3 or 1, any other count raises |
| `MVAsc3` | derived: r, x (thevenin_from_short_circuit) | written: 1-phase: kV^2 / abs (short_circuit_from_thevenin) |
| `MVAsc1` | derived: r0, x0 (thevenin_from_short_circuit) | written: 1-phase: 3 kV^2 / abs(2 Z1 + Z0) |
| `x1r1` | derived: r, x (thevenin_from_short_circuit) | written: 1-phase: x / r; r = 0 raises |
| `x0r0` | derived: r0, x0 (thevenin_from_short_circuit) | written: 1-phase: x0 / r0; r0 = 0 raises |
| `Isc3` | derived: the 3-phase short-circuit kVA (kvasc_from_isc), then as MVAsc3; r, x in kohm | not written: the ohms or the MVAsc group carries the same impedance |
| `Isc1` | derived: the 1-phase short-circuit kVA (kvasc_from_isc), then as MVAsc1; r0, x0 in kohm | not written: the ohms or the MVAsc group carries the same impedance |
| `R1` | copied to `EnergySource.r` (ohm) | written: 3-phase: get_source.impedance.r (ohm); r, x, r0, x0 unset raises (DSS takes one group) |
| `X1` | copied to `EnergySource.x` (ohm) | written: 3-phase: get_source.impedance.x (ohm) |
| `R0` | copied to `EnergySource.r0` (ohm) | written: 3-phase: get_source.impedance.r0 (ohm) |
| `X0` | copied to `EnergySource.x0` (ohm) | written: 3-phase: get_source.impedance.x0 (ohm) |
| `bus2` | raises when set: an ungrounded (series) source has no source-shape home | not written: an EnergySource has one terminal |
| `Z1`, `Z0` | raises when set (not mapped yet) | not written: the ohms or the MVAsc group carries the same impedance |
| `Z2` | raises when set (not mapped yet) | not written: r2/x2 set and different from r/x raises: the Z2 group is not mapped (nor imported) |
| `puZ1`, `puZ0`, `puZ2` | raises when set (not mapped yet) | not written: the ohms or the MVAsc group carries the same impedance |
| `baseMVA` | raises when set (not mapped yet) (the base of puZ1/puZ0/puZ2) | not written: the ohms or the MVAsc group carries the same impedance |
| `enabled` | copied to `EnergySource.normallyInService` | written: get_in_service(which='normal'); unset -> not written |
| `like` | untranscribed: the reader resolves like= before mapping | not written: the writer never writes like= |
| `frequency`, `ScanType`, `Sequence`, `Yearly`, `Daily`, `Duty`, `Model`, `puZideal`, `spectrum`, `basefreq` | untranscribed (listed in the table comment) | not written |

**Fail fast.**

- `bus2`, `Z1`, `Z0`, `Z2`, `puZ1`, `puZ0`, `puZ2` and `baseMVA` raise when set: `Vsource source: Z1 not mapped yet (no deck in the sweep sets them)`.
- Two impedance groups raise: `Vsource source: sets the ohms and MVAsc impedance groups; DSS keeps whichever was set last, which the reader does not record`. So does a partial `R1 X1 R0 X0`.
- A source with `phases` other than 1 or 3 raises (`only 1- and 3-phase sources are walked`), as does a bus whose nodes do not fit the phase count.
- On export, an `EnergySource` with `r`, `x`, `r0` or `x0` unset raises, as does a 1-phase source with `r = 0` or `r0 = 0` (no X/R ratio). With several `EnergySource`s, `circuit_source=` (default `"source"`) names the one exported as `New Circuit`; unless exactly one is exported under that name, the export raises.

**Expected differences after a round trip.**

- A 3-phase source given by `MVAsc` or `Isc` comes back as `R1 X1 R0 X0`; a 1-phase source given by ohms comes back as `MVAsc3 MVAsc1 x1r1 x0r0`. The impedance is the same in the engine.
- The circuit's source is always named `source`; the circuit name is the Feeder's.
- `angle` unset is written `0`. Floats are written to 15 significant digits.
- `frequency`, `basefreq`, the harmonic and time-series slots are not in CIM and are not written.

Excerpt from `cimhub_opendss/tests/atoms/vsource/mvasc.cimtbl` (the `defaulted` comment lists what the deck left unset):

```
Table EnergySource: mRID, name, node, phases, nominalVoltage (kV), voltageMagnitude (kV), voltageAngle (deg), r (ohm), x (ohm), r0 (ohm), x0 (ohm), normallyInService, BaseVoltage, EquipmentContainer=sub_atom
    # derived from MVAsc3=20000.0, MVAsc1=21000.0; defaulted: x1r1=4.0, x0r0=3.0
    src_source, source, sourcebus, , 115.0, 115.0, 30.0, 0.16037668205527517, 0.6415067282211007, 0.17960358301233556, 0.5388107490370067, , bv_115kv
```

A blank `phases` cell is a balanced three-phase source (`ABC`).

## Set options, containers and open switches

The reader keeps three `Set` options and the `Open`/`Close` commands on one `Options` record. Every other `Set`
option (`mode`, `controlmode`, `tolerance`, and so on) is a solution setting, not part of the model, and is dropped.

| DSS | Import | Export |
|---|---|---|
| `New Circuit.<name>` | Substation `sub_<name>` and Feeder `fdr_<name>` (lowercased), both named `<name>`; the Substation holds the `EnergySource`s, the Feeder everything else. A deck with no `New Circuit` raises `the deck has no New Circuit`; a second one raises at read time. | `Options.circuit` is the one Feeder's name. Several Feeders that share one `NormalEnergizingSubstation` are one circuit, named by the Substation; a Feeder with no equipment is not counted. Otherwise it raises. |
| `Set defaultbasefreq` | `BaseFrequency` `bf_<f>hz`, `frequency (Hz)`. Unset is the DSS default, 60, listed as `defaulted`. It is also the frequency that turns a `LineCode`'s `C` into `b` when the code has no `baseFreq`. | `Set defaultbasefreq=<network base frequency>`, written before `New Circuit`. |
| `Set voltagebases` | Mapped. The BaseVoltages are one per distinct bus voltage of the topology walk and one per `voltagebases` value, highest first. A base on no bus is kept, because it is what the engine's `CalcVoltageBases` snaps bus bases to; buses still take the walk's voltage. The master's comment lists the deck's `voltagebases`, those on no bus, and walk voltages the list lacks. | `Set voltagebases=[...]` and `CalcVoltageBases`: every `BaseVoltage.nominalVoltage` in kV, ascending, so the deck's bases come back. A BaseVoltage with no `nominalVoltage` raises. |
| `Set earthmodel` | One `EarthResistivity` `earth` (`earthModelType` carson or deri, `rho`) that every geometry `WireConfiguration` names, when the deck has a `LineGeometry` or a `Line` with `spacing=`. Unset is the engine's Deri and 100 ohm-m, listed as `defaulted`. A deck without geometry that sets `earthmodel` gets the same `earth`, which no line names (`rho` the default 100 ohm-m, listed as `defaulted`); a deck with neither gets none. `FullCarson` raises: `earthmodel=FullCarson: EarthModelKind has ['carson', 'deri']`. The geometry lines' `rho` must all agree. | `Set earthmodel=Carson` or `Deri`, written after `New Circuit`. The geometry `WireConfiguration`s' models must agree, and one without an `EarthResistivity` beside one with raises. With no geometry at all, the network's one `EarthResistivity`, which no line names. None at all: not written. |
| `Open Class.name n`, `Close` | An open `Line` becomes an open switch ([Line](lines.md)). An `Open` of anything but a `Line` raises: `Open Transformer.t 1: only a Line's terminal is mapped (as an open switch)`. | `Open Line.<name> 1` for each switch open in the chosen state (`switch_state`). |

The master's `Authority` and `Model` come from the caller (`DssImporter(name, authority=...)`). A DSS class no mapper
reads is counted in the master's `not mapped:` comment.

## Buses and BaseVoltages

A DSS bus is a name, and a `Line` or `Reactor` has no voltage of its own. The importer runs the topology walk
(`cimtopology.core.walk`, the same one every importer uses) once, from the `Vsource`s, and writes one
`ConnectivityNode` per bus the walk reaches, with its `BaseVoltage`, in `bus.cimtbl`. The master carries the
BaseVoltages. Equipment keeps its own `BaseVoltage` column too, which cimtables needs as the base of a per-unit
column.

What the walk follows:

| DSS | Walk |
|---|---|
| `Vsource` | A source: `basekv` is phase to phase on 3 phases, the source voltage on 1 phase. |
| `Line` | A branch, switches too: an open switch keeps its voltage. A `Line` with `bus1` or `bus2` unset raises. |
| `Reactor`, `Capacitor` | A branch only when `bus2` is on another bus (a series element). |
| `Transformer` | Coils with `phases`, `windings`, `kVs` and `conns` from the instance, else its `XfmrCode`. A polyphase winding's kV is phase to phase; a split-phase secondary is windings 2 and 3 on one bus. |

Bus names are lowercased, and a ConnectivityNode's `mRID` and `name` are the bus name, so a `node=` column in any other
part binds to it. A bus the walk does not reach has no row, and the equipment on it raises: `Line l: bus nowhere has
no voltage (the topology walk did not reach it)`.

Export reads the bus from each Terminal's `ConnectivityNode` (`Names.bus`; a `.` in the name becomes `_`, because it
is DSS's node delimiter). A bus reference is `<bus>.<n>...` with the conductors in order, A/B/C as 1/2/3 and s1/s2 as
1/2, never bare. A `BusbarSection` is its node's bus and writes no record. Two buses that land on one name raise.

## BusCoords and LatLongCoords

A ConnectivityNode is not a `PowerSystemResource`, so a bus cannot hold a `Location`. The importer places the
equipment as a GIS does, through the `wkt` column of the `location` shape, once every other part has bound its
Terminals (`bound_parts`, so `buscoords.cimtbl` is imported last).

| Equipment | Geometry on import |
|---|---|
| a `Line` (`ACLineSegment`) | a `LINESTRING` through its Terminals' buses, in Terminal order |
| anything else with one Terminal | a `POINT` at its bus |
| anything else with several | a `POINT` at the centroid of its buses: a switch, fuse or transformer midway between its buses |
| a two-terminal device with `device_geometry="linestring"` | a `LINESTRING` from bus to bus, like a line (`DssImporter(..., device_geometry=...)`; the default is `"point"`) |

| property | import | export |
|---|---|---|
| `name` | structural: picks the bus: every Terminal on it takes its coordinates; a name the circuit has no bus for is ignored, as in the engine (counted in the file comment) | written: the bus (Names.bus) of each Terminal of located equipment |
| `x` | derived: geometry: a line's LINESTRING vertex at each Terminal bus, verbatim; other equipment's POINT at its Terminal buses' centroid (the bus itself for one Terminal) | written: the Terminal's PositionPoint xPosition (get_location_coordinates); a bus only a device point touches is solved from it as the centroid of the device's buses |
| `y` | derived: as x | written: as x, from yPosition |
| `geographic` | mapped: the directive (LatLongCoords -> true) picks the CoordinateSystem: COORDINATE_SYSTEMS | written: crsUrn CRS84 -> true (LatLongCoords), OpenDSSLocalBusCoordinates -> false; others raise |

**Fail fast.**

- A deck that gives both `BusCoords` and `LatLongCoords` raises: one coordinate system per model.
- An unknown `device_geometry` raises.
- On export, two Locations that put one bus at different points raise (`a DSS bus has one position`), as do Locations in two coordinate systems, a `crsUrn` other than the two below, and a Location with a point count that fits no Terminal pairing.

**What is not an error.** Equipment with a Terminal bus that has no coordinates gets no `Location`, and coordinates for a
bus the circuit does not have are ignored, as the engine ignores them. Both are counted in the file's comment.

The CoordinateSystem picks the file: `BusCoords` is `crs_bus` with the URN `OpenDSSLocalBusCoordinates` (the deck's own
projection, which it does not name); `LatLongCoords` is `crs_latlong`, `urn:ogc:def:crs:OGC:1.3:CRS84`, with x the
longitude. Export inverts it and writes `<stem>_buscoords.csv` or `<stem>_latlongcoords.csv` beside the deck, which
`DssWriter` names in a `BusCoords` or `LatLongCoords` command.

**Expected differences.** A bus no located equipment touches has no coordinates after export. A single `POINT` on a
switch, fuse or transformer is its buses' centroid, so it places only the buses nothing else placed: next to one placed
bus it reflects it across the point, which gives back the importer's midpoint to float noise; with none placed every bus
goes at the point. An import under `device_geometry="linestring"` has no device points and comes back exactly.

Excerpt from `cimhub_opendss/tests/atoms/buscoords/local.cimtbl` (a line, a switch, a regulator, a load and a PV; the
line `far` has a bus with no coordinates, so it is not located):

```
Object CoordinateSystem: mRID=crs_bus, name=BusCoords, crsUrn=OpenDSSLocalBusCoordinates

# a line's LINESTRING through its Terminal buses; other equipment a POINT at their centroid
Update Table PowerSystemResource: mRID, wkt
    src_source, "POINT (0.0 0.0)"
    ln_l1,      "LINESTRING (0.0 0.0, 50.0 0.0)"
    sw_sw1,     "POINT (75.0 0.0)"
    xf_reg,     "POINT (102.5 2.5)"
```

## Run it

This imports a 1-phase source on phase B and exports it. It runs from the repository root.

```python
from pathlib import Path

from cimhub_opendss import DssReader, cim_to_dss, dss_to_cim

deck = Path("cimhub_opendss/tests/atoms/vsource/single_phase.dss")
network = dss_to_cim(DssReader(deck).read_all(), name="single_phase", artifact_dir="/tmp/ref-sources")

text = Path("/tmp/ref-sources/vsource.cimtbl").read_text()
print(text[text.index("Table EnergySource"):])

cim_to_dss(network, "/tmp/ref-sources/back.dss", name_source="name")
print(Path("/tmp/ref-sources/back.dss").read_text())
```

```
Table EnergySource: mRID, name, node, phases, nominalVoltage (kV), voltageMagnitude (kV), voltageAngle (deg), r (ohm), x (ohm), r0 (ohm), x0 (ohm), normallyInService, BaseVoltage, EquipmentContainer=sub_lateral
    # derived from MVAsc3=100.0, MVAsc1=90.0; defaulted: angle=0.0, x1r1=4.0, x0r0=3.0
    src_source, source, tap, B, 7.2, 7.344, 0.0, 0.12573046801883503, 0.5029218720753401, 0.21896347099154312, 0.6568904129746294, , bv_7p2kv

Clear
Set defaultbasefreq=60
New Circuit.lateral phases=1 bus1=tap.2 basekv=7.2 pu=1.02 angle=0 MVAsc3=100 MVAsc1=90 x1r1=4 x0r0=3
Set voltagebases=[7.2]
CalcVoltageBases
```

`name_source="name"` names the exported objects by their CIM `name`. The default is `mrid` (or `$CIMHUB_NAME_SOURCE`),
which would name this circuit `fdr_lateral`.

See the core site for the [source and location shapes](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/),
the [getters](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/) the exporter reads through, and the
[topology reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/topology/).

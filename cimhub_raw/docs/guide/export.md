# Export: CIM to RAW

```python
from cimhub_raw.exporter.cim_to_raw import RawExporter, cim_to_raw
from cimhub_raw.raw34_writer import Raw34Writer

cim_to_raw(network, "IEEE14_from_cim.raw")           # export and write in one call

model = RawExporter().to_model(network)              # records only, no files
Raw34Writer().write(model, "IEEE14_from_cim.raw")
```

`network` is a cim18v17 network that carries the bus numbers the importer wrote, for example the result of
[`raw_to_cim`](import.md). The exporter reads it through the
[getters in `cimhub_core`](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/) and returns a `GraphModel` of RAW
records, the same shape `Raw34Reader.read_all()` returns, so the `.raw` the writer produces reads back through the
reader and the importer. Only `Raw34Writer` touches the filesystem, and it does not create folders: the destination's
folder must exist.

## Options

`RawExporter().to_model(network)` and `cim_to_raw(network, destination)` take no options. `destination` is the `.raw`
path. The case's units come from the network: the exporter reads whether the ratings are in MVA or in current (below),
and every quantity in the unit RAW fixes for it.

## What it exports

Each RAW table is written from the CIM classes it was imported to. Records come out keyed as they went in.

| RAW table | Read from CIM |
|---|---|
| case identification | `BasePower` (SBASE), `BaseFrequency` (BASFRQ), the rating-set `OperationalLimitType`s (`RATING` records), NXFRAT and XFRRAT from the kind of limit the ratings are |
| zone | `SubGeographicalRegion` |
| area | `ControlArea` (PDES is minus `netInterchange`, PTOL is `pTolerance`) |
| bus | `TopologicalNode` with its `BusbarSection` (voltage limits) and `SvVoltage` (VM and VA) |
| branch | `ACLineSegment`, `SeriesCompensator`, and the line shunts linked to them |
| system switching device | `Switch`, `Breaker` and `Disconnector` between two buses |
| multi-section line | the `Line` that holds a path of branches |
| load | `EnergyConsumer`, `ConformLoad`, `NonConformLoad` |
| fixed shunt, switched shunt | `LinearShuntCompensator` (a bank's blocks under one `RegulatingControl` are one switched shunt) |
| generator | `SynchronousMachine`, `PowerElectronicsConnection`, and a generator's step-up transformer, folded back into GTAP, RT and XT |
| transformer | `PowerTransformer` that is not a generator's step-up |
| impedance correction | `ImpedanceTapChangerTable` |

A value that is not in CIM is left blank, and RAW applies its own default (the owner fields, for example, and the
case's title lines). The [round trip](roundtrip.md) page lists what comes back different.

## Bus numbers and IDs

RAW identifies things by number and by short IDs. The exporter takes them from the mRIDs the importer wrote:

- **Bus number (I)** is `TopologicalNode.busNumber`. A node without one is internal to a device (a generator's step-up
  node, a DC converter's valve side) and is not a bus. A number used by two nodes raises, and so does a network where no
  node has one: `no TopologicalNode has a busNumber: numbering a model from another format is not done yet`. A network
  from another converter does not export until it carries bus numbers.
- **Zone and area numbers** come from the mRIDs `srgn_<n>` and `ca_<n>`. A zone or area whose mRID is not of that form
  gets the next number above the largest taken, and the exporter logs the count at INFO. Two mRIDs that give one
  number raise.
- **A device's ID** (CKT of a branch, switch and transformer, the load, shunt and generator ID) is the rest of its mRID
  after the prefix and its buses: `ln_4_7_1` is the branch 4 to 7 with CKT `1`. It is used only when the buses are
  the device's own, in order, and it fits RAW's two characters. Otherwise the ID is the next free `1`, `2`, ... on those
  buses, and the exporter logs the count at INFO. A multi-section line without a key gets `&1`, `&2`, ... Two devices
  with one key raise.
- **NAME** is the CIM `name`. It is written blank when it is the key the importer uses for a blank NAME (the bus number
  for a bus, zone or area, `<I>_<J>_<CKT>` for a branch). A name longer than RAW's field raises: 12 characters for a
  bus, zone or area, 40 for a branch, switch or transformer.

To see the INFO messages, enable logging:

```python
import logging

logging.basicConfig(level=logging.INFO)
```

## A bus's AREA

CIM has no association from a node to a control area, so the exporter traces each bus's AREA from what CIM does place in
one:

- the bus of every `SynchronousMachine` and `PowerElectronicsConnection` takes its unit's `ControlArea`;
- a terminal that holds a `TieFlow` pair takes the pair's `positiveFlowIn = false` area, and the other terminals of that
  device take the `true` (home) area;
- the area then spreads across every device with two or more nodes and no `TieFlow`.

A bus in a group of buses with no such seed gets no AREA: it is written blank, and RAW reads a blank AREA as its default. The importer
lists these buses as `untranscribed: area=<AREA>`. Two areas meeting in one group raise:
`buses joined inside one area are seeded with ['ca_1', 'ca_2'] (by [...])`. A load's AREA is its own, from its load group.

## Ratings in MVA or in current

RATE1 to RATE12 of a branch, switch or transformer winding are the limits whose type is `olt_rate<n>` (0 where there is
none). They are in MVA when the limits are `ApparentPowerLimit`s. When they are `CurrentLimit`s, the exporter writes NXFRAT
(branches and switches) or XFRRAT (transformers) as 1 and each RATE as a current expressed as MVA, the square root of 3
times the device's base voltage in kV times the current in kA. A case, or one device, with both kinds raises, because
RAW's flag is one or the other, and so does a limit of any other type.

## What it refuses

`to_model` first checks every `ConductingEquipment` class in the network against the classes the modules above export,
and raises before it writes anything:

```
ValueError: no RAW export yet for {'CsConverter': 8}
```

The message names each unexported class and its count. Today DC lines and FACTS devices (`CsConverter`, `VsConverter`,
`StaticSynchronousCompensator`) are imported but not yet exported, so a case that has them imports and then raises here.
[What converts](coverage.md) lists them.

The exporter also raises on CIM it cannot say in RAW. Most often:

| CIM | Result |
|---|---|
| a branch with a line conductance (`gch`) | RAW has none |
| a switch with a `ConnectivityNode` at one terminal only | a switch is between two buses |
| a nonlinear shunt, or a shunt block with a conductance | not in RAW |
| an exponent load response | a RAW load is ZIP only |
| a shunt whose rated voltage is not its bus's base voltage | RAW states a shunt at the bus voltage |
| a generator plant whose machines disagree on the regulated bus, set point or reactive share | PSS/E treats them as one |
| a step-up transformer that is out of service, has a tap that moves, or is rated off its bus voltage | a RAW step-up has none of these |
| a transformer with a winding on a node that has no bus number | not a RAW transformer |
| a transformer with a moving tap on winding 2 of two, or a phase shifter under a voltage control | not in RAW |
| an impedance correction table that no winding uses | no base to convert its ratios |

Each message names the object. A SUBSTATION block (nodes, switching devices, equipment terminals) imports to CIM but is not yet
exported: a case with node-breaker data comes back as a bus-branch case, and a switch between two `ConnectivityNode`s is
left out.

## Writing the case

`Raw34Writer().write(model, destination)` writes the whole file. It is the reader's mirror and walks the same layout:

- Fields are written by position. A `None` field is blank (two commas in a row), and trailing blank fields are left off.
  Nothing is defaulted, so the writer writes back only what it was given.
- A float is written with the precision the schema gives when that reads back as the same number, otherwise in the shortest
  exact form. A string is padded to the field's width and quoted as the schema says.
- Records come out in the model's order, which is the file order for a model the reader built.
- The two title lines are written as given, always two. A case with more than two raises.
- Bus references are written as numbers, never as extended names.
- Every section ends with `0 / END OF <section> DATA, BEGIN <next> DATA`, and the file ends with `Q`.
- A model with multi-terminal DC or GNE records raises `NotImplementedError`. Writing a model with no case
  identification record raises `ValueError`.

`Raw34Writer().serialize(record)` returns one record's text, and `lines(model)` the whole file as a list of lines.

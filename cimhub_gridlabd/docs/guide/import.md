# Import: GLM to CIM

```python
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim

model = GlmReader("cimhub_gridlabd/tests/decks/IEEE/IEEE13_cdpsm.glm", defines={"VSOURCE": "66395.28"}).read_all()
network = glm_to_cim(model, name="IEEE13_cdpsm", artifact_dir="artifacts/IEEE13_cdpsm")
```

`network` is a cim18v17 cim-graph model. `artifact_dir` keeps the `.cimtbl` text it was built from.

The IEEE exports drive every load by a player named `ieeezipload` that the GridAPPS-D run file defines, not the
model, so the importer logs one warning: the name is in no player of the deck, and the loads' group has no schedule.

## What happens

1. `GlmReader(path, defines=...).read_all()` parses the `.glm` and the files it `#include`s, and returns a `GlmModel`
   of typed records.
2. `GlmImporter(name).to_cimtbl(model)` walks the model's topology once (with `cimtopology`), then runs one mapper
   per GLM class. Each mapper turns records into a `.cimtbl` document. It does not build CIM objects.
3. `glm_to_cim` writes the documents and cimtables binds them into a network.

The `.cimtbl` text is the only input to CIM. If a value is wrong in the network, it is wrong in the text, and you can
read it there.

## Reading a `.glm`

`GlmReader(source, *, defines=None)` takes the path of the `.glm` and the macros the model expects from the command
line. `read_all()` raises `FileNotFoundError` if the file is missing and `GlmParseError` for anything it cannot read.

| In the `.glm` | What the reader does |
|---|---|
| `${NAME}` | Expands from a `#define` or `#set` earlier in the file, then from `defines=`. A name in neither raises: `macro ${VSOURCE} is not defined (pass it in defines=)` |
| `#define name=value`, `#set name=value` | Kept in `model.defines` and `model.globals`. `defines=` entries are added to `model.defines` |
| `#include "other.glm"` | Read in place, relative to the file that includes it. A missing file raises |
| any other `#` directive (`#if`, `#ifdef`, ...) | Raises: `directive '#if' is not read` |
| `clock { ... }` | Its settings are kept as text in `model.clock` |
| `module name { ... }` or `module name;` | Kept in `model.modules[name]` |
| `schedule name { ... }` | The statements are kept as written in `model.schedules[name]` |
| `class player { double value; }` | Read, in `model.classes`. Any other `class` block raises |
| `object type { ... }` | A record in `model.graph`, keyed by its class. An object nested in another gets the outer one as its `parent`. `object house:..20` makes 20 objects |
| a player's `file` | Read beside the file that declares the player, into `model.tapes[player name]` as `(time, value)` rows as written. A row with no comma raises |

Rules that matter when a model does not convert as you expect:

- **Units stay as written.** `distance_AN 30 in` stores `30.0` and records `in` in `model.written_units`. The reader
  converts nothing. A value with no unit is in the unit the GridLAB-D class declares for the property.
- **Expressions are kept as text.** A numeric property whose text is not a number (`LIGHTS*1.2`,
  `random.normal(1750,400)`) is stored in `model.expressions` and its slot stays unset. The importer raises only if a
  mapper reads that slot, so an expression on a property the importer ignores does not stop the conversion.
- **Complex values** are `a+bj`, `a+bi`, `m+ad` (polar, degrees), `m+ar` (polar, radians) or a plain number. A polar
  value is stored as rectangular, and its magnitude and angle as written go to `model.polar`.
- **Names** are unique across the model, as in GridLAB-D. An unnamed object is called `<class>:<id>`, for example
  `load:3`, from its header id or its position in the file. A reference written `<class>:<id>` resolves to that name.
- **A property set twice** keeps the last value, as GridLAB-D does, and the reader logs a warning.
- **An object type the schema does not know** (`recorder`, `climate`) is counted in `model.not_read` and its
  properties are not read. A property a *known* class does not have raises. Keywords are case-sensitive.

## Options

`glm_to_cim(model, *, name, authority=..., substation=None, feeder=None, network=None, artifact_dir=None,
time_points=None)`. `GlmImporter(name, *, authority=..., substation=None, feeder=None, time_points=None)` takes the
same keywords except `network` and `artifact_dir`, which go to its `to_cim` method.

| Argument | Meaning |
|---|---|
| `name` | Required. The master document's `Model` and file stem, and the default name of the Substation and Feeder. Do not use the name of a part file (`bus`, `load`, `player`): the documents' names must be distinct, or writing raises `document names repeat`. |
| `artifact_dir` | Keep the `.cimtbl` files here. Without it they go to a temporary directory that is removed after loading. |
| `network` | An existing cim18v17 network to bind onto, to merge several models. |
| `authority` | The master's `Authority`. Defaults to `https://github.com/PNNL-CIM-Tools/CIMHub`. |
| `substation`, `feeder` | Name the containers. The mRIDs are `sub_<substation>` and `fdr_<feeder>`; each is `name` unless given. Use them when a utility's code is the scope and the feeder's own key is the container. |
| `time_points` | A dict the importer fills with the points of the players and schedules. See [Players and schedules](time-series.md). |

To get the documents without binding them, call `GlmImporter(name).to_cimtbl(model)`. It returns a `DocumentSet`
with a `master` and a list of `parts`, and touches no files.

## The topology walk

Before any mapper runs, the importer walks the model once with `cimtopology`:

- **Buses.** Every `node` or `triplex_node` object, and every object of a class derived from one (`meter`,
  `substation`, `load`, `capacitor`, `triplex_meter`, `triplex_load`, ...), is a bus. A bus whose `parent` is a bus is solved by GridLAB-D as its parent's bus, so it is not a bus of its own: its
  equipment lands on the root of its parent chain. A parent that is not a bus, a loop in the parent chain, or a child
  whose phases are not a subset of its root's raises.
- **The source.** Every `substation` and every bus with `bustype SWING` is a swing bus, and becomes an
  `EnergySource`. Its `nominal_voltage` is phase to neutral, on a three-phase or a one-phase
  system, and gives the `EnergySource`'s `nominalVoltage`; any other phase count raises. Its voltage and angle come
  from `positive_sequence_voltage` (a `substation`) or `voltage_A`, else from `nominal_voltage`. GridLAB-D's swing bus
  has no impedance, so the source gets a default one: 10 000 MVA short circuit, X/R of 10, with a comment that says
  so. A `SWING_PQ` bus is a plain bus.
- **Branches.** Every line, switch, fuse, recloser, sectionalizer, series reactor and regulator joins two buses, and
  a transformer carries a voltage ratio from its configuration.
- **Voltages.** The walk gives every bus its voltage from the source outward, through the transformers. These are the
  `BaseVoltage`s. The `nominal_voltage` the model writes on a bus is only checked against the walk: a bus more than
  10 % off is listed in the bus file's comment, not raised.

A bus the walk does not reach has no row, and a load or other equipment on it raises a bare `KeyError` naming the bus.

## The artifacts

`artifact_dir` holds the master, `<name>.cimtbl`, and one file per mapped GLM class that the model uses. For the
IEEE 13-node model:

```
IEEE13_cdpsm.cimtbl   bus.cimtbl            source.cimtbl        zip_fractions.cimtbl
line_configuration.cimtbl                   transformer_configuration.cimtbl
overhead_line.cimtbl  switch.cimtbl         fuse.cimtbl          recloser.cimtbl
transformer.cimtbl    regulator.cimtbl      player.cimtbl        load.cimtbl
triplex_load.cimtbl   capacitor.cimtbl      inverter.cimtbl
```

The master holds the Substation and Feeder, the `BaseFrequency`, one `BaseVoltage` per distinct bus voltage (highest
first), the two operational limit types, and one `Import` per part. It ends with the feeder head: each link's Terminal
on a swing bus is set as the Feeder's `NormalHeadTerminal`. `BaseFrequency` is `nominal_frequency` from
`module powerflow { ... }` or `#set powerflow::nominal_frequency=...`, else GridLAB-D's 60 Hz, and the master says
`defaulted` in a comment when it used the default. The parts are written in this order, so that a catalog comes
before what uses it:

| Part file | From |
|---|---|
| `bus.cimtbl` | every root bus: a `ConnectivityNode` with its `BaseVoltage` |
| `source.cimtbl` | every `substation` and swing bus: an `EnergySource` |
| `zip_fractions.cimtbl` | always: the ZIP load-response rows that loads name |
| `overhead_line_conductor.cimtbl`, `underground_line_conductor.cimtbl`, `triplex_line_conductor.cimtbl` | the conductor catalogs |
| `line_spacing.cimtbl` | `line_spacing`: geometry |
| `line_configuration.cimtbl`, `triplex_line_configuration.cimtbl` | line configurations: a template impedance or a geometry |
| `transformer_configuration.cimtbl` | transformer ratings and connections |
| `overhead_line.cimtbl`, `underground_line.cimtbl`, `triplex_line.cimtbl` | lines |
| `switch.cimtbl`, `fuse.cimtbl`, `recloser.cimtbl` | switching devices (a `sectionalizer` is walked as a branch but not mapped) |
| `series_reactor.cimtbl` | `series_reactor` |
| `transformer.cimtbl`, `regulator.cimtbl` | transformers and regulators (a regulator's configuration is read with it) |
| `player.cimtbl`, `schedule.cimtbl` | players and schedules, as load groups |
| `load.cimtbl`, `triplex_load.cimtbl`, `triplex_node.cimtbl` | loads |
| `capacitor.cimtbl` | `capacitor` |
| `inverter.cimtbl` | `inverter`, with the `solar` or `battery` it names |

A class with no records writes no part and no `Import`. Values keep the units the `.glm` used, and the unit sits in
the column header, for example `p (W)`. A comment above a row says what the importer defaulted. The per-property
rules are in the [import mapping](../CIMTBL_MAPPING.md); how a table is written is in the
[`.cimtbl` contract](https://pnnl-cim-tools.github.io/CIMHub/core/developer/cimtbl/).

## What is skipped, loudly

A GLM class no mapper reads is not an error. The master's comment lists it as `not mapped: <class> <count>`, so
nothing disappears silently. It covers the classes the schema knows but no mapper reads, and the object types the
reader does not know:

```
# GridLAB-D model t1
# Mapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#master
# not mapped: recorder 1
```

What the class would have configured is absent from the CIM network. [What converts](coverage.md) has the list.

## What raises

The reader and the importer fail rather than guess. Each message names the file and line, or the GLM object.

| Cause | What you get |
|---|---|
| The `.glm` is not there | `FileNotFoundError: GLM file not found: <path>` |
| A block with no `}`, or a last statement with no `;` | `GlmParseError` with file and line: `t3.glm:1: object 'object meter' is not closed` |
| A property the class does not have | `GlmParseError`: `t2.glm:1: meter has no property 'bogus'` |
| A `${NAME}` that nothing defines | `GlmParseError`: `macro ${VSOURCE} is not defined (pass it in defines=)` |
| A missing `#include` file or player file | `GlmParseError` for the include; `FileNotFoundError: player file not found: <path>` for the tape |
| A value that is not a boolean or an integer for its property | `GlmParseError: <class>.<property>: '<text>' is not an integer` |
| Two objects with one name | `GlmParseError: name 'x' is already used by the object at <file>:<line>` |
| A mapped property holds an expression | `ValueError: load l1 (t4.glm:2): constant_power_A is the expression 'LIGHTS*1.2', which no mapper reads yet` |
| A link whose `from` or `to` is not a bus object, a transformer with no `phases`, or `status OPEN` on a line, series reactor or regulator | `ValueError` naming the class and object, from the walk: `overhead_line l1: status OPEN on a device that is not a switch` |
| A link whose `from` or `to` names no object | `KeyError: "no object named 'zz'"` |
| A source voltage more than 10 % from the swing bus's `nominal_voltage` | `ValueError: substation 150: source voltage 66395.3 V (positive_sequence_voltage) is more than 10% from nominal_voltage 2401.78 V`. The `.glm` or the `defines=` is wrong: IEEE 123 needs `VSOURCE=2401.78`, IEEE 13 needs `66395.28` |
| A regulator with no `continuous_rating_<phase>` | `ValueError: regulator <name>: no continuous_rating_A; ratedS is the continuous rating x baseU`. GridLAB-D's 1000 A default is not the device's rating, so the importer does not use it |
| A transformer whose coil voltage does not fit the bus it sits on | `ValueError: Transformer 633-634: its coil on bus 634 gives 0.48 kV, but the island ... is 4.16 kV 3-phase` |
| A property a mapper classifies as raising when set | `ValueError` naming the object and property. Which ones are in the [import mapping](../CIMTBL_MAPPING.md) for each class |

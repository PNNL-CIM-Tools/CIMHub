# The importer

The importer takes a `GlmModel` and builds a cim18v17 network in two steps that never share objects: the mappers
turn GLM records into `.cimtbl` documents (text), and cimtables binds that text. The code is
[`importer/glm_to_cimtbl.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gridlabd/src/cimhub_gridlabd/importer/glm_to_cimtbl.py)
(the orchestrator), `importer/topology.py` (the bus walk) and one mapper per GLM class in
[`importer/cimtbl/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_gridlabd/src/cimhub_gridlabd/importer/cimtbl).
The design record for each class is [CIMTBL_MAPPING.md](../CIMTBL_MAPPING.md). The helpers every mapper uses
(`cell`, `mrid`, `Field`, `check_fields`, `untranscribed_values`) are core's, and are described on the core site's
[`.cimtbl` import contract](https://pnnl-cim-tools.github.io/CIMHub/core/developer/cimtbl/) page.

## The entry points

```python
import tempfile
from pathlib import Path

from cimtables.document import format_document
from cimhub_core.cimtbl_testing import cim_scope
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim

model = GlmReader("cimhub_gridlabd/tests/decks/IEEE/IEEE13_cdpsm.glm", defines={"VSOURCE": "66395.28"}).read_all()

documents = GlmImporter("IEEE13_cdpsm").to_cimtbl(model)      # pure: a DocumentSet, nothing written
print([part.name for part in documents.parts])
print(format_document(documents.master)[:200])

with cim_scope():                                              # puts back the CIM profile cimtables sets
    artifact_dir = Path(tempfile.mkdtemp(prefix="ieee13_artifact_"))    # a new, empty directory
    network = glm_to_cim(model, name="IEEE13_cdpsm", artifact_dir=artifact_dir)   # writes, then binds
    print(sorted(path.name for path in artifact_dir.iterdir())[:4])
```

The IEEE 13 deck's loads name a player, `ieeezipload`, that the GridAPPS-D run file declares and the deck does not. The
importer logs a warning for it (`1 player(s) named by loads are not in the deck ...`) and writes a load group for it
with no schedule.

| Call | Does |
|---|---|
| `GlmImporter(name, *, authority, substation, feeder, time_points)` | `name` is the master's `Model` and the file stem. `authority` defaults to `AUTHORITY` (`https://github.com/PNNL-CIM-Tools/CIMHub`). `substation` and `feeder` name the containers (`sub_<substation>`, `fdr_<feeder>`), each `name` unless given, so a model's scope and its container keys can differ. `time_points` is the caller's dict for the players' and schedules' points. |
| `.to_cimtbl(model)` | Returns the `DocumentSet`: master plus parts. No file is written. |
| `.to_cim(model, *, network=None, artifact_dir=None)` | The core `to_cim`: write the documents (to `artifact_dir`, else a temporary directory), load them with cimtables, bind onto `network` if given. Then it adds the points of the players and schedules to `time_points`. |
| `glm_to_cim(model, *, name, ..., time_points=None)` | Builds a `GlmImporter` and calls `to_cim`. |

The model's name must not equal a part's name: the master and the parts are written as `<name>.cimtbl` and
`<part>.cimtbl` in one directory, and core raises `document names repeat` for a model called `bus` or `series_reactor`.

### The time points step

A player's multipliers and a schedule's day profiles do not go in the artifact; they go to the caller's `time_points`
dict (the Parquet sidecar, which needs the `time-points` extra). After the core `to_cim`, `GlmImporter.to_cim` builds
`player.player_points(model)` and `schedule.schedule_points(model, load.references(model, players=False))`, keyed by
the uri of each bound schedule, and `cimhub_core.time_points.add_regular_time_points` adds them. With no points, nothing
happens. With points and no `time_points`, they are dropped with one warning that names them. See the core
[time points](https://pnnl-cim-tools.github.io/CIMHub/core/guide/time-points/) guide.

## to_cimtbl

`to_cimtbl` does these things, in this order:

1. `check_expressions(model, CLASSIFIED, load.EXPRESSION_SLOTS)` raises for any value the reader kept as an expression
   in a slot a mapper reads (not an `untranscribed` one), naming the object, its file and line, the slot and the
   text. The exception is the bases of the loads, which the load mapper reads as `<player>.value*K` itself.
2. `bus.check_bus_loads(model, CLASSIFIED)` raises when a node, meter or other bus object sets a load accumulator
   of its own (the slots `bus.py` marks `BUS_LOAD`): that load is not mapped.
3. `site(model, name, ...)` runs the topology walk once and returns a `Site` (a `NamedTuple`): the name, the walk's
   `buses`, each bus object's root bus (`roots`), the `substation` and `feeder` mRIDs and names, the
   `base_frequency` in Hz and the one-phase `services`.
4. `map_buses` makes `bus.cimtbl` and `map_source` makes `source.cimtbl`; `cimhub_core.load_response.zip_fractions()`
   makes the shared `zip_fractions.cimtbl`.
5. Each `(native class, mapper)` of `MAPPING_ORDER` is called as `mapper(model, site)` and returns one document.
6. Documents with no statements are dropped, and `map_master` makes the master, which `Import`s each remaining part in
   order.

`MAPPING_ORDER` is the `Import` order after `bus`, `source` and `zip_fractions`, and a class comes after what it
names: the three conductor catalogs, `line_spacing`, `line_configuration`, `triplex_line_configuration`,
`transformer_configuration`, the three line classes, the switching devices, `series_reactor`, `transformer`,
`regulator`, `player`, `schedule`, the load classes, `capacitor` and `inverter`. A lambda per entry passes each mapper
only what it needs from the `Site`. The players and schedules come before the loads because a load's group names
them.

`CLASSIFIED` maps every mapped native class to its `FIELDS`. The expression guard reads it, and so does the master: a
GLM class not in it is listed by count in the master's `not mapped:` comment, so nothing disappears silently. An
object type the schema lacks is in that list too, from `GlmModel.not_read`.

### The master

`map_master` writes the model's containers and its bases, then one `Import` per part, then the feeder head:

| Statement | Content |
|---|---|
| `Substation`, `Feeder` | `sub_<substation>` and `fdr_<feeder>`; the Feeder's `NormalEnergizingSubstation` is the Substation. |
| `BaseFrequency` | `module powerflow { nominal_frequency ...; }`, else `#set powerflow::nominal_frequency=...`, else 60 Hz with a `defaulted:` comment. |
| `BaseVoltage` | The walk's distinct bus voltages, highest first. |
| `OperationalLimitType` | `limit_types()`: the normal and emergency types every `CurrentLimit` names. |
| `Import` | One per non-empty part. |
| `Update Table Terminal` | Last, after the imports: `NormalHeadFeeder` on the Terminal of every link that touches a swing bus (`feeder_heads`: `<mRID>_T1` for its `from`, `_T2` for its `to`). A head on a link no mapper writes raises. |

### The topology walk

`importer/topology.py` builds a `cimtopology.core.Network` from the model, and `walk(network)` gives each bus its
nominal voltage and system (`BusSystem`). A spoke never writes its own graph walk (invariant I9).

| `Network` part | From the GLM model |
|---|---|
| `nodes` | Every root bus. A bus is any `node` or `triplex_node` subclass. A bus whose `parent` is a bus is solved by GridLAB-D as its parent's, so `bus_roots` maps it to the root of its parent chain (a parent that is no bus, or a loop, raises). |
| `sources` | Every `substation` and every bus with `bustype SWING`. Its kV is the system voltage of its `nominal_voltage` (phase to neutral) on the system its phases give (`line_voltage`). One and three phases only. `SWING_PQ` is a plain bus. |
| `branches` | Every line, switch, fuse, recloser, sectionalizer, series reactor and regulator. `status OPEN` on a switching device is a normally open branch; on any other class it raises. A link's phases (N and D aside) must be on both its end objects, as GridLAB-D requires (`check_end_phases`), except an open switch between laterals on different phases (`crossed_phases`). |
| `transformers` | One `Coil` per winding, from the `transformer_configuration` and its `connect_type` (`_transformer`). Whether a wye configuration's voltages rate the coil or the line is `coil_rated`; a one-phase service on 120 V or 240 V is split-phase (`service_phases`). |

```python
from cimtopology.core import walk
from cimhub_gridlabd.importer.topology import glm_network

buses = walk(glm_network(model))
print(len(buses), buses["611"])
```

Equipment voltages come from this walk, not from a `nominal_voltage` on the device. Voltages in the walk go through
`pint` (`topology.kv`), from the unit the value was written in.

## The mapper layout

Most mapper modules in `importer/cimtbl/` have these parts (the names in the first row and the second differ where a module maps several classes). Several classes share a module (`conductor.py`,
`configuration.py`, `line.py`, `switch.py`, `load.py`), and `catalog.py` and `link.py` are helpers, not mappers.

| Part | Role |
|---|---|
| `NATIVE_CLASS` | The schema class it maps (`schema.SeriesReactor`). A module that maps several lists them instead: `CATALOGS` (`conductor.py`), `LINES` (`line.py`) and `SWITCHES` (`switch.py`) are tuples of `(class, ...)`, `LOAD_CLASSES` (`load.py`) of `LoadClass`, `NATIVE_CLASSES` (`bus.py`) of classes. |
| `PREFIX` | The mRID prefix (`rx_`). An mRID is `mrid(PREFIX, name)`. `conductor.py` has one per class in `PREFIX`, `inverter.py` has `PREFIXES` for `solar` and `battery`. |
| `FIELDS` | `{slot: Field}`: every slot of the native class, classified. Most are built with `link.classify` or `bus.classify`, which raise on a slot nothing claims, so a schema regeneration that adds a slot fails at import time. |
| `map_<class>(model, ...)` | A pure function (`map_series_reactors`, `map_line_spacing`, `map_conductors`, ...): the model and the `Site`'s pieces (`roots`, `buses`, `feeder`) in, one `Document` out. An empty class returns a `Document` with no statements. |
| the provenance comment | `link.provenance(native, targets, count, anchor)`: what it maps, the record count and the spec anchor. |

`Field(kind, targets=(), note="")` is core's classification. `kind` is one of `copied`, `mapped`, `structural`,
`derived`, `untranscribed`. A `copied` field names its targets, `(cim_class, column, unit)`, and the unit can be the
placeholder `{unit}`, filled from the unit the value was written in. `untranscribed_values(FIELDS, record)` gives the
`# untranscribed: ...` comment for the untranscribed slots a record has set, so nothing is dropped silently.

The rules a mapper keeps:

- A value is copied as written, with its written unit in the column header: `Column("r", "ohm")`, the cell text
  from `cell(value)`. `glm_schema.registry_unit` respells GridLAB-D's names for the registry (`Ohm` to `ohm`).
  A quantity CIM has no attribute for goes through a named function and is marked `derived` in `FIELDS` and in a
  table comment (`percentImpedance` from a transformer's per unit R and X, `radius_from_diameter`).
- An unset property the mapper needs is a `defaulted:` comment or a raise; never a guess.
- A property the mapping does not cover raises when the model sets it, or is `untranscribed` with a reason.
- Ambiguity raises: unequal phases on a reactor, a per-phase switch state that differs, a winter rating that differs
  from its summer one.
- Error messages name the record with `catalog.label(record)` (`series_reactor x`) and the slot with
  `catalog.native_name(record, slot)`, which is the GLM property name, not the Python slot.

## One mapper end to end: series_reactor

[`series_reactor.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gridlabd/src/cimhub_gridlabd/importer/cimtbl/series_reactor.py)
maps `series_reactor` to a `SeriesCompensator`. GridLAB-D's reactor is one impedance per phase with no coupling
between phases; CIM's compensator is one r and x. The atom holds two reactors: `hsb`, on three phases with ratings,
and this one-phase one:

```text
object series_reactor { name r1; from rb1; to rb2; phases BN; phase_B_impedance 0.5+2j; }
```

```python
from cimtables.document import format_document
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.cimtbl.series_reactor import map_series_reactors
from cimhub_gridlabd.importer.glm_to_cimtbl import site

atom = GlmReader("cimhub_gridlabd/tests/atoms/series_reactor/series_reactor.glm").read_all()
walked = site(atom, "atom")
print(format_document(map_series_reactors(atom, walked.roots, walked.buses, walked.feeder)))
```

`map_series_reactors(model, roots, buses, feeder)`, for each reactor:

1. `_phases` takes the A, B, C letters of `phases`; any other letter than N, or none, raises.
2. `_impedance` raises when a `phase_X_resistance` or `phase_X_reactance` is set (only `phase_X_impedance` is mapped),
   when a phase the reactor has is unset (GridLAB-D's 0 is a switch stand-in), or when the phases differ in value or
   unit. It returns the one `r + jx` and its unit.
3. `link.ends` gives the root buses of `from` and `to` and the `BusSystem` of the first, whose `base_voltage` is
   the equipment's.
4. The row is `rx_<name>`, the name, the two nodes, `r`, `x`, and `r0 = r`, `x0 = x` (no coupling), the BaseVoltage and
   the `untranscribed:` comment. The columns carry the unit the impedance was written in, so the header is `r (ohm)`.
   One `Table` is written per unit.
5. A reactor on fewer than three phases gets an `Update Table Terminal` row per Terminal with its phases
   (`rx_r1_T1`, `rx_r1_T2`), since `SeriesCompensator` has no per-phase class.
6. `Limits.add(compensator, link_ratings(reactor))` writes the `OperationalLimitSet` and its `CurrentLimit`s from the
   `continuous_rating_X` and `emergency_rating_X` slots; phases that differ raise.

The result is the golden `tests/atoms/series_reactor/series_reactor.series_reactor.cimtbl` (the file also starts with
the provenance comments and ends with `OperationalLimitSet` and `CurrentLimit` rows for `hsb`, the reactor with ratings):

```text
Table SeriesCompensator: mRID, name, node1, node2, r (ohm), x (ohm), r0 (ohm), x0 (ohm), BaseVoltage, EquipmentContainer=fdr_atom
    rx_hsb, hsb, n2,  rb1, 0.0, 14.798307, 0.0, 14.798307, bv_4p16kv
    rx_r1,  r1,  rb1, rb2, 0.5, 2.0,       0.5, 2.0,       bv_4p16kv

Update Table Terminal: mRID, phases
    rx_r1_T1, B
    rx_r1_T2, B
```

The classification is checked by a test, and so is each fail-fast rule:

```python
from cimhub_core.cimtbl import check_fields
from cimhub_gridlabd.importer.cimtbl import series_reactor

check_fields(series_reactor.FIELDS, series_reactor.NATIVE_CLASS)   # raises AssertionError listing missing and stale slots
```

## Adding a mapper for a new GLM class

1. **Spec first.** Add a section to [CIMTBL_MAPPING.md](../CIMTBL_MAPPING.md): every property of the class classified,
   the CIM class and shape it becomes, the mRID prefix, the fail-fast rules and the expected differences. A mapper
   without an approved section is not merged.
2. **The mapper.** Start from a module of the same shape (`series_reactor.py` for a link, `capacitor.py` for a device
   on a bus). `cimhub_core.scaffold.scaffold_mapper("gridlabd", schema.Foo, prefix="foo_")` writes the stub and the
   completeness test, but its `map_foo(native)` takes one argument and the GLM mappers take the model and the
   `Site`'s pieces. Fill `FIELDS` from the spec (`link.classify` for a link, so the shared slots are claimed once),
   then write `map_foo(model, roots, buses, feeder)` returning a `Document`. Pick the table shape from core's
   [canonical shapes](https://pnnl-cim-tools.github.io/CIMHub/core/developer/shapes/).
3. **The order.** Add `(foo.NATIVE_CLASS, lambda model, site: foo.map_foo(model, site.roots, site.buses, site.feeder))`
   to `MAPPING_ORDER`, after every class its rows reference, and `NATIVE_CLASS: foo.FIELDS` to `CLASSIFIED`. A link
   class goes in `LINK_PREFIXES` too, so `feeder_heads` finds its Terminals. The guard raises on an expression in any
   slot the mapper reads. A mapper that reads an expression itself (the loads read `<player>.value*K`) has to be
   named in the guard's `read_by_mapper` argument, which `to_cimtbl` passes as `load.EXPRESSION_SLOTS`.
4. **The writer.** If the class is new to the writer, add it to `WRITE_ORDER` in `glm_writer.py`, after the classes it
   names, and to the exporter (see [The exporter](exporter.md)).
5. **The atom pair.** Add `tests/atoms/<table>/<case>.glm` (a few lines from a public deck, with its origin in a
   comment) and the reviewed `<case>.<table>.cimtbl` golden.
6. **The tests.** `tests/test_cimtbl_<table>.py`: `check_fields`, the golden (`assert_matches_golden`), the binding under
   cim18v17 with key values checked through the core getters in SI, each fail-fast rule with
   `pytest.raises(ValueError, match=...)`, and GridLAB-D as the oracle where it computes the same quantity. If the
   sweep should check the new class on every deck, add an `assert_gridlabd_*` function and call it from
   `assert_binds_as_gridlabd_runs_it` in `test_cimtbl_sweep.py`. [Testing](testing.md) lists the helpers.
7. **The golden directory.** If the IEEE13_cdpsm deck has the class, regenerate with `CIMHUB_UPDATE_GOLDENS=1` and
   review the diff in `tests/goldens/IEEE13_cdpsm/`.
8. Run `scripts/test-all.sh gridlabd` and `scripts/leak-gate.sh`.

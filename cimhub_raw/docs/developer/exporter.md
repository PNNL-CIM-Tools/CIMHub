# The exporter

The exporter reads a cim18v17 network and returns a `GraphModel` of RAW records, the same kind of model
`Raw34Reader.read_all()` returns, so `Raw34Writer` writes it and the reader and importer read it back. It does no file
I/O. The code is
[`exporter/cim_to_raw.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/exporter/cim_to_raw.py)
and one module per RAW table beside it. The design record, with a slot table per record class, is
[EXPORT_MAPPING.md](../EXPORT_MAPPING.md).

## The entry points

```python
import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl_testing import cim_scope
from cimhub_raw.exporter.cim_to_raw import RawExporter, cim_to_raw
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.raw34_writer import Raw34Writer

with cim_scope():
    native = Raw34Reader("cimhub_raw/tests/cases/IEEE14/IEEE_14_bus.raw").read_all()
    network = raw_to_cim(native, name="IEEE14")

    exported = RawExporter().to_model(network)                     # a GraphModel, nothing written
    print(sorted(cls.__name__ for cls in exported.graph if exported.count(cls))[:4])
    print(Raw34Writer().serialize(exported.list_by_class(schema.FixedShuntRecord)[0]))   # 9,'1 ',1,0.000,19.000

    cim_to_raw(network, "/tmp/ieee14_export.raw")                  # to_model, then Raw34Writer.write
```

| Call | Does |
|---|---|
| `RawExporter().to_model(network)` | Returns the `GraphModel`. It has no options: the names and numbers come from the mRIDs the importer wrote. |
| `cim_to_raw(network, destination)` | `RawExporter().to_model(network)`, then `Raw34Writer().write(model, destination)`. |
| `export_tables(network, modules)` | The records of the given modules only, each with its composite ID. The tests use it to export one table at a time. |
| `export_context(network)` | The `ExportContext` the modules share, for a test or a script. |

## to_model

`to_model` does these things, in this order:

1. `_check_exported(network)` raises `no RAW export yet for {...}` (with the class names and counts) for any
   `ConductingEquipment` class no module lists in its `CIM_CLASSES`, so nothing is dropped silently. A DC line's
   `CsConverter`s and `VsConverter`s, and a FACTS device's `StaticSynchronousCompensator`, raise here.
2. `export_tables(network, EXPORT_ORDER)` builds the `ExportContext` once.
3. For each module in `EXPORT_ORDER`, `module.export(context)` returns RAW records; each gets its composite ID from
   `composite_id.assign_composite_id` and is added to a new `GraphModel`.

`EXPORT_ORDER` is: case identification, zone, area interchange, bus, branch, switch, multi-section line, load, fixed
shunt, switched shunt, generator, transformer, impedance correction. A module may import another's helpers (the
transformer module reads the generator module's `step_ups`, so a machine's step-up is not also written as a
transformer), but the order is also the order of the records in the model, and so of the sections in the file.

### The module contract

Each module has:

| Name | Holds |
|---|---|
| `NATIVE_CLASS` | The RAW record class it writes (`schema.FixedShuntRecord`). |
| `CIM_CLASSES` | The `ConductingEquipment` classes it exports, which `_check_exported` collects. A table with no equipment of its own (zone, area, multi-section line, impedance correction, case identification) has `()`. |
| `SLOTS` | `{NATIVE_CLASS: {slot: Slot}}`: what the module does with every slot of the record. |
| `export(context)` | The records, a list sorted by key, over the whole network. |

A module works over the whole network, not object by object, because IDs are allocated per bus and a bus's AREA is a
trace.

### ExportContext

`ExportContext` is a `NamedTuple` made once by `export_context(network)`:

| Field | Holds |
|---|---|
| `network` | The CIM network. `context.objects(*cim_classes)` returns its objects of those classes, class by class. |
| `bus_numbers` | `TopologicalNode` to its bus number, from `busNumber`. A node without one is internal to a device (a machine behind its step-up) and is left out, with one info log with the count. |
| `zone_numbers`, `area_numbers` | `SubGeographicalRegion` to its zone number and `ControlArea` to its area number. |
| `bus_areas` | `TopologicalNode` to its `ControlArea`, or `None` when the trace cannot reach it. |
| `branch_ratings_in_current` | NXFRAT: the branch and switch ratings are `CurrentLimit`s. |
| `transformer_ratings_in_current` | XFRRAT: the transformer ratings are `CurrentLimit`s. |

## Identity and names: identity.py

[`identity.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/exporter/identity.py)
turns the importer's mRIDs back into RAW numbers, IDs and names. The importer's mRID prefix of each table is imported
from the importer's module, so the two directions cannot drift.

| Function | Does |
|---|---|
| `bus_numbers(nodes)` | Each numbered node's `busNumber`. A number used twice, or no numbered node at all, raises. |
| `keyed_numbers(objects, prefix)` | Each object's number from its mRID `<prefix><n>` (`srgn_3`, `ca_1`). An object whose mRID is not of that form gets the next number above the largest taken, in mRID order, with an info log of the count. This is one of the two documented fallbacks. Two mRIDs giving one number raise. |
| `terminal_buses(device, context)` | The bus number at each of the device's terminals, in `sequenceNumber` order. A terminal on a node with no number raises. |
| `keyed_ids(devices, width, fallback_prefix="")` | Each device's ID, for `(device, mRID prefix, buses in order)`: the rest of `<prefix><bus>_<bus>_..._<ID>` when it fits `width`, else the next free `1`, `2`, ... among the devices on the same buses (RAW's key), with an info log. The second documented fallback. Two devices with one key raise. |
| `raw_name(obj, key, width)` | The NAME: blank when unset or equal to `key` (the importer's blank-NAME form), else the name; a name longer than `width` raises. |

## The area trace: area_trace.py

CIM 18 has no association from a node to a `ControlArea`, so the importer records an area through what CIM already
places in one: generating units and tie flows. `trace_areas(network)` recovers each bus's AREA the same way:

- Seeds: the node of every `SynchronousMachine` and `PowerElectronicsConnection`, with its unit's `ControlArea`; a
  `TieFlow` pair's terminal, with the pair's `positiveFlowIn = false` area, and the other terminals of that device, with
  the pair's `true` (home) area.
- The areas spread across every device with two or more nodes and no `TieFlow` (`topology.islands`, shared with the
  importer).
- Two areas meeting in one island raise. A node in an island with no seed gets `None`; the importer wrote the AREA on
  that bus's row as `untranscribed`, and the exporter writes it blank.

`metered_terminal(device)` returns the `sequenceNumber` of the terminal holding a device's `TieFlow` pair, which is its
metered end (MET); pairs on two terminals raise. The importer's `untraced_area_buses` runs the same rule over the RAW
records, so the two stay together.

## Ratings: ratings.py

RATE1..RATE12 are the limits whose type has the importer's mRID `olt_rate<n>`. `device_limits` returns a device's kind
(`ApparentPowerLimit`, `CurrentLimit` or none) and its limits by type, through `get_limits_by_type`; a device holding
both kinds raises. `device_ratings(device, terminal=None)` gives the twelve values, 0 where there is no limit; a current
is converted to MVA with `rating_from_ka` on the device's BaseVoltage (a transformer's, per winding, on that winding's
terminal). `ratings_in_current(devices, per_terminal=False)` decides NXFRAT and XFRRAT for the case: both kinds among
the devices raise, because RAW's flag is one or the other.

## Reading CIM: only through the core getters

An exporter never reads a CIM attribute for a quantity itself. Every value comes through one of:

- a `cimhub_core.getters` function, which resolves units, bases and the CIM shape that holds the concept (a line's
  impedance, a transformer's windings, a tap changer's steps, a shunt's admittance, a regulating control, a node's
  solved voltage, a limit set);
- `cimtables.graph_write.get_qty(obj, attribute, unit)`, which reads one attribute in the unit asked for
  (`get_qty(area, "pTolerance", "MW")`).

The unit is always asked for, never converted by hand. A RAW per unit value is then a named inverse from
`importer/cimtbl/derived.py` (`per_unit_from_kv`, `mva_from_per_unit`, `rating_from_ka`), so a formula is stated once.
`exporter/shunt_admittance.py` wraps `get_shunt_admittance` so that a shunt's g and b come out in pu on its bus's
base, which is how RAW states every shunt; a shunt rated off its bus voltage raises. The getters are described in core's
[getter guide](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/) and
[reference](https://pnnl-cim-tools.github.io/CIMHub/core/reference/); a missing getter is a request to the core owner,
not a local reimplementation.

## SLOTS

`SLOTS` is the exporter's mirror of the importer's `FIELDS`: every slot of the RAW record, with what the module does
with it. A `cimhub_core.export_slots.Slot(kind, note)` has one of four kinds:

| Kind | Meaning |
|---|---|
| `written` | The value comes from a getter. |
| `rule` | A fixed or computed value RAW needs (IC 0, REV 34, ST from `inService`, IDE from the machines). |
| `unset` | CIM cannot hold it. The slot is `None` and written blank, so PSS/E applies its default. Everything the importer marks untranscribed is `unset` here, unless the spec recovers it (the bus AREA). |
| `not mapped` | A form of the same data that is not written. |

`check_slots(SLOTS[NATIVE_CLASS], NATIVE_CLASS)` raises when a slot of the record is missing from the dict, or a key is
not a slot, or a kind is unknown. `test_slots_are_complete` runs it for every module in `EXPORT_ORDER`, and
`test_untranscribed_on_import_is_unset_on_export` checks the importer's untranscribed fields against the exporter's
`unset` slots.

The slot tables in EXPORT_MAPPING.md (`### Slots (generated from SLOTS)`) are the output of
`slots_table(slots, "RAW")` from `cimhub_core.export_slots`. No test or script in this package regenerates them, so
when a note in `SLOTS` changes, render the table and update the spec by hand.

## One module end to end: fixed_shunt

[`fixed_shunt.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/exporter/fixed_shunt.py)
writes a `LinearShuntCompensator` with no control as a Fixed shunt. A shunt with a `RegulatingControl` is a
switched-shunt block, and a branch's line shunt is that branch's GI, BI, GJ and BJ, so the module has to tell them
apart.

```python
from cimhub_raw.exporter import fixed_shunt

for slot, how in fixed_shunt.SLOTS[fixed_shunt.NATIVE_CLASS].items():
    print(slot, how.kind, "-", how.note)
```

`export(context)`:

1. `branch.line_shunts(context)` returns the shunts that belong to a branch: those whose mRID is `cap_<key>_i` or
   `_j` for a branch `ln_<key>` or `sc_<key>` and that sit on that end's bus. They are left out here.
2. The remaining shunts with no `RegulatingControl` are collected with `terminal_buses(shunt, context)`.
3. `keyed_ids(..., ID_WIDTH)` gives each its ID: the rest of `cap_<bus>_<ID>`, else the next free one on the bus.
4. For each, `bus_base_admittance(shunt, "actual", base_power)` gives g and b in pu on the bus's base, and
   `mva_from_per_unit(g, base_mva)` makes them GL (MW) and BL (Mvar) at one per unit voltage. STATUS is 0 when
   `get_in_service(shunt, which="actual")` is false, else 1.
5. The records are sorted by `(bus_number, shunt_id)`.

The round trip checks it: `test_round_trip` reads each fixture, imports it, exports it and compares every slot not marked
`unset` of every module with the original, so GL and BL come back as they went in.

## Adding an exporter module

1. **Spec first.** Add a section to [EXPORT_MAPPING.md](../EXPORT_MAPPING.md): which CIM classes become the record,
   which getter gives each slot, the keys and names, the fail-fast rules and the expected differences from the original
   case.
2. **The module.** Create `exporter/<table>.py` with `NATIVE_CLASS`, `CIM_CLASSES`, `SLOTS` and
   `export(context)`. List every slot of the record in `SLOTS` (`cimhub_core.export_slots.with_default` fills the rest
   with one kind). Read through the getters and `get_qty`, take the importer's prefix and derived functions rather than
   restating them, and use `keyed_ids` and `terminal_buses` for IDs and buses. Raise on what RAW cannot hold; never
   write a guessed value.
3. **The order.** Add the module to `EXPORT_ORDER` in `cim_to_raw.py`, after any module it imports helpers from. Its
   `CIM_CLASSES` stop `_check_exported` from raising for that equipment.
4. **The tests.** In `tests/test_cim_to_raw.py`: add the module to the chain of `E<n>_MODULES` tuples that ends in
   `LANDED` (so `test_round_trip` and `test_written_case_reads_back` cover it), and a test for each fail-fast rule with `pytest.raises(ValueError,
   match=...)`. Differences that are expected by design go in `EXPECTED`, with the reason. Add the module and its importer to the
   parameters of `test_untranscribed_on_import_is_unset_on_export`; a slot that is written although the importer lists
   the field untranscribed goes in `NOT_UNSET`.
5. **The slot table.** Render `slots_table(SLOTS[NATIVE_CLASS], "RAW")` into the spec's `### Slots` section.
6. Run `scripts/test-all.sh raw` and `scripts/leak-gate.sh`.

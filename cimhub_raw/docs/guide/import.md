# Import: RAW to CIM

```python
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader

model = Raw34Reader("cimhub_raw/tests/cases/IEEE14/IEEE_14_bus.raw").read_all()
network = raw_to_cim(model, name="IEEE14", artifact_dir="artifacts/IEEE14")
```

`network` is a cim18v17 cim-graph `BusBranchModel`. `artifact_dir` keeps the `.cimtbl` text it was built from.

## What happens

1. `Raw34Reader(path).read_all()` parses the `.raw` and returns a `GraphModel` of typed records, one class per RAW
   table.
2. `RawImporter(name).to_cimtbl(model)` works out the case-wide facts once (the system base, each bus's zone, area
   and base voltage, the substations), then runs one mapper per RAW table. Each mapper turns records into a `.cimtbl`
   document. It does not build CIM objects.
3. `raw_to_cim` writes the documents and cimtables binds them into a network.

The `.cimtbl` text is the only input to CIM. If a value is wrong in the network, it is wrong in the text, and you can
read it there.

## Reading a `.raw`

`Raw34Reader(source)` takes the path of the `.raw`. `read_all()` reads the file once and returns the same model on
later calls. It raises `FileNotFoundError` if the file is missing, `Raw34ParseError` for anything it cannot read as
v34, and `NotImplementedError` for a populated multi-terminal DC or GNE section.

The file is read by position, in the order RAW v34 fixes:

| Part of the file | What the reader does |
|---|---|
| first line | `IC, SBASE, REV, XFRRAT, NXFRAT, BASFRQ`. A REV other than 34 raises: `REV is 33.0; this reader reads RAW v34 only` |
| two title lines | Kept as written, in `titles` |
| system-wide data | `GENERAL`, `GAUSS`, `NEWTON`, `ADJUST`, `TYSL` and `SOLVER` records are kept as text, each at most once. A `RATING` record names a rating set. Any other keyword raises: `unknown system-wide data record 'SOLVERX'` |
| sections | Bus, load, fixed shunt, generator, branch, system switching device, transformer, area, two-terminal DC, VSC DC line, impedance correction, multi-terminal DC, multi-section line, zone, inter-area transfer, owner, FACTS device, switched shunt, GNE and induction machine, then the substation section. Each ends with a record whose first field is `0`; the text after it (`/ END OF BUS DATA, BEGIN LOAD DATA`) is a comment |
| substation section | One block per substation: its record, its nodes, its switching devices, its equipment terminals, each part ended by its own `0` record |
| `Q` | Ends the data. Every later section is empty |

Rules that matter when a case does not read as you expect:

- **Fields** are separated by a comma or by blanks. Two commas in a row leave a field blank, and a record may stop
  early. A blank or missing field is `None` in the record.
- **Comments.** A line that starts with `@!` is skipped. An unquoted `/` starts a comment that runs to the end of the
  line. A quoted field may hold commas, blanks and slashes.
- **Names** lose their trailing blanks. A bus is `'BUS 1       '` in the file and `BUS 1` in the record.
- **Extended bus names.** A quoted value in an integer field is an extended bus name, `'NAME        kV'`: the 12-character
  bus name, then its base kV. The reader resolves it to the bus number, so every bus reference in the model is a number.
  A leading `-` gives the negated number. A name that matches no bus, or two, raises.
- **Keys.** Every record has a key built from its own fields, for example `10_1` for the load with ID `1` on bus 10. A
  second record with the same key raises: `duplicate BranchRecord '1_2_1' (first on line <n>)`.
- **A parse error** names the file and line, and shows the line: `case.raw:2: REV is 33.0; this reader reads RAW v34 only`.
- **Multi-terminal DC and GNE.** A case that has records in either section raises `NotImplementedError` as soon as it
  is read. Induction machine records are read, but the importer raises on them (below).

The reader does not fill defaults. A blank field stays `None` in the record, and the importer fills it from the schema's
default when it maps the record.

## Options

`raw_to_cim(model, *, name, authority=..., network=None, artifact_dir=None)`.
`RawImporter(name, *, authority=...)` takes the same keywords except `network` and `artifact_dir`, which go to its
`to_cim` method.

| Argument | Meaning |
|---|---|
| `name` | Required. The master document's `Model` and file stem, and the name of the case's `GeographicalRegion` (its mRID is `rgn_` and the name in lower case). Do not use the name of a part file (`bus`, `load`, `zone`, ...): document names must be distinct, so the importer raises `document names repeat: ['bus']`. |
| `artifact_dir` | Keep the `.cimtbl` files here. Without it they go to a temporary directory that is removed after loading. |
| `network` | An existing cim18v17 network to bind onto, to merge several models. |
| `authority` | The master's `Authority`. Defaults to `https://github.com/PNNL-CIM-Tools/CIMHub`. |

To get the documents without binding them, call `RawImporter(name).to_cimtbl(model)`. It returns a `DocumentSet` with a
`master` and a list of `parts`, and touches no files.

## The artifacts

`artifact_dir` holds the master, `<name>.cimtbl`, and one file per RAW table the case has records in. A table with no
records writes no file and no `Import`. The master `Import`s the files in this order, so that a catalog comes before
what uses it. The IEEE 14-bus case writes `zone`, `area_interchange`, `bus`, `branch`, `load`, `fixed_shunt`,
`generator` and `transformer`.

| Part file | From |
|---|---|
| `zone.cimtbl` | zone records (and a zone a bus names that has no record) |
| `area_interchange.cimtbl` | area records, with the inter-area transfers listed in a comment |
| `bus.cimtbl` | buses: substations, nodes, busbars, voltage limits, solved voltages |
| `substation.cimtbl` | SUBSTATION blocks: nodes, switching devices |
| `branch.cimtbl` | non-transformer branches, series capacitors, line shunts |
| `switch.cimtbl` | system switching devices |
| `multi_section_line.cimtbl` | multi-section lines |
| `load.cimtbl` | loads |
| `fixed_shunt.cimtbl` | fixed shunts |
| `generator.cimtbl` | generators, with their plant controls and step-up transformers |
| `impedance_correction.cimtbl` | impedance correction tables |
| `transformer.cimtbl` | two- and three-winding transformers |
| `two_terminal_dc.cimtbl` | two-terminal DC lines |
| `vsc_dc.cimtbl` | VSC DC lines |
| `facts_device.cimtbl` | FACTS devices |
| `switched_shunt.cimtbl` | switched shunts. It follows the generators and FACTS devices because a shunt can regulate their reactive power |
| `equipment_terminal.cimtbl` | equipment terminals of the SUBSTATION blocks. It comes last, after every equipment file |

Owner records have no file: CIM 18 has no home for them, and the master's comment lists their count
(`untranscribed: Owner 1`).

Read the files the way you would a table. This is the head of IEEE 14's `branch.cimtbl`:

```
Table ACLineSegment: mRID, name, bus1, bus2, r (pu system), x (pu system), bch (pu system), length (km), inService, BaseVoltage, EquipmentContainer
    ln_1_2_1,   1_2_1,   1,  2,  0.01938, 0.05917, 0.0528, , true, bv_138kv,
    ln_1_5_1,   1_5_1,   1,  5,  0.05403, 0.22304, 0.0492, , true, bv_138kv,
```

A comment above a table lists what the importer left out (`# untranscribed: o1, f1, ...`) and above a row what it
defaulted (`# defaulted: wmod=0, wpf=1.0, nreg=0`). The master's comment lists every RAW class no mapper reads, as
`not mapped: <class> <count>`, so nothing disappears silently.

## The system base

The master's first object is `BasePower`, copied from SBASE in MVA. Every column headed `(pu system)` is a value copied
in per unit on that base, and cimtables converts it to ohms or siemens when it binds the network. The importer does no unit
arithmetic. A blank SBASE is 100 MVA, and the master says so: `defaulted: SBASE=100`.

| Master object | From |
|---|---|
| `BasePower` | SBASE |
| `BaseFrequency` | BASFRQ. A blank is 60 Hz, marked `defaulted: BASFRQ=60` |
| `GeographicalRegion` | the case: its name is `name` |
| `BaseVoltage` | one per distinct BASKV, highest first, named like `bv_138kv` and `bv_13p8kv` |
| `OperationalLimitType` | the four bus voltage-limit types, then the twelve rating sets `olt_rate1` to `olt_rate12`, named by the `RATING` records (else `RATE1`, `RATING SET 1`) |

NXFRAT and XFRRAT say what a branch's and a transformer's RATEn are: at 0 or below, MVA (an `ApparentPowerLimit`); above 0,
a current expressed as MVA (a `CurrentLimit` in kA). A blank is MVA, and the master says `defaulted: NXFRAT=0` or
`defaulted: XFRRAT=0`.

## Buses, substations and node-breaker data

Every bus is a `TopologicalNode` whose mRID is its bus number and whose `name` is its NAME, with a `BusbarSection` that holds its voltage limits and its
solved voltage (VM times BASKV, and VA). Every bus is also in a `Substation`. Buses that equipment inside a substation
joins share one, never across a zone boundary:

- every system switching device;
- a zero-impedance branch, R = 0 and |X| at most THRSHZ (from the `GENERAL` record, default 0.0001);
- a branch whose CKT starts with `@` or `*`;
- a series capacitor, X below 0;
- every transformer, all of its windings' buses.

The substation is named `sub_` and its lowest bus number. IEEE 14 has 11 substations, two of them of several buses:
4, 7 and 9, and 5 and 6. Its `bus.cimtbl` lists the buses and the equipment that merged them.

A SUBSTATION block (node-breaker data) takes precedence. It joins every bus its nodes name into one substation `sub_s<IS>`,
and each node is a `ConnectivityNode` `sub_s<IS>_n<NI>` inside its bus's `TopologicalNode`. The block's switching devices
become `Switch`, `Breaker` or `Disconnector` by their type, and its equipment terminals place each piece of equipment on
a node. The IEEE 118 case has four such substations. A block that is split across two zones, a node on no bus, a node
number given twice in a block, or a bus in two blocks raises.

A bus's AREA has no place in CIM, so the importer records it through what CIM can hold: generating units and the tie
flows of equipment between two areas. A bus that no generator or tie reaches is listed on its row as
`untranscribed: area=<AREA>`, and its AREA comes back blank on [export](export.md).

## What raises

| Case holds | Result |
|---|---|
| IC other than 0 (a change case) | `ValueError`: only a base case maps |
| no buses | `ValueError: the RAW model has no buses` |
| a BASKV that is blank or 0 or below | `ValueError: bus 1: BASKV=None is no base voltage` |
| multi-terminal DC records | `NotImplementedError` from the reader |
| GNE device records | `NotImplementedError` from the reader |
| induction machine records | `NotImplementedError` from the importer: `RAW InductionMachineRecord: 1 record(s), but the table is phase 2 and not mapped yet` |
| a generator with WMOD 4 | `NotImplementedError` |
| a FACTS device with a series element (J other than 0) | `NotImplementedError` |
| a load or generator in an AREA with no area record | `ValueError`: `AREA 5 has no area-interchange record` |
| an unmapped code (a switching device with a blank or unknown STYPE, ...) | `ValueError` naming the record, the field and the known values |
| a series capacitor (X below 0) with B other than 0 | `ValueError` |
| a plant whose generators disagree on VS, IREG or RMPCT | `ValueError` naming both IDs |
| a generator with WMOD 3 that shares its bus with another generator record | `NotImplementedError` |
| a swing bus whose only generator records are converter-interfaced (WMOD 1 to 3) | `ValueError` |
| a remote IREG from a swing bus | `ValueError` |
| a multi-section line whose dummy buses do not have exactly two branches | `ValueError` |
| a two-terminal DC line whose IF/IT name an AC transformer, or with a commutating capacitor (XCAP) | `NotImplementedError` |
| a two-terminal DC line with no bridges (NB below 1) or no valve-side voltage (EBAS x TR not above 0) | `ValueError` |

Every message names the record, by its key, so you can find it in the file. The multi-terminal DC, GNE and induction
machine tables are the only tables with no mapping at all. The
[conversion reference](../reference/index.md) lists the rest of each table's rules, and [What converts](coverage.md)
what each RAW table becomes.

A branch, transformer or other record that names a bus that is not in the case is not checked by the reader. Check your
case's references before you import it: the importer's first failure may be a bare `KeyError` on the bus number.

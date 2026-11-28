# Reader and writer

`Raw34Reader` reads a PSS/E RAW v34 file into a `GraphModel` of the schema's record dataclasses; `Raw34Writer` writes
such a model back. The two walk the same positional layout (`record_layout.py`), so they cannot disagree about where
a field sits. These are the only classes in the package that touch a `.raw` file. The code is
[`raw34_reader.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/raw34_reader.py),
[`raw34_writer.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/raw34_writer.py)
and
[`record_layout.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/record_layout.py).

```python
import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.raw34_reader import Raw34Reader
from cimhub_raw.raw34_writer import Raw34Writer

model = Raw34Reader("cimhub_raw/tests/cases/IEEE14/IEEE_14_bus.raw").read_all()
print(model.count(schema.BusRecord), model.count(schema.BranchRecord))      # 14 17
load = model.list_by_class(schema.LoadRecord)[0]
print(load.ID, load.constant_real_power, load.constant_imag_power)          # 10_1 9.0 5.8

Raw34Writer().write(model, "/tmp/ieee14_out.raw")
print(Raw34Writer().serialize(load))                                        # 10,'1 ',1,1,1,9.000,5.800,...
```

## Raw34Reader

`Raw34Reader(source)` binds a path without reading it. `read_all()` reads the file once and returns the same
`GraphModel` on every later call. The parsing is in a private class, `_FileReader`, made for one read of one file: its
lines, a table of bus names for extended bus names, and the line each key was first seen on. A missing file raises
`FileNotFoundError`.

### Sections

The sections are positional. After the case identification and the system-wide data, `SECTIONS` lists the twenty
sections in the v34 file order, each as the name used in the end-of-section comments and its record class:

| Order | Section | Record class |
|---|---|---|
| 1-7 | BUS, LOAD, FIXED SHUNT, GENERATOR, BRANCH, SYSTEM SWITCHING DEVICE, TRANSFORMER | `BusRecord`, `LoadRecord`, `FixedShuntRecord`, `GeneratorRecord`, `BranchRecord`, `SwitchRecord`, `TransformerRecord` |
| 8-12 | AREA, TWO-TERMINAL DC, VSC DC LINE, IMPEDANCE CORRECTION, MULTI-TERMINAL DC | `AreaInterchangeRecord`, `TwoTerminalDCRecord`, `VscDcRecord`, `ImpedanceCorrectionRecord`, `MultiTerminalDCRecord` |
| 13-17 | MULTI-SECTION LINE, ZONE, INTER-AREA TRANSFER, OWNER, FACTS DEVICE | `MultiSectionLineRecord`, `ZoneRecord`, `InterareaTransferRecord`, `OwnerRecord`, `FactsDeviceRecord` |
| 18-20 | SWITCHED SHUNT, GNE, INDUCTION MACHINE | `SwitchedShuntRecord`, `GneDeviceRecord`, `InductionMachineRecord` |

The SUBSTATION section (nested blocks) follows and is read by `_read_substations`. The comment text after a section's
`0` is not read: only the position matters, and a section is empty when its first record is the `0`. A section whose
terminator is missing raises (`the file ends inside the BUS section (no 0 record)`).

`@!` lines are comments and are skipped everywhere except the two title lines, which `next_line(verbatim=True)` reads
as they are. The case identification record is the first non-comment line; its REV must be 34 or the read raises
(`REV is 33.0; this reader reads RAW v34 only`).

The system-wide records follow the titles and run up to a `0`. `RATING` records become `RatingRecord`s in the case's
`ratings` list. The keywords in `SYSTEM_WIDE_KEYWORDS` (`GENERAL`, `GAUSS`, `NEWTON`, `ADJUST`, `TYSL`, `SOLVER`) are
kept as their text in the slot of the same lower-case name (`case.general`); a keyword given twice, or any other
keyword, raises.

A `Q` record ends the data. The reader sets `ended`, every later section is empty, and what follows `Q` is not read.
A `Q` inside a multi-line record, or before an impedance correction table's last point, raises.

### Tokens and quoting

`tokenize(text)` splits one record line into `Token`s (a `str` with a `quoted` flag), or `None` for a blank field:

```python
from cimhub_raw.raw34_reader import tokenize

print(tokenize("1,'A, B',,3 / comment"))     # ['1', 'A, B', None, '3']
```

- Fields are separated by a comma or by blanks. Two commas in a row, or a comma at the start, make a blank field.
- A quoted field (`'...'` or `"..."`) may hold commas, blanks and a `/`. An unclosed quote raises `ValueError`, which
  `_tokens` turns into a `Raw34ParseError`.
- An unquoted `/` starts a comment that runs to the end of the line. This is how `0 / END OF BUS DATA, BEGIN LOAD
  DATA` reads as the one token `0`.
- A section ends at a record whose first token is a bare `0` (`_is_terminator`): a quoted `'0'` is a name.

### Fields and the layout

A record is a sequence of lines, each a tuple of `Slot`s. `record_layout.record_lines(record_class)` builds them from
the schema annotations (see [The LinkML schema](schema.md)) and caches the result:

```python
import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.record_layout import line_count, record_lines

for line in record_lines(schema.TransformerRecord):
    print(len(line), line[0].name)          # five lines (22, 11, 27, 27, 27 slots); the first slot of each
print(line_count(schema.TransformerRecord, {"k": 0}))     # 4: no third winding
```

| Function | Does |
|---|---|
| `Slot(name, value_type, count, annotations)` | One field position. `value_type` is `int`, `float` or `string`. `count` is 1 for a scalar and the list length for a fixed-size list (`RATE1`..`RATE12`, `count` 12), which fills that many positions. |
| `record_lines(record_class)` | The record's lines in field order. A slot without an `order`, or marked `structural`, is not a field of the record text and is left out. Two slots with one `order` on a line raise. |
| `line_count(record_class, first_line)` | The number of lines the record has, given the values of its first line. A transformer has its fifth line (the third winding) only when `K` is set and nonzero. Every other record has all the lines of its layout. |
| `terminal_slots(terminal_type)` | The slots of an equipment terminal record, which has one field list per equipment form, chosen by TYP (`TERMINAL_FORMS`). An unknown form raises. |

`_values(record_class, slots, tokens, ...)` converts the tokens of one line to `{slot name: value}`:

- More tokens than the line has slots raises (`BusRecord: 14 fields where the record has 13`).
- A missing or blank field is `None`. A list slot takes its `count` tokens and is `None` when all are blank.
- An `int` slot takes a number with no fraction (`1`, `1.0`), else raises; a `float` slot takes a finite number, and
  a quoted one raises; a `string` slot is the token with its trailing blanks removed. Every error names the record
  class and slot and the line, with the line's text.
- A quoted value in an `int` slot is an **extended bus name**, `'NAME        kV'`: the 12-character bus name, then the
  base kV. `_bus_number` looks it up in the table `_index_bus_names` builds right after the bus section, so every bus
  reference in the model is a number. A leading `-` gives the negated number. A name that matches no bus or more than
  one, or has no kV, raises.

`_read_section` reads a record's first line, then `line_count` and `record_lines` say how many more lines to read and
how to read each; their values are merged into one dict, and the dataclass is built from it. A dataclass that rejects
the values (a required field left blank) raises through `_construct`, with the line.

The impedance correction table is the one special case (`_impedance_correction`): its length is not in the layout.
It reads the table number, then points in `(T, Re(F), Im(F))` triples, up to `POINTS_PER_LINE` (six) per line, until a
`0, 0, 0` triple. Points after that triple, a partial triple, a blank point field, a `Q` before the end, or more than
`MAX_POINTS` (99) raise. The points are `ImpedanceCorrectionPoint`s in the record's `points` list.

The SUBSTATION section is nested: a substation record, then three parts each ended by its own `0` (the nodes, the
switching devices, the equipment terminals). `_read_substations` reads the parts in that order and sets the reader-filled
`substation_number` on each part record (a `structural` slot). An equipment terminal's slots depend on its TYP, the
third field (`_terminal_slots`).

### Defaults and the defaulted note

The reader fills no defaults. A blank or missing field is `None`, so the model holds what the file said, and the
writer writes it back blank. The importer fills a blank from the slot's `raw_default` annotation
(`records.raw_defaults`, `fill_keyed_defaults`) and lists each value it filled in a `defaulted:` comment on the row, so
a default is visible in the artifact. [The importer](importer.md) has the details.

The one exception is a blank key field, which takes its `raw_default` when the composite ID is built (next section):
a load with no ID is load `1`, so the same load has the same key however the file wrote it. The slot itself stays
`None`.

### Composite IDs

`GraphModel` keys a record on its schema `identifier: true` slot, else on `record.ID`. Most RAW records have a
natural key of several fields, so the reader calls
[`composite_id.assign_composite_id(record)`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_raw/src/cimhub_raw/schema/raw_v34/composite_id.py)
on every record it adds, which sets `record.ID`.

`KEY_FIELDS` lists the fields of each key; the key is their trimmed values joined with `_`:

| Record | Key fields | Example |
|---|---|---|
| Load, Fixed shunt, Generator | `bus_number`, `load_id` / `shunt_id` / `gen_id` | `10_1` |
| Branch, System switching device | `from_bus_number`, `to_bus_number`, `circuit` | `1001_1201_1` |
| Transformer | `i`, `j`, `k`, `circuit` | `1001_1002_0_1` |
| Switched shunt | `bus_number` | `4001` |
| FACTS device | `name` | |
| Induction machine | `bus_id`, `name` | |
| Inter-area transfer | `from_area`, `to_area`, `transfer_id` | |
| Multi-section line | `i`, `j`, `line_id` | |
| Substation node | `substation_number`, `node_number` | |
| Station switching device | `substation_number`, `from_node`, `to_node`, `circuit` | |
| Equipment terminal | `substation_number`, `bus_number`, `terminal_type`, `j_bus`, `k_bus`, `identifier` | |

The other records have a single key slot marked `identifier: true`: the bus, area, zone, owner, substation and
impedance correction table numbers, a rating set's number, a DC line's name and, for the case identification record,
IC. That slot wins over `ID` as the graph key, so the case record is keyed `'0'` even though
`assign_composite_id` also sets its `ID` to `CASE`.
`_add` also checks the key: a second record with the same type and key raises (`duplicate BranchRecord '1_2_1' (first on
line <n>)`). The exporter calls the same function on the records it builds (`export_tables`), so the key that seeds an
mRID on import is the key an exported record has.

### Errors

`Raw34ParseError(message, *, source, line_number, text)` is a message prefixed with `<file>:<line>:` and followed by
the offending line's text. A reader error is one of these:

| Raised for | Where |
|---|---|
| a REV other than 34 | `_read_case` |
| an unknown or repeated system-wide keyword | `_read_case` |
| more fields than the record has, a value that does not convert, an unclosed quote | `_values`, `_tokens` |
| an extended bus name with no bus, or two | `_bus_number` |
| a duplicate key | `_add` |
| a missing section terminator, a blank line where a record belongs, the file ending inside a record, data after the last section that is not `Q` | `_next_record_tokens`, `_part`, `read` |
| a dataclass that rejects its values | `_construct` |

A populated MULTI-TERMINAL DC or GNE section raises `NotImplementedError` (`PHASE_2_SECTIONS`), naming the section and
the record count. A bus reference to a bus that does not exist is not a reader error: the reader checks only extended
names. A mapper finds it.

## Raw34Writer

`Raw34Writer().write(model, destination)` writes `"\n".join(lines(model)) + "\n"` to the path. `serialize(obj)` is one
record as RAW text, several lines for a multi-line record. The writer is the reader's mirror: it writes what the
model holds and defaults nothing.

| Function | Does |
|---|---|
| `format_field(slot, value)` | One field's text. `None` is blank. An `int` slot is `str(int(value))`. A `float` slot is written with the slot's `precision` when that reads back as the same number, else with `repr` (the shortest exact form). A `string` slot is padded to its `width` with `ljust` and, when `quote` is set, wrapped in its `quote_char` (default `'`). |
| `format_line(slots, record)` | One line: its fields by position, comma-joined. A list slot writes its values then blanks up to `count`; more values than `count` raises. Trailing blank fields are dropped, so the line has only what the model held. |
| `format_record(record)` | Every line of a record: `line_count` lines, each from `format_line`. |
| `format_impedance_correction(record)` | The special case below. |

```python
import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.raw34_writer import format_field
from cimhub_raw.record_layout import record_lines

slot = record_lines(schema.FixedShuntRecord)[0][1]          # shunt_id: width 2, quoted
print(repr(format_field(slot, "1")))                        # "'1 '"
```

### The file, in order

`lines(model)` writes:

1. The case record line, the two title lines (verbatim, always two; a case with more than two raises), each
   system-wide keyword that has text, and a `RATING,` line per rating.
2. For each entry of `SECTIONS`, a line `0 / END OF <previous> DATA, BEGIN <section> DATA`, then that section's records
   in the model's insertion order (the file order, for a model the reader built).
3. `0 / END OF <last section> DATA, BEGIN SUBSTATION DATA`, then each substation record followed by its nodes, a
   `0 / END OF SUBSTATION NODE DATA, BEGIN SUBSTATION SWITCHING DEVICE DATA` line, its switching devices, a
   terminator line, its equipment terminals (each by `terminal_slots` of its TYP) and a last terminator. A part whose
   substation is not in the model raises.
4. `0 / END OF SUBSTATION DATA` and `Q`.

A model with no `CaseIdentificationRecord` raises. Bus references are written as numbers, never as extended names.

### The impedance correction special case

A table is written number first, then its points `(T, Re(F), Im(F))` six to a line, ended by a `0, 0, 0` point; the
number is on the first line only. `format_impedance_correction` writes each value with a precision of 5.

### Phase-2 records

A model that holds a record of a phase-2 section (`PHASE_2_SECTIONS`: MULTI-TERMINAL DC, GNE) makes `lines` raise
`NotImplementedError` with the count and class, as the reader does for the same sections.

## Round trip

The reader and writer are lossless on the committed cases and atoms: `test_read_write_read_is_lossless` reads a case,
writes it, reads the output and compares every record field. See [Testing](testing.md).

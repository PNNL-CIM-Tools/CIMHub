# Reader and writer

`DssReader` turns a master `.dss` file and everything it redirects into a `DssModel`: LinkML dataclasses from
`opendss_schema`, one per `New` object. `DssWriter` does the reverse. They are the only code that touches deck files,
and the importer and exporter work on the `DssModel` between them. Both read the schema's YAML annotations at run
time instead of keeping name tables of their own (see [The LinkML schema](schema.md)).

```python
from cimhub_opendss import DssReader, DssWriter
from cimhub_opendss.schema import opendss_schema as schema

model = DssReader("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss").read_all()
print(len(model.list_by_class(schema.Line)), "lines")        # 16 lines
DssWriter().write(model, "/tmp/ieee13_out/IEEE13.dss")       # a deck the engine compiles and the reader reads back
```

## DssReader

`DssReader(source)` only binds the path. The first `read_all()` parses the whole file tree and caches the result;
later calls return the same `DssModel`. The work is in four steps, each a method in
[`dss_reader.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/src/cimhub_opendss/dss_reader.py).

| Step | Method | What it does |
|---|---|---|
| 1. Lines | `_read_with_redirects` | Yields `(line, file, line_number)`. Strips `!` and `//` comments outside quotes, skips `/* ... */` blocks (a line that starts with `/*` up to the line holding `*/`), follows `Redirect` and `Compile` (case-insensitive file names), and records the files named by `BusCoords` and `LatLongCoords`. A missing `Redirect` or `Compile` target raises `DssParseError`; a missing coordinates file raises `FileNotFoundError`. |
| 2. Join | `_join_continuation_lines` | A `~`, `More` or `M` line joins the most recent `New` or `Edit`, even with `Set` commands between them. One before any `New` or `Edit` raises. |
| 3. Parse | `_parse_command_line` | Routes a line to a `DssCommand` (`cmd`, class, name, `params`, file, line). |
| 4. Apply | `_build_graph` | Applies the commands in deck order to build the model. |

### Commands

`dss_command(word)` resolves a word the way the engine does: an exact name in `DSS_COMMANDS`, else the first command
that the word abbreviates (`CalcV` is `calcvoltagebases`, `o` is `open`). Then:

| Command | What the reader does |
|---|---|
| `New Class.name props` | Creates the object. `New Circuit.<name>` is `New Vsource.source` and the name goes on `Options.circuit`; a second `New Circuit` raises. A second `New` of an existing object is applied as an edit, with one warning. |
| `like=other` | Copies every slot the command leaves unset from `other`, which must be defined earlier. `like` itself stays set on the record, and the writer never writes it. |
| `Edit Class.name props`, `Class.name.prop=value` | Changes an object that must exist; otherwise raises. `wdg=` on an Edit raises, since it would replace whole arrays. |
| `BatchEdit Class.regex props` | Sets the properties on every object whose name the regular expression matches (a case-insensitive search); matching none raises. |
| `Set name=value` | Keeps `voltagebases`, `defaultbasefrequency` and `earthmodel` (`KEPT_OPTIONS`) on one `Options` record. Every other option is a solution setting and is not part of the model. An option name resolves as the engine resolves it (`dss_option`): the exact name, else the first option in `DSS_OPTIONS`, the engine's order, that it abbreviates. So `Set DefaultBaseF=50` is kept, and `Set e=...` is `element`, not `earthmodel`. A name that is no option raises. |
| `Open` and `Close` | Add or remove `Class.name terminal` in `Options.open_terminals`; the object must exist. Opening one conductor raises. |
| `Clear`, `ClearAll` | Discard everything defined so far. |
| `Redirect`, `Compile`, `BusCoords`, `LatLongCoords` | Handled in step 1. |
| commands in `SKIPPED_COMMANDS` (`solve`, `show`, `export`, ...) | Ignored: they leave the model as it is. |
| any other word | Raises: an unknown word (`Reditect`) or a command that changes the model in a way the reader does not follow (`Disable`, `Remove`, `Select`, ...). |

An error in any command is re-raised as `DssParseError`, whose message ends `in <file> at line <n>` and which keeps
`file_path` and `line_number`:

```python
from pathlib import Path
from cimhub_opendss import DssParseError, DssReader

deck = Path("/tmp/reader_error.dss")
deck.write_text("Clear\nNew Circuit.t bus1=a basekv=12.47\nReditect foo.dss\n")
try:
    DssReader(deck).read_all()
except DssParseError as error:
    print(error)                                   # unknown DSS command 'Reditect': Reditect foo.dss in /tmp/reader_error.dss at line 3
    print(error.file_path, error.line_number)
```

### Property names

`dss_name_map.get_class_map(schema_class)` builds a `DssClassMap` per class once. Its `param_to_field` maps every
lowercased DSS property name to a dataclass field:

- the field's own name, and its `dss_name` annotation when the DSS name is not a legal Python name (`%R` and `pct_R`,
  `class` and `load_class`);
- `bus` for `bus1`, and the `%`-form of every `pct_` field;
- `field_for(param)` takes an exact match, else the first property, in DSS order, that starts with `param`, as DSS
  accepts abbreviations (`ppm` is `ppm_antifloat`). A name that matches nothing raises `ValueError`.

A value with no `name=` goes to the property after the last one given, in the schema's `order`
(`_resolve_positional`); on a Transformer, XfmrCode, AutoTrans or LineGeometry a positional value raises, because
those classes are rewritten by block. `{...}` values are evaluated as RPN (`rpn_value`).

Enums go through `DssClassMap.enum_value_maps`: member names, aliases, the `dss_value` annotation and the number at
the end of the `meaning` URI all select the member, case-insensitively. An unknown value raises and lists the known
ones.

### Arrays and blocks

| Input | Result |
|---|---|
| `kVs=[115, 4.16]`, `kvs=(...)`, quoted lists, `kvar=[(14.4 13.8 / sqr 300 *), ...]` | A list; each element can be an RPN expression (`_parse_array`). |
| `mult=(file=shape.csv)` | The first column of the file, read relative to the deck that names it (`_read_array_file`). |
| `wdg=1 bus=A kV=115 wdg=2 bus=B kV=4.16` on a Transformer or XfmrCode | `buses=[A B]`, `kVs=[115 4.16]`, and the same for `kVAs`, `conns`, `taps`, `pct_Rs` (`_preprocess_winding_text`, `_extract_winding_arrays`). A winding left unset while another sets it takes the schema's `dss_default`, with a warning (no default raises). `RdcOhms` has no array form in DSS: each value goes to the active winding's place in the `RdcOhms` list, and since it has no default (the engine's is computed from %R), a winding left unset while another sets it raises. `Rneut` and `Xneut` belong to the active winding, which the reader keeps as `wdg=`; the schema holds one winding's, so a second winding that sets either raises. |
| `cond=1 wire=W x=0 h=28 units=ft` blocks on a LineGeometry | `xs`, `hs` and `wires`, `cncables` or `tscables` arrays (`_extract_linegeometry_arrays`). |

### Defaults stay unset

The reader never fills a DSS default into a record: an unset property is `None` (or `[]`), and a model written back
repeats only what the deck said. The defaults are the schema's `dss_default` annotations. `dss_defaults(schema_class)`
returns them typed as the reader types deck text, and the mappers pass them to `cimhub_core.cimtbl.fill_defaults`,
which lists each filled slot in a `defaulted:` comment in the artifact. The one place the reader uses a default is the
winding array above, because an array cannot hold a hole.

### DssModel

`DssModel` is a core `GraphModel` (`list_by_class(cls)`, `count(cls)`, `add_to_graph(obj)`, `graph`) with one addition:
the assignment history. A record keeps only the last value of each slot, but for some properties the order of the
assignments decides the value (a Generator keeps `kvar` as a power factor taken at the kW of that moment; a
Storage's `State` picks one of the setpoints `kW` sets).

```python
load = model.list_by_class(schema.Load)[0]
model.assignments(load)[:2]              # [('bus1', '611.3'), ('phases', 1)], in deck order
model.last_of(load, "kW", "kvar", "pf")  # the one of these slots the deck assigned last: 'kvar'
```

`history` holds every `(slot, value)` from `New`, the slots `like=` copied first, edits and `BatchEdit`, keyed by
`(class, lowercased name)`. Mappers replay it where the order matters (`CIMTBL_MAPPING.md` S4b-8).

Names are case-insensitive, as in DSS, and an object keeps the spelling of its first `New`. Buscoords rows are made
from the coordinate files after the commands, keyed by bus name. `LatLongCoords` files are `lat, long` and are stored
as `x = long`, `y = lat`; the directive decides, not the file name.

## DssWriter

`DssWriter` takes a `DssModel` and writes one deck.

- `serialize(obj)` renders one `new Class.name prop=value ...` command. It raises for `Options` and `Buscoords`
  (which `write` places) and for a LineGeometry with positions (which needs the model's wire catalogs).
- `write(model, destination, *, per_class=False)` writes the deck. A class in the model that is neither in
  `WRITE_ORDER` nor `Options` or `Buscoords` raises.

### Command order

`write` emits, in this order:

1. `Clear`
2. `Set defaultbasefreq=...` when `Options` has one, so the circuit takes it
3. `New Circuit.<Options.circuit>` with the slots of `Vsource.source`. `Options.circuit` and `Vsource.source` come
   together: one without the other raises, and neither is a fragment (a catalog deck)
4. `Set earthmodel=...`
5. Every record of each class in `WRITE_ORDER`: `Loadshape`, `Wiredata`, `Cndata`, `Tsdata`, `Linespacing`,
   `Linegeometry`, `Linecode`, `Xfmrcode`, `Vsource`, `Line`, `Relay`, `Fuse`, `Recloser`, `Swtcontrol`,
   `Transformer`, `Regcontrol`, `Load`, `Capacitor`, `Capcontrol`, `Pvsystem`, `Storage`, `Generator`, `Reactor`. Each
   class comes after everything it references: catalogs before their users, a Line before the Fuse, Recloser or
   SwtControl that switches it, a Transformer before its RegControl, a Capacitor before its CapControl.
6. `Set voltagebases=[...]` and `CalcVoltageBases`
7. One `Open Class.name terminal` per `Options.open_terminals`
8. `Buscoords <stem>_buscoords.csv` and `LatLongCoords <stem>_latlongcoords.csv`, naming the coordinate files written
   beside the deck

With `per_class=True`, each class's commands go to their own file beside the deck (`linecode.dss`, `line.dss`, ...)
and the master has a `Redirect` for each, in the same order:

```python
DssWriter().write(model, "/tmp/ieee13_perclass/IEEE13.dss", per_class=True)
```

### How annotations drive the output

`_properties(obj)` writes `dss_name=value` for each set slot (`None` is skipped), in this order: first the
`_LEADING_SLOTS` (`XfmrCode`, `linecode`, `geometry`, `spacing`, `phases`, `Switch`), then the schema's `order`
annotation. The leading slots go first because assigning each one sets other properties: a template copies its values,
an XfmrCode re-sizes the windings, and `Switch=y` sets the impedance. The record's own values then go after them. `like` is never
written, since the reader has already copied its values into the slots. A per-winding slot DSS has no array form for
(`_PER_WINDING_SLOTS`: `RdcOhms`) goes last, as one `wdg=n RdcOhms=v` block per winding, so no other per-winding slot
follows a `wdg=` it moves.

| Annotation | Writer use |
|---|---|
| `order` | The position of the slot in the command (9999 when absent). |
| `dss_name` | The property name written, else the field name. |
| `dss_format: matrix` | A list is written as a lower-triangle matrix `[r11 |r21 r22 |...]` (`_format_matrix`), and a string value is not sanitized, since it already holds the brackets. |
| `dss_value` | Not read by the writer. An enum is written as the number at the end of its `meaning` URI when there is one (`LoadModel.4` as `4`), else its text. |

Values go through `_format_value`: `bool` as `Yes` or `No`, a float to 15 significant digits (`format_float`), a list
as `[a b c]`, a nested dataclass as its name. Names and references go through `dss_safe_name`, which replaces each run
of characters DSS cannot carry in a name (whitespace, quotes, `<>`, brackets, braces, parentheses, `,`, `=`, `~`, `|`) with one `_`, so a definition
and every reference to it are spelled alike. Two records of one class whose names become one (`a b` and `A_B`,
compared lowercased as DSS compares names) raise in `write` (`check_safe_names`): DSS would apply the second as an
edit of the first. The exporter's `Names` raises on the same collision before the writer sees it.

A LineGeometry with positions is written by `_geometry` as `cond=N wire=W x=.. h=..` blocks. The block keyword
(`wire`, `cncable` or `tscable`) comes from the wire catalog that defines each conductor, and a conductor in no
catalog, or in two, raises.

### Buscoords files

`Buscoords` rows are written beside the deck, one CSV per kind: `<stem>_buscoords.csv` as `bus, x, y` and
`<stem>_latlongcoords.csv` as `bus, y, x`, since a `LatLongCoords` file is `lat, long`. The reader swaps them back.

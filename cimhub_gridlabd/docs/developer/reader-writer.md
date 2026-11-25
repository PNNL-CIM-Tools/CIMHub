# Reader and writer

`GlmReader` turns a `.glm` file and everything it `#include`s into a `GlmModel`: LinkML dataclasses from
`cimhub_gridlabd.schema.gridlabd`, one per `object` block, plus what the mappers need beyond the records. `GlmWriter`
does the reverse. They are the only code that touches deck files and player tapes, and the importer and exporter work
on the `GlmModel` between them. Both get property names and units from the schema's YAML at run time through
`glm_schema.py` instead of keeping name tables of their own (see [The LinkML schema](schema.md)).

```python
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.schema import gridlabd as schema

model = GlmReader("cimhub_gridlabd/tests/decks/IEEE/IEEE13_cdpsm.glm", defines={"VSOURCE": "66395.28"}).read_all()
print(len(model.list_by_class(schema.OverheadLine)), "overhead lines")     # 11 overhead lines
GlmWriter().write(model, "/tmp/ieee13_out/IEEE13.glm")                     # a deck the reader reads back
```

The IEEE decks refer to `${VSOURCE}` without defining it, as the GridAPPS-D run file does. `defines` is where the
reader takes it, the way `gridlabd -D VSOURCE=66395.28` would. Without it the read raises (see Macros below).

## GlmReader

`GlmReader(source, *, defines=None)` only binds the path and the caller's macros. `read_all()` raises
`FileNotFoundError` for a missing file, then runs the steps below. They are in
[`glm_reader.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gridlabd/src/cimhub_gridlabd/glm_reader.py).

| Step | Code | What it does |
|---|---|---|
| 1. Tokens | `_tokens(path)` | Yields one `_Token` per statement: kind `open` (text before `{`), `close`, `end` (text before `;`) or `directive` (a line that starts with `#`), with file and line. `//` comments are dropped. Quoted text and `${NAME}` stay whole, so a `;` or `//` inside them is text. An unterminated quote or `${`, or a statement with no closing `;`, raises. |
| 2. Raw objects | `_Parser` | Reads the blocks and directives in order into `_RawObject`s (type, header id, properties, nested objects) and into the model's settings. Macros expand here. |
| 3. Records | `_expand_objects`, `_build`, `_record` | Orders the objects as GridLAB-D creates them, names them, resolves references, types each value and adds the records to the model. |
| 4. Tapes | `read_all`, `read_tape` | Reads each player's `file` into `GlmModel.tapes`. |

### Blocks and directives

| Input | What the reader does |
|---|---|
| `object <class> { ... }` | One record of the schema class named `<class>` (`glm_schema.class_registry`). A class the schema lacks is counted in `GlmModel.not_read` and its properties are not read. A property the class lacks raises. Keywords are case-sensitive, as in GridLAB-D's parser. |
| nested `object <class> { ... }` | The nested object's `parent` is the enclosing object, in GridLAB-D's creation order (the parent first). A nested object that also sets `parent` raises. |
| `object house:..20 { ... }` | 20 objects, nested objects included. A ranged object that sets `name` raises, since all copies would share it. |
| `clock { ... }` | Merged into `GlmModel.clock`. |
| `module <name> { ... }`, `module <name>;` | `GlmModel.modules[name]`, the settings as text (`{}` for the bare form). |
| `schedule <name> { ... }` | `GlmModel.schedules[name]`: its statements as written (nested blocks flattened to their text). The rules are read by `importer/cimtbl/schedule.py`. |
| `class player { double value; }` | `GlmModel.classes`. This is the one `class` block read, the GridAPPS-D run file's player value (`PLAYER_CLASS`); any other raises. |
| `#define name=value`, `#set name=value` | `GlmModel.defines` and `GlmModel.globals`. The name may contain `.` and `:` (`powerflow::nominal_frequency`). The value is unquoted and macro-expanded. |
| `#include "file"` | Parsed in place, relative to the including file. A missing file raises. |
| any other directive (`#if`, `#ifdef`, `#error`, ...), any other block, any other top-level statement | Raises `GlmParseError` naming it. |

### Macros

`${NAME}` is expanded where it appears in a value, from the file's `#define`s so far, then its `#set`s, then the
caller's `defines`. An unknown name raises `macro ${NAME} is not defined (pass it in defines=)`. After the parse, the
caller's `defines` are added to `GlmModel.defines`, so a written deck carries them.

### Values, units and expressions

`_convert(kind, text)` types a value by the dataclass's type hint (`_slot_kinds`: `complex`, `float`, `int`, `bool`,
`enum` or `text`). There is no unit conversion in the reader.

| Value text | Result |
|---|---|
| `30 in`, `12MVA` | The number is stored and the unit goes to `GlmModel.written_units[(name, slot)]`. `GlmModel.unit(record, slot)` returns it, else the unit the schema declares for the slot. |
| `0.5+2j`, `0.5+2i` | A rectangular `Complex`. |
| `100+5d`, `100+0.087r` | A polar complex, degrees or radians. It is stored rectangular, and its magnitude and angle as written go to `GlmModel.polar`, since the rectangular value went through sin and cos, which differ in the last bit between C libraries. |
| `LIGHTS*1.2`, `random.normal(1750,400)` | A numeric or complex text that is not a literal is an expression: kept verbatim in `GlmModel.expressions[(name, slot)]`, and the slot stays unset. The orchestrator raises on an expression in a slot a mapper reads (see [The importer](importer.md)). |
| `TRUE`, `false` | A boolean, in any case; anything else raises. An integer slot with a non-integer value raises. |
| enum | Kept as the text written. |
| text | Kept as written, except that a value of the form `<class>:<id>` that names an unnamed object resolves to that object's name. |

An unset property is `None` on the record: **GridLAB-D's defaults are never filled in**. A written deck repeats only
what the model said. The defaults the mappers need are named in the mapping spec, and a mapper that uses one says so
in a `defaulted:` comment.

### Names, repeats and errors

- Names are unique across the model, as in GridLAB-D; a repeat raises and names the first object's file and line.
- An unnamed object is `<class>:<header id>` when its header has one (`object node:12`), else `<class>:<position>`,
  the position being GridLAB-D's object id, counted from 0 over every object in the file tree.
- A property set twice on one object keeps the last value, with one warning that names the type, the property and
  the count.
- `GlmModel.origins[name]` is the `(file, line)` of the object's header, which the importer uses in its messages.

Every error the reader raises is a `GlmParseError`, whose message starts `<file>:<line>:` and which keeps `path` and
`line`:

```python
from pathlib import Path
from cimhub_gridlabd.glm_reader import GlmParseError, GlmReader

Path("/tmp/reader_error.glm").write_text("object node {\n  name a;\n  bogus 3;\n}\n")
try:
    GlmReader("/tmp/reader_error.glm").read_all()
except GlmParseError as error:
    print(error)                           # /tmp/reader_error.glm:3: node has no property 'bogus'
    print(error.path, error.line)
```

### Player tapes

`read_tape(path)` reads a player's file as `(time, value)` text rows, as written: blank lines and lines that start
with `#` are dropped, and a value ends at a `;` (what GridLAB-D's player does). A row with no comma, an empty time
or an empty value raises, and so does a missing file. The reader looks for a player's `file` beside the file that
declares the player and keeps the rows in `GlmModel.tapes[player name]`. The importer reads the times and values
(`importer/cimtbl/player.py`).

### GlmModel

`GlmModel` is a core `GraphModel` (`list_by_class(cls)`, `count(cls)`, `add_to_graph(obj)`, `graph`) with the
fields the mappers read.

| Field or method | Holds |
|---|---|
| `by_name(name)` | The record called `name`, whatever its class; raises `KeyError`. |
| `unit(record, slot)` | The unit the value is written in, else the schema's. |
| `written_units` | `(name, slot)` to the unit text written with a value. |
| `expressions` | `(name, slot)` to the text of a numeric value that is not a literal. |
| `polar` | `(name, slot)` to `(magnitude, degrees)` of a polar complex. |
| `not_read` | A `Counter` of the object types the schema lacks. |
| `clock`, `modules`, `globals`, `defines` | The settings blocks and directives, as text. |
| `schedules`, `classes`, `tapes` | The schedule statements, the one `class` block, the player rows. |
| `origins` | `(file, line)` of each object's header. |

## GlmWriter

`GlmWriter` takes a `GlmModel` and writes one deck.

- `write(model, destination)` builds the deck first (so what it cannot write raises before any file is written), writes
  it to `destination`, creating its directory, then each player's tape to `player.file` beside it.
- `deck(model)` returns the deck as text. A player with no `file` raises here.
- `serialize(obj, expressions=None, written_units=None)` renders one `object <class> { ... }` block. `expressions` is
  `GlmModel.expressions`: a slot that is unset but has an expression is written as that text. `written_units` is
  `GlmModel.written_units`: a value written with a unit is written back with it (`distance_AB 30 in;`).

```python
from cimhub_gridlabd.glm_writer import GlmWriter

load = model.by_name("ld_611")
print(GlmWriter().serialize(load, model.expressions))
```

The `base_power_C` of that load is an expression (a player's value times a constant), so it is written as the text the
deck had:

```text
object load {
  name "ld_611";
  parent "611";
  phases "CN";
  nominal_voltage 2401.78;
  base_power_C ieeezipload.value*187882.94;
  current_pf_C 0.904819;
  current_fraction_C 1;
}
```

### What `deck` writes, in order

1. The `clock` block (nothing when the model has none).
2. `#set name=value` for each of `GlmModel.globals`, then `#define name=value` for each of `defines`.
3. One `module <name> { ... }` per module, or `module <name>;` when it has no settings. Settings are written as
   given: the exporter's are already GLM text.
4. The `class` blocks (`class player { double value; }`).
5. The `schedule` blocks, one rule per line.
6. Every record of each class in `WRITE_ORDER`, in name order within a class.

`WRITE_ORDER` puts each class after the classes it names: `player`, the three conductor catalogs, `line_spacing`,
`line_configuration`, `triplex_line_configuration`, `transformer_configuration`, `regulator_configuration`, then the
buses (`substation`, `node`, `meter`, `triplex_node`, `triplex_meter`), the lines, the switching devices and
`series_reactor`, `transformer` and `regulator`, then the devices parented to buses: `load`, `triplex_load`,
`capacitor`, `inverter`, `solar`, `battery`. A model that holds a class not in `WRITE_ORDER` raises, so nothing is
dropped. The players and the tapes must also match: a player with no tape, or a tape with no player, raises.

A block starts `name "<name>";`, then every set slot in the schema's order (the order of the dataclass fields, which
is the YAML's), each as the slot's GLM property name (`from` for the slot `from_node`) and a value.

### Value formats

| Python value | Written as |
|---|---|
| a `bool` | `TRUE` or `FALSE` |
| an `int` | its digits |
| a `float` | `format_float`: 15 significant digits, the shortest form (`60`, `0.0018`, `1e-05`) |
| a `Complex` | `format_complex`: rectangular `a+bj`. The real part is unsigned when positive, and the imaginary sign is always written, so `0.5-2j` and `-1.5+2j`, never `+0.5-2j`. This is the form the Java CIMHub exports use. |
| an enum or text | double-quoted. A text that holds `"` raises, since GLM cannot quote it. GridLAB-D reads quoted keywords. |

```python
from cimhub_gridlabd.glm_writer import format_complex, format_float
from cimhub_gridlabd.schema import gridlabd as schema

print(format_complex(schema.Complex(real=0.5, imag=-2)))     # 0.5-2j
print(format_complex(schema.Complex(real=-1.5, imag=2)))      # -1.5+2j
print(format_float(0.0000123))                                # 1.23e-05
```

A value the deck wrote with a unit (`GlmModel.written_units`) is written with that unit, so a model from `GlmReader`
keeps `30 in` as `30 in`: a bare 30 would be read in the schema's unit (`distance_AB` is in `ft`). Any other value is
written in the slot's schema unit with no unit text, since GridLAB-D stores each property in one fixed unit. The
exporter's models hold no written units: they are in the schema's units already.

### Player tapes

`tape_text(rows)` renders a tape: one `time,value` row per line. `write` writes `tape_text(model.tapes[name])` to
`<deck directory>/<player.file>`. The exporter names its players' files `<group>.player`, so they land beside the
deck. A `file` with a subdirectory in it (`tapes/a.player`, which the reader accepts) is written there, the
subdirectory made. A player with no `file` raises `ValueError` before the deck is written.

### Schedules

`_schedule_block(name, rules)` writes `schedule <name> {` then each rule as `  <rule>;` and `}`. The rules are the
text the reader kept or the exporter built (`minutes hours days months weekdays value`).

### The header the exporter sets

The writer has no header of its own; `cim_to_glm._set_header` fills the model: a `clock` that starts and stops at one
instant, `#set relax_naming_rules=1`, `module powerflow` with `solver_method NR`, `nominal_frequency` and
`line_capacitance TRUE`, and `module generators;` when the model has an inverter, solar or battery. See
[The exporter](exporter.md).

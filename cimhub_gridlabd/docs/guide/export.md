# Export: CIM to GLM

```python
from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter, cim_to_glm
from cimhub_gridlabd.glm_writer import GlmWriter

cim_to_glm(network, "out/IEEE13_cdpsm.glm", name_source="name")    # export and write in one call

model = GlmExporter().to_model(network, name_source="name")        # records only, no files
GlmWriter().write(model, "out/IEEE13_cdpsm.glm")
```

`network` is any cim18v17 network, for example the result of [`glm_to_cim`](import.md). The exporter reads it through
the [getters in `cimhub_core`](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/) and returns a `GlmModel`,
the same shape `GlmReader.read_all()` returns, so the `.glm` the writer produces reads back through the reader and
the importer, and GridLAB-D solves it. Only `GlmWriter` touches the filesystem.

## Options

`GlmExporter(time_points=None).to_model(network, *, name_source=None, switch_state="actual")`.
`cim_to_glm(network, destination, *, time_points=None, **opts)` passes `opts` to `to_model` and writes the result.

| Argument | Meaning |
|---|---|
| `name_source` | What a GLM name comes from: `'name'`, `'mrid'` or `'uri'`. Without it, `$CIMHUB_NAME_SOURCE`, else `'mrid'`. Any other value raises. |
| `switch_state` | `'actual'` (default) writes each switch's `status` from `Switch.open`. `'normal'` reads `Switch.normalOpen`. Any other value raises: `switch_state must be one of ['actual', 'normal'], not 'bogus'`. |
| `time_points` | A dict of time point tables. Its `RegularTimePoint` table holds the points of the network's schedules and gives the players their rows. See [Players and schedules](time-series.md). |
| `destination` | `cim_to_glm` only. The `.glm` path. Its folders are created, and each player's file is written beside it. |

## Names

Every GLM name is the CIM object's `name`, `mRID` or `uri()`, as `name_source` says, with each run of characters
GridLAB-D cannot take in a name (white space, `.`, `:`, quotes, `;`, braces, `$`) replaced by `_`. A `.` would read as
`object.property`, and `:` as `class:id`.

| `name_source` | Use it when |
|---|---|
| `'mrid'` (default) | the model came from `glm_to_cim`: the importer compiled each mRID from the GLM name, with a prefix per class (`ld_`, `ln_`, `sw_`), so names are unique |
| `'name'` | you want the names a person gave the objects. A model with duplicate names raises (below). A model from `glm_to_cim` gets its original GLM names back |
| `'uri'` | names must be stable and of fixed length across tools. `mRID` is a free-form string in cim18v17, so it is not a safe join key; `uri()` is |

On the IEEE 13-node model, load `611` is `ld_ld_611` under `'mrid'`, `ld_611` under `'name'` and a UUID under `'uri'`.

Rules:

- GLM names are global, so there is one namespace. Two objects that end up with one name raise:
  `ACLineSegment 'ln_b' and 'ln_a' are both named 'a' in GLM (name source 'name')`.
- An object with no `name` (or `mRID`, or `uri()`) to export it under raises, naming its class and mRID.
- A bus is a `node`, or a `triplex_node` on a split-phase bus, and the swing bus is a `substation` (a one-phase swing is a `node` with `bustype SWING`: GridLAB-D's substation needs three phases).

## The header

The `.glm` is one power flow, not a time series. The exporter writes the same header every time:

```
clock {
  timezone UTC0;
  starttime '2000-01-01 00:00:00';
  stoptime '2000-01-01 00:00:00';
}
#set relax_naming_rules=1
module powerflow {
  solver_method NR;
  nominal_frequency 60;
  line_capacitance TRUE;
}
module generators;
```

| Line | Why |
|---|---|
| `clock` | starts and stops at one instant. With players, the instant is the earliest player start, so each scheduled load is its base times the first point; a later `stoptime` plays the schedule |
| `#set relax_naming_rules=1` | GridLAB-D accepts the quoted names the writer produces, which may hold characters it would otherwise reject |
| `solver_method NR` | the Newton-Raphson solver |
| `nominal_frequency` | the network's `BaseFrequency`, in Hz |
| `line_capacitance TRUE` | CIM's line susceptance is part of the model, and GridLAB-D ignores every `c` matrix without it |
| `module generators;` | only when the network holds inverters, solar or batteries |
| `module tape;` and `class player { double value; }` | only when there are players |

## What it refuses

The exporter fails rather than dropping equipment. Before it writes anything, it checks every piece of conducting
equipment in the network against the classes it exports. A class it does not export raises, with the count of each:

```
ValueError: no GLM export yet for {'SynchronousMachine': 1}
```

A `BusbarSection` is the one class it skips on purpose: GLM has no object for it, because the busbar is its node's
bus. [What converts](coverage.md) lists the classes that export.

| Cause | What you get |
|---|---|
| A `switch_state` other than `'actual'` or `'normal'` | `ValueError` before anything is exported |
| A switch whose `open` is unset under `'actual'`, or whose `normalOpen` is unset under `'normal'` | `ValueError: LoadBreakSwitch 'sw_swt_671692': open is unset`. There is no fallback from one to the other. Use `switch_state='normal'` for an as-built model |
| Two objects with one GLM name, or one with nothing to name it by | `ValueError`, see [Names](#names) |
| A CIM quantity the GLM property has no home for, or a configuration GLM cannot hold | `ValueError` naming the object. The cases are in the [export mapping](../EXPORT_MAPPING.md) |

## Switches

A CIM `Fuse` is written as a `fuse`, a `Recloser` as a `recloser`, a `Sectionaliser` as a `sectionalizer`, and any
other switch class (`LoadBreakSwitch`, `Breaker`, `Disconnector`, `Jumper`, a plain `Switch`) as a `switch`, because
GLM has no breaker. `status` is `OPEN` or `CLOSED`, read from the state `switch_state` names.

## The writer

`GlmWriter().write(model, destination)` creates the destination's folders, writes the `.glm`, and writes one file
for each `player` beside it. `GlmWriter().deck(model)` returns the same text without touching files.

The deck is written in this order: the `clock` block, the `#set` lines, the `#define` lines, one `module` block per
module, the `class` blocks, the `schedule` blocks, then the objects. Objects go in dependency order, each class after
the ones it names: players, the conductor catalogs, spacings and line configurations, transformer and regulator
configurations, nodes and meters, lines, switching devices, transformers and regulators, loads and capacitors, then
inverters, solar and batteries. Within a class, objects are sorted by name.

| Value | Written as |
|---|---|
| a number | 15 significant digits, the shortest form (`60`, `0.0018`, `1e-05`), in the unit GridLAB-D fixes for that property. No unit text is written |
| a complex number | rectangular, `0.3465+1.0179j`; the sign of the imaginary part is always written |
| a boolean | `TRUE` or `FALSE` |
| text (a name, a reference, a keyword) | double-quoted: `name "lcon_mtx601_ABC";` |
| a property that holds an expression | the expression as it was read, for example a load's `<player>.value*K` |

An unset property is not written, so GridLAB-D uses its own default. A model with an object of a class that has no
place in the writing order raises `GlmWriter: no write order for [...]`. Text with a double quote in it raises
`GLM text '...' holds a double quote, which GLM cannot quote`.

A player's file has one `time,value` row per line:

```
2009-07-21 04:00:00 GMT,0.425364
+60s,0.42153
```

The writer raises if the model's players and tapes differ: `GlmWriter: players [...] and tapes [...] differ`.

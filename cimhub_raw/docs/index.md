---
title: CIMHub PSS/E RAW
hide:
  - navigation
  - toc
---

<div class="ct-hero" markdown>

# PSS/E RAW cases <span class="ct-accent">to CIM and back</span>

<p class="ct-lede"><code>cimhub-raw</code> reads a PSS/E RAW v34 case, writes it as <code>.cimtbl</code> text, and builds an
IEC CIM model (<code>cim18v17</code>) from that text. It also reads a CIM model and writes a <code>.raw</code> case that
the reader and the importer read back.</p>

[Quick start](guide/quickstart.ipynb){ .md-button .md-button--primary }
[What converts](guide/coverage.md){ .md-button }
[Developer docs](developer/index.md){ .md-button }

</div>

```python
from cimhub_raw.exporter.cim_to_raw import cim_to_raw
from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim
from cimhub_raw.raw34_reader import Raw34Reader

model = Raw34Reader("cimhub_raw/tests/cases/IEEE14/IEEE_14_bus.raw").read_all()   # .raw -> RAW records
network = raw_to_cim(model, name="IEEE14", artifact_dir="IEEE14_cimtbl")           # records -> .cimtbl -> CIM
cim_to_raw(network, "IEEE14_from_cim.raw")                                         # CIM -> .raw
```

`raw_to_cim` writes the case as `.cimtbl` text and builds the CIM network from that text, so the text you can read
and diff (pass `artifact_dir=` to keep it) is exactly what the model was built from. Values keep the units the case
used, and the unit is in the column header. `cim_to_raw` reads the network back through the
[CIMHub core getters](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/), which convert once to the unit RAW
expects.

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } __User guide__

    ---

    Install it, convert the IEEE 14-bus case both ways, then import, export, the round trip and the list of RAW
    tables that convert.

    [:octicons-arrow-right-24: User guide](guide/index.md)

-   :material-table-search:{ .lg .middle } __Conversion reference__

    ---

    For each group of RAW tables, what each record becomes in CIM, how its fields map and where the two models
    differ.

    [:octicons-arrow-right-24: Conversion reference](reference/index.md)

-   :material-code-braces:{ .lg .middle } __Developer docs__

    ---

    The map of the code: reader and writer, importer, exporter, the LinkML schema, the tests and the rules a change
    keeps.

    [:octicons-arrow-right-24: Developer docs](developer/index.md)

-   :material-file-tree:{ .lg .middle } __Schema reference__

    ---

    Every RAW v34 record and field the reader knows, generated from the LinkML schema.

    [:octicons-arrow-right-24: Schema reference](schema/index.md)

</div>

## What the package does

| Step | Call | Result |
|---|---|---|
| Read | `Raw34Reader(path).read_all()` | a `GraphModel` of typed records, one class per RAW table |
| Import | `raw_to_cim(model, name=...)` | a cim18v17 `BusBranchModel`, built from `.cimtbl` text |
| Export | `RawExporter().to_model(network)` | a `GraphModel` of RAW records again, from the CIM objects |
| Write | `Raw34Writer().write(model, path)` | a `.raw` that the reader and the importer read |

Only the reader and the writer read and write case files: `RawImporter.to_cimtbl` and `RawExporter.to_model` touch
none. The [quick start](guide/quickstart.ipynb) runs each step on the IEEE 14-bus case.

- **Nothing is guessed.** An unsupported REV, an unknown system-wide record, a field that does not convert, a duplicate
  record, an unresolved extended bus name or an unmapped code raises, naming the record (and, in the reader, the file and
  line). A blank field takes the schema's default and is listed on the row's comment, so a default never
  hides.
- **Units are not converted by hand.** Import copies values in the units the case used, per unit on the system base
  (SBASE) where RAW says so, and the unit is in the column header. Export reads each quantity through a core getter.
- **Some RAW data raises.** A case with multi-terminal DC lines, GNE devices or induction machines does not import,
  and the exporter raises for CIM equipment it has no RAW record for (DC lines and FACTS devices are imported but not
  yet exported). See [What converts](guide/coverage.md).
- **Three public cases are in the repository:** IEEE 14 bus, IEEE 118 bus (with four node-breaker substations) and the
  WECC 240 bus case, under
  [`cimhub_raw/tests/cases`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/tests/cases).

CIMHub PSS/E RAW is one package of CIMHub. The other converters, and the landing page for all of them, are at
[CIMHub](https://pnnl-cim-tools.github.io/CIMHub/). The shared layer under every converter is
[CIMHub core](https://pnnl-cim-tools.github.io/CIMHub/core/).

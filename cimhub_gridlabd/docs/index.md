---
title: CIMHub GridLAB-D
hide:
  - navigation
  - toc
---

<div class="ct-hero" markdown>

# GridLAB-D models <span class="ct-accent">to CIM and back</span>

<p class="ct-lede"><code>cimhub-gridlabd</code> reads a <a href="https://www.gridlabd.org/">GridLAB-D</a> <code>.glm</code> model,
writes it as <code>.cimtbl</code> text, and builds an IEC CIM model (<code>cim18v17</code>) from that text. It also reads a
CIM model and writes a <code>.glm</code> that GridLAB-D solves.</p>

[Quick start](guide/quickstart.ipynb){ .md-button .md-button--primary }
[What converts](guide/coverage.md){ .md-button }
[Developer docs](developer/index.md){ .md-button }

</div>

```python
from cimhub_gridlabd.exporter.cim_to_glm import cim_to_glm
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim

model = GlmReader("cimhub_gridlabd/tests/decks/IEEE/IEEE13_cdpsm.glm", defines={"VSOURCE": "66395.28"}).read_all()  # .glm -> typed records
network = glm_to_cim(model, name="IEEE13_cdpsm")                                   # records -> .cimtbl -> CIM
cim_to_glm(network, "out/IEEE13_cdpsm.glm", name_source="name")                    # CIM -> .glm
```

`glm_to_cim` writes the model as `.cimtbl` text and builds the CIM network from that text, so the text you can read
and diff (pass `artifact_dir=` to keep it) is exactly what the model was built from. Values keep the units the
`.glm` wrote, and the unit is in the column header. `cim_to_glm` reads the network back through the
[CIMHub core getters](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/), which convert once to the unit
GridLAB-D expects.

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } __User guide__

    ---

    Install it, convert the IEEE 13-node feeder both ways, then import, export, players and schedules, round-trip
    checks and the list of GLM classes that convert.

    [:octicons-arrow-right-24: User guide](guide/index.md)

-   :material-table-search:{ .lg .middle } __Conversion reference__

    ---

    For each group of GLM classes, what each one becomes in CIM, how its properties map and where the two models
    differ.

    [:octicons-arrow-right-24: Conversion reference](reference/index.md)

-   :material-code-braces:{ .lg .middle } __Developer docs__

    ---

    The map of the code: reader and writer, importer, exporter, the LinkML schema, the tests and the rules a change
    keeps.

    [:octicons-arrow-right-24: Developer docs](developer/index.md)

-   :material-file-tree:{ .lg .middle } __Schema reference__

    ---

    Every GLM class and property the reader knows, generated from the LinkML schema.

    [:octicons-arrow-right-24: Schema reference](schema/index.md)

</div>

## What the package does

| Step | Call | Result |
|---|---|---|
| Read | `GlmReader(path, defines=...).read_all()` | a `GlmModel` of typed records, with `#include`s followed and `${NAME}` macros expanded |
| Import | `glm_to_cim(model, name=...)` | a cim18v17 network, built from `.cimtbl` text |
| Export | `GlmExporter().to_model(network)` | a `GlmModel` again, from the CIM objects |
| Write | `GlmWriter().write(model, path)` | a `.glm` (and its player files) that the reader, the importer and GridLAB-D read |

Only the reader and the writer read and write model files: `GlmImporter.to_cimtbl` and `GlmExporter.to_model` touch none. The [quick start](guide/quickstart.ipynb) runs each step on a
real model.

- **Nothing is guessed.** An unknown property, an expression the importer cannot read, an unmapped value or an
  unresolved reference raises with the name of the GLM object. A GLM class no mapper reads is listed by count in the
  master `.cimtbl`, so it never disappears silently.
- **Units are not converted by hand.** Import copies values in the units the `.glm` wrote; export reads each quantity through a core
  getter, which converts once to the unit GridLAB-D fixes for that property.
- **Players and schedules carry time series.** Their points go to a dict of Arrow tables beside the model, not into
  the CIM objects. See [Players and schedules](guide/time-series.md).

CIMHub GridLAB-D is one package of CIMHub. The other converters, and the landing page for all of them, are at
[CIMHub](https://pnnl-cim-tools.github.io/CIMHub/). The shared layer under every converter is
[CIMHub core](https://pnnl-cim-tools.github.io/CIMHub/core/).

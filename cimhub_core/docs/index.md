---
title: CIMHub core
hide:
  - navigation
  - toc
---

<div class="ct-hero" markdown>

# Read a CIM model <span class="ct-accent">in the unit you want</span>

<p class="ct-lede"><code>cimhub-core</code> is the shared layer under every CIMHub converter. Its export getters read
IEC CIM objects, in cim18v17, as plain floats and NamedTuples in the unit you name. It also holds the
<code>.cimtbl</code> import contract, the canonical table shapes and the test harness that the format spokes build on.</p>

[Quick start](guide/quickstart.ipynb){ .md-button .md-button--primary }
[Getter reference](reference/index.md){ .md-button }
[Developer docs](developer/index.md){ .md-button }

</div>

```python
import cimtables
import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.getters.load import get_phase_loads

network = cimtables.load_model('feeder.cimtbl')  # a cim-graph FeederModel
load = next(obj for obj in network.graph[cim.EnergyConsumer].values() if obj.mRID == 'ld_n1')
print(get_phase_loads(load, 'kW', 'kVAr').total)  # PhasePower(p=1155.0, q=660.0)
```

CIM stores SI, and each getter converts once, through `cimtables.graph_write.get_qty`, to the unit you pass. A value
CIM leaves unset comes back as `None`, and a model the getter cannot read safely raises with the object's class
and mRID.

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } __User guide__

    ---

    Install it, load a small feeder and read its line, transformer, loads and terminals. Then units, per-unit
    bases, generator sign and time series.

    [:octicons-arrow-right-24: Quick start](guide/quickstart.ipynb)

-   :material-format-list-bulleted:{ .lg .middle } __Getter reference__

    ---

    Every getter by CIM concept: lines and wires, transformers, loads, sources and DER, topology and state, and the
    derived values under them.

    [:octicons-arrow-right-24: Getter reference](reference/index.md)

-   :material-code-braces:{ .lg .middle } __Developer docs__

    ---

    The map of the code: how an importer reaches CIM through `.cimtbl`, the rules every change keeps, how to write
    a getter and how the tests are laid out.

    [:octicons-arrow-right-24: Developer docs](developer/index.md)

</div>

## What is in core

| Part | What it is |
|---|---|
| Export getters | One function per CIM concept in `cimhub_core.getters`, returning floats and NamedTuples ([reference](reference/index.md)). |
| The `.cimtbl` contract | How a native importer writes `.cimtbl` text that [cimtables](https://pnnl-cim-tools.github.io/CIM-Tables/) turns into CIM ([developer](developer/cimtbl.md)). |
| Shapes | The canonical `.cimtbl` tables every importer emits, kept as examples in the package ([developer](developer/shapes.md)). |
| Time points | The Parquet files that hold schedule points beside the CIM XML ([guide](guide/time-points.md)). |
| Test harness | `cimhub_core.cimtbl_testing`: `cim_scope`, golden comparison and record-level diffs ([developer](developer/testing.md)). |

Core is one package of CIMHub. The converters themselves, and the landing page for all of them, are at
[CIMHub](https://pnnl-cim-tools.github.io/CIMHub/).

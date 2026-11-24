---
title: CIMHub OpenDSS
hide:
  - navigation
  - toc
---

<div class="ct-hero" markdown>

# OpenDSS decks <span class="ct-accent">to CIM and back</span>

<p class="ct-lede"><code>cimhub-opendss</code> reads an <a href="https://www.epri.com/pages/sa/opendss">OpenDSS</a> deck, writes it as
<code>.cimtbl</code> text, and builds an IEC CIM model (<code>cim18v17</code>) from that text. It also reads a CIM model
and writes a deck the engine compiles.</p>

[Quick start](guide/quickstart.ipynb){ .md-button .md-button--primary }
[What converts](guide/coverage.md){ .md-button }
[Developer docs](developer/index.md){ .md-button }

</div>

```python
from cimhub_opendss import DssReader, cim_to_dss, dss_to_cim

model = DssReader("IEEE13_CDPSM.dss").read_all()          # deck -> typed records
network = dss_to_cim(model, name="IEEE13_CDPSM")          # records -> .cimtbl -> CIM network
cim_to_dss(network, "out/IEEE13_CDPSM.dss")               # CIM network -> deck
```

`dss_to_cim` writes the model as `.cimtbl` text and builds the CIM network from that text, so the text you can read
and diff (pass `artifact_dir=` to keep it) is exactly what the model was built from. Values keep the deck's units;
the unit is in the column header. `cim_to_dss` reads the network back through the
[CIMHub core getters](https://pnnl-cim-tools.github.io/CIMHub/core/guide/getters/), which convert once to the unit
DSS expects.

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } __User guide__

    ---

    Install it, convert the IEEE 13-node feeder both ways, then import, export, round-trip checks and the list of
    DSS classes that convert.

    [:octicons-arrow-right-24: User guide](guide/index.md)

-   :material-table-search:{ .lg .middle } __Conversion reference__

    ---

    For each group of DSS classes, what each one becomes in CIM, how its properties map and where the two models
    differ.

    [:octicons-arrow-right-24: Conversion reference](reference/index.md)

-   :material-code-braces:{ .lg .middle } __Developer docs__

    ---

    The map of the code: reader and writer, importer, exporter, the LinkML schema, the tests and the rules a change
    keeps.

    [:octicons-arrow-right-24: Developer docs](developer/index.md)

-   :material-file-tree:{ .lg .middle } __Schema reference__

    ---

    Every DSS class and property the reader knows, generated from the LinkML schema.

    [:octicons-arrow-right-24: Schema reference](schema/index.md)

</div>

## What the package does

| Step | Call | Result |
|---|---|---|
| Read | `DssReader(path).read_all()` | a `DssModel` of typed records, with `Redirect`s followed and `Edit`s applied |
| Import | `dss_to_cim(model, name=...)` | a cim18v17 network, built from `.cimtbl` text |
| Export | `DssExporter().to_model(network)` | a `DssModel` again, from the CIM objects |
| Write | `DssWriter().write(model, path)` | a deck the reader, the importer and the engine read |

Only the reader and the writer touch the filesystem. The [quick start](guide/quickstart.ipynb) runs each step on a
real deck.

- **Geometry stays geometry.** A `LineGeometry` imports as a `WireConfiguration` and exports as a `LineGeometry`. No
  impedance matrix is computed in its place.
- **Nothing is guessed.** An unknown property, an unmapped value or an unresolved reference raises with the name of
  the DSS object. A DSS class no mapper reads is listed by count in the master `.cimtbl`, so it never disappears
  silently.
- **Units are not converted by hand.** Import copies values in the deck's units; export converts with the CIM
  quantity's `.to()`.

CIMHub OpenDSS is one package of CIMHub. The other converters, and the landing page for all of them, are at
[CIMHub](https://pnnl-cim-tools.github.io/CIMHub/). The shared layer under every converter is
[CIMHub core](https://pnnl-cim-tools.github.io/CIMHub/core/).

# Export: CIM to DSS

```python
from cimhub_opendss import DssExporter, DssWriter, cim_to_dss

cim_to_dss(network, "out/IEEE13_CDPSM.dss")                 # export and write in one call

model = DssExporter().to_model(network, name_source="name")  # records only, no files
DssWriter().write(model, "out/IEEE13_CDPSM.dss")
```

`network` is any cim18v17 network, for example the result of [`dss_to_cim`](import.md). The exporter reads it through
the getters in `cimhub_core` and returns a `DssModel`, the same shape `DssReader.read_all()` returns, so the deck
the writer produces reads back through the reader and the importer.

## Arguments to `to_model`

| Argument | Meaning |
|---|---|
| `name_source` | What a DSS name comes from: `'name'`, `'mrid'` or `'uri'`. Without it, `$CIMHUB_NAME_SOURCE`, else `'mrid'`. Any other value raises. |
| `circuit_source` | Which `EnergySource` becomes `New Circuit` when the network has several. Matched against the exported name. Default `"source"`. |

`cim_to_dss(network, destination, **opts)` passes `opts` to `to_model`. The writer creates the destination's folders
and sanitizes every name it writes. Two objects of one DSS class that end up with the same name raise, naming both.

Use `'uri'` when names must be stable and of fixed length across tools. `mRID` is a free-form string in cim18v17,
so it is not a safe join key; `uri()` is.

## What is written

The deck is written in this order: `Clear`, `Set defaultbasefreq`, `New Circuit`, `Set earthmodel`, the records,
`Set voltagebases` and `CalcVoltageBases`, one `Open` per open switch terminal, then `Buscoords`/`LatLongCoords`
naming the CSV files written beside the deck (`<stem>_buscoords.csv`).

Quantities are converted with `CIMUnit.to()` into the unit the DSS property expects. Line lengths (km for a lumped line) and wire
dimensions are written in metres.

Which CIM class becomes which DSS class, and where each slot comes from, is in the
[export mapping](../EXPORT_MAPPING.md). [Coverage](../coverage/overview.md) lists the classes.

## What raises

- Conducting equipment of a CIM class no exporter module handles: `no DSS export yet for {'<Class>': <count>}`.
- More than one `EnergySource` with none exported under `circuit_source`.
- A value a DSS property needs that the model does not hold, for example a `WireConfiguration` with no
  `WireSpacing`, or a wire with neither `Rdc` nor `Rac`.

## What does not survive a round trip

Some DSS and CIM distinctions are lossy by design. Every switch class other than `Fuse` and `Recloser` comes back
as a `LoadBreakSwitch`. A DSS protection setting with no home in cim18v17 is written as the engine's default. The
export mapping marks each such slot as `unset` or `rule`.

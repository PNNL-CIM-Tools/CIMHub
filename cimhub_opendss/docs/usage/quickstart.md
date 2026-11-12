# Quick start

## Install

```bash
pip install cimhub_opendss
```

## Convert a deck and back

The example uses the IEEE 13-node deck in the repository's tests
(`cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss`).

```python
from cimhub_opendss import DssReader, cim_to_dss, dss_to_cim

deck = "cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss"

model = DssReader(deck).read_all()                  # .dss -> typed records
network = dss_to_cim(model, name="IEEE13_CDPSM")    # records -> .cimtbl -> cim18v17 network
cim_to_dss(network, "out/IEEE13_CDPSM.dss")         # network -> deck; missing folders are created
```

`cim_to_dss` writes the deck at the path you give. A deck with bus coordinates also gets a CSV next to it
(`IEEE13_CDPSM_buscoords.csv`). The deck reads back through `DssReader` and compiles in the engine.

## The four steps

| Step | Call | Touches files |
|---|---|---|
| Read | `DssReader(path).read_all()` returns a `DssModel` | reads the deck and its `Redirect`s |
| Import | `dss_to_cim(model, name=...)` returns a cim18v17 network | writes `.cimtbl` artifacts to a temporary directory unless you pass `artifact_dir=` |
| Export | `DssExporter().to_model(network)` returns a `DssModel` | none |
| Write | `DssWriter().write(model, path)` | writes the deck |

Only the reader and the writer touch the filesystem. `dss_to_cim` and `cim_to_dss` chain the steps for you.

## Next

- [Import](import.md): the `.cimtbl` artifacts, `artifact_dir`, and what raises.
- [Export](export.md): names, the circuit source, and what raises.
- [Round trip](roundtrip.md): checking a converted deck against the original in the engine.
- To run the package's tests from a checkout, see the repository's `scripts/test-all.sh opendss`.

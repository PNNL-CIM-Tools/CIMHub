# Import: DSS to CIM

```python
from cimhub_opendss import DssReader, dss_to_cim

model = DssReader("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss").read_all()
network = dss_to_cim(model, name="IEEE13_CDPSM", artifact_dir="artifacts/IEEE13_CDPSM")
```

## What happens

1. `DssReader(path).read_all()` follows `Redirect`s and `~` continuation lines, evaluates RPN values, and returns a
   `DssModel` of typed records. `Edit`, dotted edits, `Open`/`Close` and batch edits are applied as the engine would.
2. `DssImporter(name).to_cimtbl(model)` walks the deck's topology once (with `cimtopology`), then runs one mapper per
   DSS class. Each mapper turns records into a `.cimtbl` document. It does not build CIM objects.
3. `dss_to_cim` writes the documents and cimtables binds them into a cim18v17 network. A last part,
   `buscoords.cimtbl`, is mapped from the bound network because it needs the equipment's terminals.

## Arguments

| Argument | Meaning |
|---|---|
| `name` | Required. The master document's `Model` and file stem. |
| `artifact_dir` | Keep the `.cimtbl` files here. Without it they go to a temporary directory that is removed after loading. |
| `authority` | The master's `Authority`. Defaults to `https://github.com/PNNL-CIM-Tools/CIMHub`. |
| `length_unit` | The per-length unit for a `LineCode` that has no units of its own and whose line sets none. It overrides the importer's magnitude check. |
| `network` | An existing cim18v17 network to bind onto, to merge several decks. |

To get the documents without binding them, call `DssImporter(name).to_cimtbl(model)`. It returns a `DocumentSet`
with a `master` and a list of `parts`.

## The artifacts

For the IEEE 13-node deck, `artifact_dir` holds one file per DSS table, plus the master:

```
IEEE13_CDPSM.cimtbl   bus.cimtbl        zip_fractions.cimtbl
linecode.cimtbl       xfmrcode.cimtbl   vsource.cimtbl        line.cimtbl
transformer.cimtbl    regcontrol.cimtbl load.cimtbl           capacitor.cimtbl
pvsystem.cimtbl       storage.cimtbl    buscoords.cimtbl
```

The master imports the parts in dependency order: catalogs (wire data, geometry, line codes, transformer codes)
before the equipment that uses them. A class with no records writes no part. Values keep the deck's units, and the
unit sits in the column header, for example `nominalVoltage (kV)`. The full file list, shapes and per-field
classification are in the [import mapping](../CIMTBL_MAPPING.md).

## What raises

The importer fails rather than guessing:

- A deck with no `New Circuit`, or with a second one.
- A DSS class name the schema does not know.
- A property the mapper has not classified, or one it classifies as raising when set (for example `Seasons` and
  `Ratings` on a `Line`, or `Z1`/`Z0` on a `Vsource`).
- A line code whose per-length magnitude does not fit one unit, when no `length_unit` is given.
- Equipment on a bus the topology walk does not reach.

Each case names the DSS object. The reason and the engine default behind each choice are in the
[import mapping](../CIMTBL_MAPPING.md).

## What is skipped, loudly

A DSS class no mapper reads (monitors, meters, shapes, and so on) is not an error. The master's comment lists it as
`not mapped: <Class> <count>`, so nothing disappears silently. See [coverage](../coverage/overview.md) for the list.

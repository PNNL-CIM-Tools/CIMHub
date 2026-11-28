# Installation

```bash
pip install --pre cimhub-raw
```

The package is imported as `cimhub_raw`. It needs Python 3.11 or newer. `--pre` is required for now: it is an alpha
release and depends on pre-release versions of `cimhub-core`, `cim-tables` and `cim-topology`.

With [uv](https://docs.astral.sh/uv/):

```bash
uv add --prerelease allow cimhub-raw
```

## What it installs

| Dependency | Why |
|---|---|
| `cimhub-core` | the export getters, the `.cimtbl` import contract, the record model (`GraphModel`) and the shared names |
| `cim-tables` | binds `.cimtbl` text into a CIM network |
| `cim-topology` | the topology walk that groups buses into substations and traces each bus's AREA |

`cimhub-core` brings in the CIM profile and graph packages, and the LinkML runtime that the record classes need.

## Check it works

```python
from cimhub_raw.raw34_reader import Raw34Reader

model = Raw34Reader("case.raw").read_all()
print({record_class.__name__: len(records) for record_class, records in model.graph.items()})
```

Replace `case.raw` with a RAW v34 case of yours: the reader reads REV 34 only. The three public cases used in this guide
are in the repository under
[`cimhub_raw/tests/cases`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/tests/cases).

## No engine needed

The converter does not need a power-flow program, and the package has no solve extra: nothing in the tests solves a
case. The [round trip](roundtrip.md) compares the records of the original and the exported case instead.

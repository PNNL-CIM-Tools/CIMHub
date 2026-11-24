# Installation

```bash
pip install --pre cimhub-opendss
```

The package is imported as `cimhub_opendss`. It needs Python 3.11 or newer. `--pre` is required for now: it is an
alpha release and depends on pre-release versions of `cimhub-core`, `cim-tables` and `cim-topology`.

With [uv](https://docs.astral.sh/uv/):

```bash
uv add --prerelease allow cimhub-opendss
```

## What it installs

| Dependency | Why |
|---|---|
| `cimhub-core` | the export getters, the `.cimtbl` import contract and the shared names |
| `cim-tables` | binds `.cimtbl` text into a CIM network |
| `cim-topology` | the topology walk that gives every bus its voltage |
| `pyyaml` | reads the LinkML schema that drives the reader and writer |

`cimhub-core` brings in the CIM profile and graph packages.

## The time-points extra

A `LoadShape` that a `Load`, `PVSystem`, `Storage` or `Generator` names as `yearly` carries a time series. CIM keeps
those points in a Parquet file beside the model, which needs `pyarrow` and `cim-builder`. The `time-points` extra
adds them (it is `cimhub-core[time-points]`):

```bash
pip install --pre "cimhub-opendss[time-points]"
```

Without the extra, `import cimhub_core.time_points` raises `ModuleNotFoundError`, so a call that passes `time_points=`
fails. A call that passes none logs one warning and drops the points. See
[Import](import.md#load-shapes-and-time-points).

## Check it works

```python
from cimhub_opendss import DssReader

model = DssReader("Master.dss").read_all()
print({cls.__name__: len(records) for cls, records in model.graph.items()})
```

Replace `Master.dss` with a deck of yours. The IEEE decks used in this guide are in the repository under
[`cimhub_opendss/tests/decks`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_opendss/tests/decks).

## The engine (optional)

The package does not run OpenDSS. The [round-trip checks](roundtrip.md) compile the original and the written deck in
the engine and compare the solved voltages. The tests do this with
[OpenDSSDirect.py](https://dss-extensions.org/OpenDSSDirect.py/) (`import opendssdirect`), which you install
yourself:

```bash
pip install opendssdirect.py
```

The repository's test environment pins `opendssdirect.py~=0.9.4`; the engine is only a test oracle there.

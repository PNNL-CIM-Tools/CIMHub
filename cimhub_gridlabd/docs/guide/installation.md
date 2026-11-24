# Installation

```bash
pip install --pre cimhub-gridlabd
```

The package is imported as `cimhub_gridlabd`. It needs Python 3.11 or newer. `--pre` is required for now: it is an
alpha release and depends on pre-release versions of `cimhub-core`, `cim-tables` and `cim-topology`.

With [uv](https://docs.astral.sh/uv/):

```bash
uv add --prerelease allow cimhub-gridlabd
```

## What it installs

| Dependency | Why |
|---|---|
| `cimhub-core` | the export getters, the `.cimtbl` import contract and the shared names |
| `cim-tables` | binds `.cimtbl` text into a CIM network |
| `cim-topology` | the topology walk that gives every bus its voltage |
| `linkml-runtime` | the dataclasses the reader fills and the writer reads |
| `pyyaml` | reads the LinkML schema that drives the reader and writer |

`cimhub-core` brings in the CIM profile and graph packages.

## The time-points extra

A `player`, and a `schedule` a load's base power names, carries a time series. CIM keeps those points in a Parquet
file beside the model, which needs `pyarrow` and `cim-builder`. The `time-points` extra adds them (it is
`cimhub-core[time-points]`):

```bash
pip install --pre "cimhub-gridlabd[time-points]"
```

Without the extra, `import cimhub_core.time_points` raises `ModuleNotFoundError`, so a call that passes
`time_points=` fails. A call that passes none logs one warning and drops the points. See
[Players and schedules](time-series.md).

## Check it works

```python
from cimhub_gridlabd.glm_reader import GlmReader

model = GlmReader("feeder.glm").read_all()
print({cls.__name__: len(records) for cls, records in model.graph.items()})
```

Replace `feeder.glm` with a model of yours. If it uses `${VSOURCE}` or another macro it does not define, pass the
value with `defines={"VSOURCE": "66395.28"}`, as `gridlabd -D VSOURCE=66395.28` would. The IEEE models used in this
guide are in the repository under
[`cimhub_gridlabd/tests/decks`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_gridlabd/tests/decks).

## The engine (optional)

The package does not run GridLAB-D. The [round-trip checks](roundtrip.md) solve the original and the written model
in the engine and compare the bus voltages. The tests do this with the `gridlabd` wheel from PyPI
(`import gridlabd`, in `tests/gridlabd_engine.py`), which you install yourself:

```bash
pip install "gridlabd~=6.0.0"
```

The repository's workspace declares it in the `dev` dependency group of the root `pyproject.toml` as
`gridlabd~=6.0.0`; it is only a test oracle there. Any GridLAB-D 6.0 install that runs the `.glm` works as well.

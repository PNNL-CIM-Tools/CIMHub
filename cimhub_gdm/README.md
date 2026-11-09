# cimhub_gdm

Imports an NLR grid-data-models (GDM) `DistributionSystem` into cim18v17.

GDM has no file format: its native model is typed pydantic objects with pint quantities. So this spoke is
**builder-native**. `GdmImporter().to_cim(system)` calls CIM-Builder's keyword methods directly and writes no
`.cimtbl` artifact. Tests compare the result with reviewed `.cimtbl` goldens (see the `cimtbl-import-contract`
skill, reference §9).

```python
from cimhub_gdm import gdm_to_cim, read_gdm

system = read_gdm("system.json")
system.name = system.name or "my_feeder"   # the CIM Model name; ditto leaves it empty
feeder_model = gdm_to_cim(system)
```

**Status (Phase 1):** the network shell (feeders, substations), buses, voltage sources and switches are mapped.
Every other GDM class raises as pending, naming the phase that ports it, so real systems don't import yet.
Time series are dropped with one warning.

The plan is [`docs/GDM_REWRITE_PLAN.md`](docs/GDM_REWRITE_PLAN.md).

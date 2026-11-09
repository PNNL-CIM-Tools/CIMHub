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

**Status (Phase 3):** the network shell (feeders, substations), buses, voltage sources, switches, lines (matrix,
sequence and geometry, with their wire and cable catalogs), loads, capacitors (with their controllers), transformers
(tank-configuration templates, center taps by lug, off-nominal taps) and regulators (with their tap changers and
controls) are mapped. DER and reactors raise as pending, naming the phase that ports them. Time series are dropped
with one warning. Requires the CIM-Builder `TransformerTankEnd` method (`add_transformer_tank_end`).

The plan is [`docs/GDM_REWRITE_PLAN.md`](docs/GDM_REWRITE_PLAN.md).

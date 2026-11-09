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

**Status (Phase 5, close-out):** the network shell (feeders, substations), buses, voltage sources, switches, lines (matrix,
sequence and geometry, with their wire and cable catalogs), loads, capacitors (with their controllers), transformers
(tank-configuration templates, center taps by lug, off-nominal taps), regulators (with their tap changers and
controls), DER (PV and batteries, with their inverter and battery AssetInfo) and series reactors are mapped. Inverter
controllers, the daily-timed capacitor controller and earthing switches raise as pending, naming what they wait for.
Time series are dropped with one warning. Requires the CIM-Builder `TransformerTankEnd` method
(`add_transformer_tank_end`) and `SeriesCompensatorBuilder`.

The output is cim18v17 only, and survives a cim18v17 XML round trip unchanged. An IEEE13-like reference system
(`tests/gdm_atoms.py`, `reference_system()`) is checked end to end against a reviewed golden. GDM fields with no
cim18v17 home are untranscribed (each listed in its class's `FIELDS`, logged at `DEBUG`); the gaps are in
[`docs/GDM_MAPPING.md`](docs/GDM_MAPPING.md) §10.

**Exporter (in progress, branch `gdm-exporter`).** `GdmExporter().to_model(network)` returns a GDM
`DistributionSystem`, reading every value through the core getters. `cim_to_gdm(network, path)` writes it as GDM
JSON (`write_gdm`). It exports feeders, substations, buses, sources, switches, fuses, reclosers, matrix and
sequence lines, loads, capacitors, transformers (center taps included) and regulators so far. The result writes and
solves through ditto's OpenDSS writer. DER, reactors and geometry lines raise `no GDM export yet`.
Plan: [`docs/EXPORT_PLAN.md`](docs/EXPORT_PLAN.md); spec: [`docs/EXPORT_MAPPING.md`](docs/EXPORT_MAPPING.md).
The tap assumptions both directions make, to review later: [`docs/TAP_ASSUMPTIONS.md`](docs/TAP_ASSUMPTIONS.md).

The plan is [`docs/GDM_REWRITE_PLAN.md`](docs/GDM_REWRITE_PLAN.md).

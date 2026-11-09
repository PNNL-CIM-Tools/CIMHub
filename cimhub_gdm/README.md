# cimhub_gdm

Imports an NLR grid-data-models (GDM) `DistributionSystem` into cim18v17.

GDM has no file format: its native model is typed pydantic objects with pint quantities. So this spoke is
**builder-native**. `GdmImporter().to_cim(system)` calls CIM-Builder's keyword methods directly and writes no
`.cimtbl` artifact. Tests compare the result with reviewed `.cimtbl` goldens (see the `cimtbl-import-contract`
skill, reference §9).

The plan is [`docs/GDM_REWRITE_PLAN.md`](docs/GDM_REWRITE_PLAN.md).

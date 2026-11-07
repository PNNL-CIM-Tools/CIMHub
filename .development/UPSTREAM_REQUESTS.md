# What CIMHub needs from upstream

Open requests to the libraries CIMHub builds on (invariant I9: file it here, never write a local stand-in).
Each entry says the repo, why CIMHub needs it, and how to reproduce it. Move an entry to "Closed" with the fixing
commit once it is verified from this repo.

| # | repo | ask | blocks |
|---|---|---|---|
| U1 | CIM-Graph | Import legacy profiles lazily. `import cimgraph.models` loads `cim17v40` (from `cimgraph.queries.sparql.get_all_nodes`) and `cimhub_2023` (from `cimgraph.models.feeder_model`) at module import: about 0.6 s and two profiles a cim18v17-only process never uses. | F1 exit check "importing `cimhub_core` loads no legacy profile". Until it is fixed, the check is a grep of `cimhub_*/src`. |
| U2 | CIM-Tables | The template shapes `transformer_template` and `transformer_by_template` fail with the working-tree `connectivity.py` (AutoTransformerEnd change, uncommitted 2026-11-07): `'xc_xfm1_end_1': a phases column needs a node/bus column to put the phases on`. A `TransformerTankEnd` on a `TransformerTankConfiguration` has no node by design. | `cimhub_core/tests/test_shapes.py` (3 tests) |
| U3 | CIM-Tables | (old R11) A `RegulatingControl` that monitors its own equipment's generated Terminal cannot be written: `RegulatingCondEq` is `serialize=False`, so neither row can come first. Accept `RegulatingCondEq` on the control row, or resolve references to generated Terminals after the file binds. | DSS/GLM capacitor and regulator controls with local voltage sensing |
| U4 | CIM-Tables or CIM-Builder | Upstream homes for derived math that is now in `cimhub_core/derived/`: star↔mesh impedance, short-circuit/no-load test → mesh/core admittance, trilateration of conductor distances → `XYSpacing`, ZIPV coefficients. | nothing; move upstream when accepted |
| U5 | CIM-Builder | About 15 builder modules (`new_base_voltage`, …) still import cimhub_2023 or cim18gad. Spokes use only the cim18v17 builders until they are ported. | GDM wave, if it needs one of them |
| U6 | CIM-Profiles | Native unit spellings that pint misreads (`sf`, `$` → `USD`) need a home in the shared unit registry. Today they are in the old core `units.py`, which is not carried over. | any spoke whose reader meets them |
| U7 | all five | Releases of cim-graph 0.6, cimtables, cim-builder, cimprofiles and cim-topology (with `cimtopology.core`; PyPI has only the old CIM-model-bound version) to PyPI, so the path sources can become version pins. | CI on GitHub, PyPI release, going public |

## Closed (verified from this repo, 2026-11-07)

- R1a: a `.cimtbl` suffix in a document name raises (`cimtables/document.py`).
- R7 `get_qty` (`cimtables/graph_write.py`), R8 `diff_models` (`cimtables/diff.py`).
- R10: mRIDs holding `#` seed distinct UUIDs (`lc_1p_#2acsr_#2n` vs `lc_1p_#2arv_#2n`).
- R12: type hints cached per class (`graph_write.type_hints = functools.cache(...)`).
- R14: `Qty(5, 'percent')` on a PerCent attribute stores `5.0`.

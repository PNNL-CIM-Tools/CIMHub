# What CIMHub needs from upstream

Open requests to the libraries CIMHub builds on (invariant I9: file it here, never write a local stand-in).
Each entry says the repo, why CIMHub needs it, and how to reproduce it. Move an entry to "Closed" with the fixing
commit once it is verified from this repo.

| # | repo | ask | blocks |
|---|---|---|---|
| U1 | CIM-Graph | Import legacy profiles lazily. `import cimgraph.models` loads `cim17v40` (from `cimgraph.queries.sparql.get_all_nodes`) and `cimhub_2023` (from `cimgraph.models.feeder_model`) at module import: about 0.6 s and two profiles a cim18v17-only process never uses. | F1 exit check "importing `cimhub_core` loads no legacy profile". Until it is fixed, the check is a grep of `cimhub_*/src`. |
| U4 | CIM-Tables or CIM-Builder | Upstream homes for derived math that is now in `cimhub_core/derived/`: star↔mesh impedance, short-circuit/no-load test → mesh/core admittance, conductor distances → XY positions (`derived/spacing.py`, getters G5), ZIPV coefficients, a 1- or 2-phase line's phase matrix from sequence values and the n-conductor balanced matrix (`derived/sequence.py`, S2, S3), Kron reduction of grounded conductors (`derived/kron.py`, getters G2). | nothing; move upstream when accepted |
| U5 | CIM-Builder | About 15 builder modules (`new_base_voltage`, …) still import cimhub_2023 or cim18gad. Spokes use only the cim18v17 builders until they are ported. | GDM wave, if it needs one of them |
| U6 | CIM-Profiles | Native unit spellings that pint misreads (`sf`, `$` → `USD`) need a home in the shared unit registry. Today they are in the old core `units.py`, which is not carried over. | any spoke whose reader meets them |
| U7 | all five | Releases of cim-graph 0.6, cimtables, cim-builder, cimprofiles and cim-topology (with `cimtopology.core`; PyPI has only the old CIM-model-bound version) to PyPI, so the path sources can become version pins. | CI on GitHub, PyPI release, going public |
| U8 | CIM-Profiles (CIM WG13) | `RotatingMachine.phaseConnection` (`PhaseShuntConnectionKind`), as `EnergyConsumer` and `PowerElectronicsConnection` have. SynchronousMachine has none, so a delta OpenDSS Generator is written as `earthing=false` (S4b-5), which an ungrounded wye would also be. | DSS exporter: a delta machine back to `conn=delta` without relying on DSS having no ungrounded-wye machine |
| U9 | CIM-Tables | A `phases` column on a class with no `<Class>Phase` child (SeriesCompensator) should set `Terminal.phases` only, as on a TransformerEnd, instead of raising. Today `reactor.cimtbl` writes `Update Table Terminal: mRID, phases` for the generated Terminals. | nothing; the Update works |
| U10 | CIM-Tables | Tell a balanced three-phase device from three separate A, B, C phases. Today `phases=ABC` always writes three `<Class>Phase` children, which in CIM (and the OpenDSS CIM export) means a per-phase device; a balanced one has none. CIMHub writes a blank `phases` cell for balanced ABC (`cimhub_core.cimtbl.phases_cell`), so its Terminals lose `phases=ABC`. Ask: a spelling (a column or a value) that sets `Terminal.phases` without children; U9 (SeriesCompensator) would fall out of it. | nothing; Terminal.phases of balanced devices is unset until then |
| U11 | CIM-Tables | The Terminals a set of documents makes, without binding: the inverse of the connectivity columns (`node`/`node1`/`node2` → Terminal 1/2 of the row; a TransformerEnd's `node` → Terminal `endNumber` of its transformer), part of the planned "connectivity inverse". A spoke's coordinates part needs each piece of equipment's Terminal buses (DSS S5-2). Until then `cimhub_core.cimtbl.document_terminals` does it on `CONNECTIVITY_COLUMNS`; delete it once this lands. | nothing; core's stand-in works |
| U12 | CIM-Tables | `get_qty` on a declared power base: a transformer percent read on another S at the From winding's own voltage (e.g. `get_qty(mesh, "x", "percent", power_base=...)`). DSS and GLM put every percent on winding 1's kVA and RAW on the system MVA, while CIM stores each on its From winding's `baseU²/baseS`. Until then `getters/transformer.py` moves the stored percent itself, z × S_new/S_old and y × S_old/S_new (powers only, no local `z_base`; getters G6). | nothing; the getter's power ratio works |

## Closed (verified from this repo, 2026-11-07)

- U3 (2026-11-08): own-terminal control. CIM-Tables' additive `Update` breaks the cycle: the compensator row,
  then the control naming its generated `cap_<name>_T1`, then `Update LinearShuntCompensator: mRID=...,
  RegulatingControl=...`; `RegulatingControl.RegulatingCondEq` binds as the compensator (S4a CapControl).
- U2 (2026-11-08): the template shapes bind. CIM-Tables `8fc537f` keeps a TransformerEnd's phases on its Terminal
  only, so a `phases` column on a `TransformerTankEnd` (which has none on a configuration) raises by design. The
  fix was in core: `shapes/transformer_template.cimtbl` no longer gives its tank ends phases; the instance's
  `PowerTransformerEnd` carries them.

- R1a: a `.cimtbl` suffix in a document name raises (`cimtables/document.py`).
- R7 `get_qty` (`cimtables/graph_write.py`), R8 `diff_models` (`cimtables/diff.py`).
- R10: mRIDs holding `#` seed distinct UUIDs (`lc_1p_#2acsr_#2n` vs `lc_1p_#2arv_#2n`).
- R12: type hints cached per class (`graph_write.type_hints = functools.cache(...)`).
- R14: `Qty(5, 'percent')` on a PerCent attribute stores `5.0`.

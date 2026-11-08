# Committed RAW v34 cases

Only cases with a documented public origin live here (split-readiness rule 4). Other cases are read from
`CIMHUB_RAW_SWEEP_DIR` by the sweep test and are never committed (`.development/RAW_REWRITE_PLAN.md` §5).

| case | file | origin | license / terms | local edits |
|---|---|---|---|---|
| IEEE 14 bus | `IEEE14/IEEE_14_bus.raw` | IEEE 14-bus test case from the University of Washington Power Systems Test Case Archive (title line: `08/19/93 UW ARCHIVE ... IEEE 14 BUS TES`), written as RAW v34 by PSS/E `rawd34` (header comment, Dec 2025) | public test case | none since the v34 conversion; copied from CIMHub_2_0 `test_data` on 2026-11-08 |
| WECC 240 bus | `WECC240/240busWECC_2018_PSS.raw` | NREL reduced 240-bus WECC model, V0.2 (H. Yuan, R. S. Biswas, J. Tan, Y. Zhang, IEEE PES T&D 2020); the file states that it contains no CEII | public release by NREL | none; copied from CIMHub_2_0 `test_data` on 2026-11-08 |

**To confirm before commit:** the URL each file was downloaded from, and the IEEE14 v34 conversion's provenance.

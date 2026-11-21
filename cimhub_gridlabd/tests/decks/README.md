# Vendored GridLAB-D decks

Small public decks used by the reader, topology and sweep tests. The other Powergrid-Models GLM decks (IEEE123
transactive, the larger PNNL taxonomy feeders) are not vendored: set `CIMHUB_GLM_DECKS` to a directory with the same
layout (`PNNL/orig_R5-12.47-3.glm`) to run their tests.

Copied 2026-11-09, unmodified, from GridAPPS-D Powergrid-Models `models/feeders/GridLABD/` at commit `1bec2d3a`
(<https://github.com/GRIDAPPSD/Powergrid-Models>). **Licenses to confirm at release review** (split-readiness rule 4):
the Powergrid-Models checkout carries no license file.

| deck | origin |
|---|---|
| `IEEE/IEEE13_cdpsm.glm`, `IEEE/IEEE13_assets.glm`, `IEEE/IEEE123.glm` | IEEE PES distribution test feeders, exported to GLM by the GridAPPS-D CIMHub Java tools (<https://github.com/GRIDAPPSD/CIMHub>) |
| `IEEE/IEEE13_houses.glm` | the IEEE 13-node feeder with GridLAB-D houses, as distributed in Powergrid-Models |
| `PNNL/orig_GC-12.47-1.glm`, `PNNL/orig_R1-12.47-3.glm` | PNNL taxonomy prototypical feeders (GridLAB-D `models/taxonomy_feeders`, Battelle) |

Known deck defects (the tests list them; the decks are not edited):

- `IEEE/IEEE13_cdpsm.glm`, `IEEE13_assets.glm`, `IEEE123.glm` use `${VSOURCE}` without defining it: pass
  `defines={"VSOURCE": "66395.28"}`, as `gridlabd -D` would.
- `IEEE/IEEE13_houses.glm` rates its bus-634 center-tap transformers for a 2401 V primary on the 480 V bus, so the
  topology walk stops on it.
- Every PNNL taxonomy meter has `nominal_voltage 480`, whatever bus it is on.

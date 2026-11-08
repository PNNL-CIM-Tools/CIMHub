# Vendored OpenDSS decks

Small public decks used by the reader, topology and sweep tests. Large decks (EPRI J1, IEEE8500, IEEE9500,
IEEE123_PV, ...) are not vendored: set `CIMHUB_DSS_DECKS` to a directory with the same layout to run their tests.

Copied 2026-11-07 from the CIMHub_2_0 test data, without the CIMHub 1.x `*_uuids.dat`, `convert.json` and meter
export files. No other local edits. **Origins to confirm at release review** (split-readiness rule 4).

| deck | origin | license |
|---|---|---|
| `IEEE/IEEE13_original`, `IEEE/IEEE37`, `IEEE/IEEE123`, `IEEE/IEEE4_xfmrs` | IEEE PES Distribution Test Feeders, as distributed with OpenDSS (EPRI, <https://sourceforge.net/p/electricdss/>) | OpenDSS: BSD-3-Clause |
| `IEEE/IEEE13_CDPSM`, `IEEE/IEEE13_assets` (copied 2026-11-07, for the wire and geometry catalogs) | IEEE 13-node feeder extended for CIM profile testing, GridAPPS-D CIMHub (<https://github.com/GRIDAPPSD/CIMHub>) | BSD-3-Clause |
| `EPRI/K1`, `EPRI/M1` | EPRI DPV test feeders, baseline (unmodified), <http://dpv.epri.com/> | EPRI test circuit terms |

K1 and M1 `Redirect` files with the wrong file-name case for a case-sensitive filesystem. The reader resolves
case-insensitively; the engine does not, so the engine tests skip them.

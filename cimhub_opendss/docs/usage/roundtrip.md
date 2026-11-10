# Round trip

A round trip imports a deck to CIM and exports it back to a new deck. The check that matters is that the engine
solves both decks to the same answer.

## Run it yourself

```python
from cimhub_opendss import DssReader, cim_to_dss, dss_to_cim

deck = "cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss"
network = dss_to_cim(DssReader(deck).read_all(), name="IEEE13_CDPSM")
cim_to_dss(network, "out/IEEE13_CDPSM.dss")

written = DssReader("out/IEEE13_CDPSM.dss").read_all()   # the written deck reads back
```

To compare the two decks in the engine, compile each with [OpenDSSDirect.py](https://dss-extensions.org/) and
compare node voltages and element powers. The test helpers in `cimhub_opendss/tests/engine_compare.py` do this with
controls off and a tight tolerance, so both decks converge to one answer from their different starting points.

## What the tests check

| Test file | Checks |
|---|---|
| `test_export_decks.py` | Whole decks through import and export: power flow parity in the engine, bus coordinates, and idempotence (a second pass changes nothing). |
| `test_cimtbl_sweep.py` | Every deck (a `roundtrip` test) imports and binds, or stops at a named, expected error. |
| `test_dss_to_cimtbl.py` | The IEEE 13-node `.cimtbl` artifacts match the committed goldens. |
| `test_export_*.py` | Each exporter module, from small CIM networks. |

Parity compares against the original deck minus the settings the CIM model does not hold. Those settings are listed
per deck in `test_export_decks.py` (for example `Transformer.taps` or `Load.Vminpu/Vmaxpu`), so a loss is explicit.

## Running the tests

From a checkout, one pytest process per package:

```bash
scripts/test-all.sh opendss                  # the package's tests
scripts/test-all.sh opendss -- --roundtrip   # also the slow whole-deck tests
```

Slow decks carry the `roundtrip` pytest marker and are skipped unless you pass `--roundtrip`. The vendored decks
(`cimhub_opendss/tests/decks/`, origins in its README) cover the IEEE 4, 13, 37 and 123-node feeders and EPRI K1 and
M1. Larger decks (EPRI J1, IEEE 8500, IEEE 9500) are not vendored. Set `CIMHUB_DSS_DECKS` to a directory with the
same layout, for example `IEEE/IEEE8500/Master.dss`, and their tests run; otherwise they skip.

To regenerate a golden after an intended change, set `CIMHUB_UPDATE_GOLDENS=1` and review the diff.

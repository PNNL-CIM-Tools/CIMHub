# Round trip

A round trip imports a deck to CIM and exports it back to a new deck. The check that matters is that the engine
solves both decks to the same answer.

## Run it yourself

```python
import tempfile
from pathlib import Path

from cimhub_opendss import DssReader, cim_to_dss, dss_to_cim

original = Path("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss")
written = Path(tempfile.mkdtemp()) / "IEEE13_CDPSM.dss"

network = dss_to_cim(DssReader(original).read_all(), name="IEEE13_CDPSM")
cim_to_dss(network, written, name_source="name")

print(len(DssReader(written).read_all().graph))   # the written deck reads back
```

`name_source="name"` keeps the deck's own names, so the two decks compare element by element. The default, `'mrid'`,
also reads back, but a name that the importer lowercased or prefixed (`ld_611`) is written as it was compiled.

## Compare voltages in the engine

Compile each deck with [OpenDSSDirect.py](https://dss-extensions.org/OpenDSSDirect.py/) ([installation](installation.md))
and compare the solved node voltages. Turn controls off and tighten the tolerance, so both decks converge to one
answer from their different starting points. Measure the difference against the bus's base voltage, because a node
near zero (a floating neutral) would make a relative error meaningless.

```python
import tempfile
from pathlib import Path

import opendssdirect as dss

from cimhub_opendss import DssImporter, DssReader, cim_to_dss

dss.Basic.AllowChangeDir(False)   # Compile would otherwise change the process's directory

original = Path("cimhub_opendss/tests/decks/IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss")
written = Path(tempfile.mkdtemp()) / "IEEE13_CDPSM.dss"
network = DssImporter("IEEE13_CDPSM").to_cim(DssReader(original).read_all())
cim_to_dss(network, written, name_source="name")


def solved_voltages(deck):
    """({node: complex volts}, {bus: base volts, line to neutral}) after a no-control solve."""
    dss.Text.Command("Clear")
    dss.Text.Command(f"Compile [{deck.resolve()}]")
    dss.Text.Command("Set controlmode=off tolerance=1e-10 maxiterations=500")
    dss.Solution.Solve()
    assert dss.Solution.Converged()
    values = dss.Circuit.AllBusVolts()
    nodes = [name.lower() for name in dss.Circuit.AllNodeNames()]
    volts = {node: complex(values[2 * i], values[2 * i + 1]) for i, node in enumerate(nodes)}
    bases = {}
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        bases[bus.lower()] = dss.Bus.kVBase() * 1000
    return volts, bases


before, bases = solved_voltages(original)
after, _ = solved_voltages(written)
assert before.keys() == after.keys()
worst = max(abs(after[node] - before[node]) / bases[node.split(".")[0]] for node in before)
print(f"{len(before)} nodes, largest difference {worst:.2%} of the bus base voltage")
```

For IEEE 13 this prints `57 nodes, largest difference 0.06% of the bus base voltage`. The package's own tests use a
tolerance of 0.1 % of the base voltage.

The difference is not zero because the CIM model does not hold every setting of the deck. In IEEE 13 the loads'
`Vminpu` and `Vmaxpu` are not in CIM, and the exporter writes the loads' kV as 2.40178 where the deck says 2.4. The
settings the tests copy from the original into the written deck before solving are:

| Setting | Why it is not in the model |
|---|---|
| `Load.Vminpu`, `Load.Vmaxpu` | below `Vminpu` the engine turns a load into constant impedance |
| `Transformer.ppm_antifloat` | the engine's 1 ppm default against the deck's setting moves a floating delta |
| `Transformer.taps`, `Capacitor.states` | an in-deck `Solve` moves them, and the importer reads the deck's text |

## What the tests check

The package's tests run from a checkout (`cimhub_opendss/tests/`). The engine-based ones need `opendssdirect`.

| Test file | Checks |
|---|---|
| `test_export_decks.py` | Whole decks through import and export. Power-flow parity in the engine (`engine_compare.assert_same_power_flow`), that each deck's bus coordinates come back as the engine had them, and idempotence: exporting the exported deck again gives byte-identical text. |
| `test_cimtbl_sweep.py` | Every deck either binds, with every equipment's `BaseVoltage` equal to its nodes', or stops at a named, expected error. An unlisted stop fails, and so does a listed stop that now binds. |
| `test_dss_to_cimtbl.py` | The IEEE 13-node `.cimtbl` artifacts match the committed goldens in `tests/goldens/`. |
| `test_cimtbl_*.py` | Each mapper against its atoms (`tests/atoms/<table>/`), many of them also compiled in the engine to check a value. |
| `test_export_*.py` | Each exporter module from small CIM networks, comparing the engine's state (buses, `YPrim`, node voltages) of the original and the written atom (`engine_compare.assert_same_engine_state`). |
| `tests/cross_format/` (repository root) | A GridLAB-D deck through CIM to a DSS deck, and the IEEE 13-node feeder in both formats. |

Parity compares against the original deck minus the settings in the table above. Each deck's list is in
`test_export_decks.py`, so a loss is explicit.

## Running the tests

From a checkout, one pytest process per package:

```bash
scripts/test-all.sh opendss                  # the package's tests
scripts/test-all.sh opendss -- --roundtrip   # also the slow whole-deck tests
```

Whole-deck tests carry the `roundtrip` pytest marker and are skipped unless you pass `--roundtrip`. The vendored decks
(`cimhub_opendss/tests/decks/`, origins in its README) are the IEEE 4, 13 and 37 node and 123-bus feeders, the EPRI K1
and M1 feeders, and the IEEE 13-node variants with assets. K1 and M1 stop at import (a `Line` whose `phases` differ
from its `LineCode`'s), and the engine cannot compile them here, so they are in the sweep only as expected stops.
Larger decks (EPRI J1, IEEE 8500, IEEE 9500) are not vendored. Set `CIMHUB_DSS_DECKS` to a directory with the same
layout, for example `IEEE/IEEE8500/Master.dss`, and their tests run; otherwise they skip.

To regenerate a golden after an intended change, set `CIMHUB_UPDATE_GOLDENS=1` and review the diff.

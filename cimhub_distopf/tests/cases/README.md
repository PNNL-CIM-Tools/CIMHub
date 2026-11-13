# DistOPF test cases

Copied unchanged from the public `distopf` 1.1.0 wheel on PyPI (https://pypi.org/project/distopf/1.1.0/),
`distopf/cases/csv/<case>/`. License: MIT, Copyright (c) 2025, Battelle Memorial Institute (the wheel's
`LICENSE.md`). No local edits.

| case | what it exercises |
|---|---|
| `ieee13` | IEEE 13-node feeder: lines, switch, transformer, three regulators, two capacitors |
| `ieee123_30der` | IEEE 123-node feeder with 30 DER (PV, diesel, PV + battery), two batteries, schedules |
| `triplex_pv` | split-phase (s1/s2) secondaries with PV |

The other 22 cases in the wheel are the importer's sweep corpus; they are read from an installed or downloaded
wheel, not committed.

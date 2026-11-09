# Branch atoms (slice R1)

Hand-built by the CIMHub team in the RAW v34 format; synthetic, no real network. They cover what neither public
case (IEEE14, WECC240) has. Each is the two-bus node-breaker atom's section layout with its own data and no
SUBSTATION data.

| atom | content |
|---|---|
| `line_shunts.raw` | two 115 kV buses and one branch 1-2 with line shunts GI + jBI = 0.01 - j0.05 and BJ = 0.02, RATE1/RATE2 = 100/120 MVA, MET = 2 and LEN = 12.5 |
| `switches.raw` | four 138 kV buses and three system switching devices: STYPE 1 (closed, rated 200 "current as MVA" with NXFRAT = 1), 2 (open) and 3 (normally open) |
| `multi_section_line.raw` | four 230 kV buses; a multi-section line 1-4 `&1` through dummy buses 2 and 3 (its last section is entered as 4-3), and a parallel ordinary line 1-4 circuit 2 |

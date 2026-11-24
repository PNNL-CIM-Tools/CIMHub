# CIMHub

CIMHub converts power-system model formats to and from the Common Information Model (CIM, IEC 61968/61970). It
targets one CIM profile, **cim18v17**, and follows a hub-and-spoke design: each native format is a spoke package,
CIM is the hub, and any two formats convert through CIM.

Importing and exporting use different paths:

- **Import.** A spoke reads its native file into typed native records, maps them to `.cimtbl` text (one file per
  native table, values copied verbatim with the source unit in the column header), and
  cimtables builds the CIM model from that text. Spoke code never
  constructs CIM objects, so the `.cimtbl` files are a reviewable record of exactly what was mapped.
- **Export.** A spoke reads the CIM model through the getters in `cimhub_core.getters`, which return plain floats
  in the unit the caller asks for, and writes native records. Each exporter converts units with `CIMUnit.to()`.
- **GDM** is the exception. A grid-data-models `DistributionSystem` is a set of typed Python objects, not a file,
  so its importer calls CIM-Builder directly and writes no `.cimtbl`.

## Packages and status

| Package | Format | Import | Export |
|---|---|---|---|
| `cimhub-core` | shared layer: `.cimtbl` contract, getters, shapes, test harness | | |
| `cimhub-opendss` | OpenDSS (`.dss`) | yes | yes |
| `cimhub-raw` | PSS/E RAW v34 | yes (multi-terminal DC, GNE and induction machine raise) | yes (AC equipment; a class with no export module raises) |
| `cimhub-gdm` | grid-data-models `DistributionSystem` | yes | yes (see the package README for limits) |
| `cimhub-gridlabd` | GridLAB-D (`.glm`) | yes | yes |

MATPOWER and DistOPF are planned and are not in this repository yet. Each package README lists what
that package maps and what raises.

## Install

```bash
pip install --pre cimhub-opendss      # also installs cimhub-core
```

Python 3.11 or later. All five packages are on PyPI as 2.1 alphas, hence `--pre`.

To work on the code, clone the repository and use [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/PNNL-CIM-Tools/CIMHub.git
cd CIMHub
uv sync
```

## Quickstart

Import an OpenDSS deck into CIM, then export it back to a deck. The deck is the IEEE 13-node feeder in the
repository's test data.

```python
from cimhub_opendss import DssReader, cim_to_dss, dss_to_cim

deck = "cimhub_opendss/tests/decks/IEEE/IEEE13_original/IEEE13Nodeckt.dss"
network = dss_to_cim(DssReader(deck).read_all(), name="IEEE13", artifact_dir="ieee13_cimtbl")
cim_to_dss(network, "ieee13_export.dss")
```

`ieee13_cimtbl/` then holds `IEEE13.cimtbl` (the master) and one `.cimtbl` file per DSS class. Leave out
`artifact_dir` to use a temporary directory.

## Documentation

| Document | Contents |
|---|---|
| [cimhub_core/docs/developer/architecture.md](cimhub_core/docs/developer/architecture.md) | hub and spokes, the import and export paths, the invariants |
| [cimhub_core/docs/developer/converter-api.md](cimhub_core/docs/developer/converter-api.md) | the reader, writer, importer and exporter classes and the `<fmt>_to_cim` functions |
| [cimhub_core/docs/developer/units.md](cimhub_core/docs/developer/units.md) | units on import and export |
| [cimhub_core/docs/developer/testing.md](cimhub_core/docs/developer/testing.md) | atoms, goldens and the test types |
| [cimhub_opendss/docs/CIMTBL_MAPPING.md](cimhub_opendss/docs/CIMTBL_MAPPING.md) | OpenDSS to `.cimtbl` mapping spec |
| [cimhub_opendss/docs/EXPORT_MAPPING.md](cimhub_opendss/docs/EXPORT_MAPPING.md) | CIM to OpenDSS export spec |
| [cimhub_raw/docs/CIMTBL_MAPPING.md](cimhub_raw/docs/CIMTBL_MAPPING.md) | PSS/E RAW v34 to `.cimtbl` mapping spec |
| [cimhub_gdm/docs/GDM_MAPPING.md](cimhub_gdm/docs/GDM_MAPPING.md), [EXPORT_MAPPING.md](cimhub_gdm/docs/EXPORT_MAPPING.md) | GDM import and export specs |

User-facing OpenDSS documentation is the site configured in `cimhub_opendss/mkdocs.yml`.

## Contributing

Read [CLAUDE.md](CLAUDE.md) first. It lists the invariants every change is checked against and the skills in
[.claude/skills/](.claude/skills/) that hold the detailed rules (style, units, conductor geometry, the `.cimtbl`
contract, tests). Humans can read those files too.

```bash
uv sync
scripts/test-all.sh            # one pytest process per package
scripts/test-all.sh core       # one package
scripts/leak-gate.sh           # must print "leak-gate: clean" before every commit
```

Run the packages' tests one process each: cimtables sets the CIM profile process-wide, so suites must not share an
interpreter. Set `CIMHUB_UPDATE_GOLDENS=1` to regenerate goldens, and review the diff.

## License

BSD 3-Clause. See [LICENSE](LICENSE). Contributors are listed in [AUTHORS](AUTHORS).

## Attribution and disclaimer

This software was created under a project sponsored by the U.S. Department of Energy's Office of Electricity, an
agency of the United States Government. Neither the United States Government nor the United States Department of
Energy, nor Battelle, nor any of their employees, nor any jurisdiction or organization that has cooperated in the
development of these materials, makes any warranty, express or implied, or assumes any legal liability or
responsibility for the accuracy, completeness, or usefulness or any information, apparatus, product, software, or
process disclosed, or represents that its use would not infringe privately owned rights.

PACIFIC NORTHWEST NATIONAL LABORATORY\
operated by BATTELLE\
for the UNITED STATES DEPARTMENT OF ENERGY\
under Contract DE-AC05-76RL01830

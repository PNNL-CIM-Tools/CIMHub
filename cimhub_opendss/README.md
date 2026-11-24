# cimhub-opendss

OpenDSS converter for CIMHub: OpenDSS `.dss` decks to and from CIM (cim18v17). `DssReader` parses a deck into native
records. `DssImporter` maps them to `.cimtbl` text (one file per DSS class, values copied verbatim in the deck's
units), and cimtables builds the CIM model from that text. `DssExporter` reads a CIM model through the
`cimhub-core` getters and `DssWriter` writes a deck that `DssReader` and the importer read back.

```bash
pip install --pre cimhub-opendss      # also installs cimhub-core
```

Python 3.11 or later.

## Quickstart

```python
from cimhub_opendss import DssReader, cim_to_dss, dss_to_cim

# IEEE13Nodeckt.dss and IEEELineCodes.dss: cimhub_opendss/tests/decks/IEEE/IEEE13_original/ in the repository
network = dss_to_cim(DssReader("IEEE13Nodeckt.dss").read_all(), name="IEEE13", artifact_dir="ieee13_cimtbl")
cim_to_dss(network, "ieee13_export.dss")
```

- `dss_to_cim(model, *, name, authority=..., length_unit=None, network=None, artifact_dir=None)` returns the CIM
  network. `name` is the model name and the master file stem. Without `artifact_dir` the `.cimtbl` files go to a
  temporary directory that is removed after loading. `length_unit` overrides the deck's line length unit.
- `cim_to_dss(network, destination, **opts)` writes the deck. Options go to `DssExporter().to_model`:
  `name_source` (`'name'`, `'mrid'` or `'uri'`; default `$CIMHUB_NAME_SOURCE`, else `'mrid'`) and
  `circuit_source`, the EnergySource to write as `New Circuit` when the model has several.

## What is supported

| DSS class | Import | Export |
|---|---|---|
| Circuit / Vsource | yes | yes |
| Line (matrix, sequence and geometry impedance), LineCode, LineGeometry, LineSpacing, WireData, CNData, TSData | yes | yes |
| Transformer, XfmrCode, RegControl | yes | yes |
| Load, Capacitor, CapControl | yes | yes |
| PVSystem, Storage, Generator | yes | yes |
| Reactor | yes | yes |
| Bus coordinates | yes | yes |

The master `.cimtbl` lists, in a comment, every DSS class in the deck that no mapper reads yet, with its record
count. The exporter raises, naming the classes and counts, when the CIM model holds conducting equipment of a class it
does not export. Unknown fields, unmapped enumerations and unresolved references raise on import. A deck without a
`New Circuit`, or with a second one, raises.

## Documentation

- [OpenDSS to `.cimtbl` mapping spec](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_opendss/docs/CIMTBL_MAPPING.md)
- [CIM to OpenDSS export spec](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_opendss/docs/EXPORT_MAPPING.md)
- [Documentation site source](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_opendss/docs/index.md)
- [CIMHub architecture](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/developer/architecture.md) and [converter API](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_core/docs/developer/converter-api.md)

BSD 3-Clause. Source and issues: <https://github.com/PNNL-CIM-Tools/CIMHub>.

## License and attribution

BSD 3-Clause. See [LICENSE](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_opendss/LICENSE). Contributors are listed in [AUTHORS](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/AUTHORS).

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

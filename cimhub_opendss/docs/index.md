# CIMHub OpenDSS

Converts [OpenDSS](https://www.epri.com/pages/sa/opendss) decks to and from CIM (IEC 61968/61970, the `cim18v17`
profile).

- **Import:** `DssReader` parses a deck into typed records. The importer maps the records to `.cimtbl` text, and
  [cimtables](https://pypi.org/project/cim-tables/) binds that text into a CIM network. The importer never builds CIM
  objects itself.
- **Export:** `DssExporter` reads a CIM network through the shared getters in `cimhub_core` and returns records.
  `DssWriter` writes them as a deck the engine compiles.
- **Units:** the `.cimtbl` column headers carry the source units (`ratedS (kVA)`, `r (ohm/km)`), and the exporter
  converts with `CIMUnit.to()`. No spoke code multiplies by `1e3`.
- **Geometry stays geometry:** a `LineGeometry` imports as a `WireConfiguration` and exports back as a
  `LineGeometry`. No impedance matrix is computed in its place.

## Where to go

| If you want to | Read |
|---|---|
| Convert a deck in five minutes | [Quick start](usage/quickstart.md) |
| Know what the importer writes and what it refuses | [Import](usage/import.md), [Import mapping](CIMTBL_MAPPING.md) |
| Write a deck from a CIM network | [Export](usage/export.md), [Export mapping](EXPORT_MAPPING.md) |
| Check that a conversion preserved the model | [Round trip](usage/roundtrip.md) |
| See which DSS classes convert today | [Coverage](coverage/overview.md) |
| Look up a DSS property | [Schema reference](schema_ref/index.md) |

## Install

```bash
pip install cimhub_opendss
```

The package pulls in `cimhub-core`, `cim-tables` and `cim-topology`. It needs Python 3.11 or later.

## Contributor note: building this site

The schema reference is generated from the LinkML schema and is never committed (`docs/.gitignore` lists
`schema_ref/`). From `cimhub_opendss/`:

```bash
# 1. generate the schema reference
uvx --with-requirements docs/requirements-mkdocs.txt --from linkml gen-doc \
    -d docs/schema_ref src/cimhub_opendss/schema/linkml/opendss.yaml

# 2. build the site; --strict fails on any warning
uvx --with-requirements docs/requirements-mkdocs.txt mkdocs build --strict -d /tmp/dss-site
```

`uvx` keeps the documentation tools out of the workspace's `uv.lock`. Use `mkdocs serve` in place of `mkdocs build` to
preview.

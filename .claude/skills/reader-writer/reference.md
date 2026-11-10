# Readers and writers: reference

Companion to [SKILL.md](SKILL.md). Code goes in `cimhub_<fmt>/src/cimhub_<fmt>/reader/`, `writer/`,
`importer/cimtbl/` and `exporter/`; tests in `cimhub_<fmt>/tests/`. `DssReader` is the reference reader.

## Before you start

- The LinkML schema exists with complete annotations (`linkml-native-schema` skill).
- You have small public sample files (`split-readiness` skill: documented public origin).
- Note the file structure: one file or many, sections, record delimiters, quoting, comment markers, multi-line
  records, empty-field meaning.

Example (PSS/E RAW):

```
0, 100.00, 34, 0, 1, 60.00     / case identification
1,'BUS_001',138.0,1,1,...      / bus record: comma-separated, single-quoted strings
0 / END OF BUS DATA            / section terminator
```

## Reader skeleton

```python
from pathlib import Path

from cimhub_core import FormatReader, GraphModel

from cimhub_raw.schema import raw as schema


class RawParseError(ValueError):
    def __init__(self, message: str, path: Path, line_number: int, line: str):
        super().__init__(f"{path}:{line_number}: {message}\n  {line}")


class RawReader(FormatReader):
    def __init__(self, source: str | Path) -> None:
        self.source = Path(source)        # bind only; no parsing here

    def read_all(self) -> GraphModel:
        model = GraphModel()
        lines = self.source.read_text(encoding="utf-8").splitlines()
        for section_class, start, end in self._sections(lines):
            for line_number in range(start, end):
                line = lines[line_number].strip()
                if not line or self._is_comment(line):
                    continue
                try:
                    record = self._parse_record(line, section_class)
                except (ValueError, TypeError) as error:
                    raise RawParseError(str(error), self.source, line_number + 1, line) from error
                model.add_to_graph(record)
        return model
```

Catch only the errors your parsing can raise, and re-raise with location. Don't wrap `read_all` in a blanket
`except Exception`.

## Parsing strategies

| Structure | Formats | Approach |
|---|---|---|
| line by line | MATPOWER rows, CSV | one record per non-comment line |
| sections | RAW, GLM | find section boundaries, then parse each line with that section's class |
| multi-file | DSS (`Redirect`, `Compile`), DistOPF CSV directory | follow includes relative to the including file; one class per file where the format does that |

## Tokenizing

```python
import csv, io, shlex

def split_commas(line: str) -> list[str]:          # respects quotes: "1, 'A,B'" -> ['1', "A,B"]
    return [token.strip() for token in next(csv.reader(io.StringIO(line), skipinitialspace=True, quotechar="'"))]

def split_whitespace(line: str) -> list[str]:      # respects quotes
    return shlex.split(line)

def split_fixed_width(line: str, widths: list[int]) -> list[str]:
    tokens, start = [], 0
    for width in widths:
        tokens.append(line[start:start + width].strip())
        start += width
    return tokens
```

## Building a record from tokens

```python
from cimhub_core.serialization import get_schema_annotations

def _parse_record(self, line: str, schema_class: type):
    annotations = get_schema_annotations(schema_class)
    ordered = sorted((spec["order"], name) for name, spec in annotations.items() if "order" in spec)
    tokens = split_commas(line)
    if len(tokens) > len(ordered):
        raise ValueError(f"{schema_class.__name__}: {len(tokens)} fields, schema has {len(ordered)}")
    values = {}
    for token, (_, name) in zip(tokens, ordered):
        if token != "":
            values[name] = token          # LinkML dataclasses coerce str -> declared range
    return schema_class(**values)         # missing fields keep their ifabsent defaults
```

If the format has its own spellings (booleans as `y`/`n`, `1.0` for an int), convert them in one small function
keyed off the slot's `range`, and raise on a value it doesn't recognise.

## Writer skeleton

```python
from pathlib import Path

from cimhub_core import FormatWriter, GraphModel
from cimhub_core.serialization import AnnotationSerializer

from cimhub_raw.schema import raw as schema


class RawWriter(FormatWriter):
    SECTION_ORDER = [schema.Bus, schema.Load, schema.Generator, schema.Branch]

    def __init__(self) -> None:
        self.serializer = AnnotationSerializer(separator=",", skip_none=False)

    def serialize(self, obj) -> str:
        return self.serializer.serialize(obj)          # multi-line records via line_number annotations

    def write(self, model: GraphModel, destination: str) -> None:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [self._case_header(model)]
        for section_class in self.SECTION_ORDER:
            lines += [self.serialize(obj) for obj in model.list_by_class(section_class)]
            lines.append(f"0 / END OF {section_class.__name__.upper()} DATA")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

Variants:

- **Single file, no sections:** `for obj in model.iter_all(): f.write(self.serialize(obj) + "\n")`.
- **One file per class (DistOPF CSV):** `destination` is a directory; for each class in the model, write a header
  row from the field order, then one serialized row per object.
- **Command order matters (DSS master):** a class-level order list, and the writer emits `Redirect` lines for the
  per-class files.

## Importer and exporter skeletons

```python
from cimgraph.models import BusBranchModel

from cimhub_core import CimtblImporter, FormatExporter, GraphModel


class RawImporter(CimtblImporter):
    model_cls = BusBranchModel

    def to_cimtbl(self, model: GraphModel):            # pure: documents only (cimtbl-import-contract)
        ...


def raw_to_cim(model: GraphModel, *, name: str, network=None):
    return RawImporter(name).to_cim(model, network=network)


class RawExporter(FormatExporter):
    def to_model(self, network, **opts) -> GraphModel:  # reads through cimhub_core getters
        native = GraphModel()
        ...
        return native


def cim_to_raw(network, destination, **opts) -> None:
    RawWriter().write(RawExporter().to_model(network, **opts), destination)
```

## Test templates

```python
def test_read_bus_record(tmp_path):
    path = tmp_path / "case.raw"
    path.write_text(SAMPLE_CASE, encoding="utf-8")
    buses = RawReader(path).read_all().list_by_class(schema.Bus)
    assert [bus.number for bus in buses] == [1, 2]
    assert buses[0].base_kv == pytest.approx(138.0)


def test_bad_line_reports_location(tmp_path):
    path = tmp_path / "bad.raw"
    path.write_text(CASE_WITH_BAD_BUS, encoding="utf-8")
    with pytest.raises(RawParseError, match=r"bad\.raw:3:"):
        RawReader(path).read_all()


def test_serialize_bus():
    bus = schema.Bus(number=1, name="BUS_001", base_kv=138.0)
    assert RawWriter().serialize(bus) == "1,'BUS_001     ',138.0000,1,1,1,1,1.00000,0.0000"


def test_round_trip(tmp_path):
    original = RawReader(FIXTURE).read_all()
    RawWriter().write(original, tmp_path / "out.raw")
    again = RawReader(tmp_path / "out.raw").read_all()
    for cls in original.graph:
        assert again.list_by_class(cls) == original.list_by_class(cls)


def test_contract():
    assert issubclass(RawReader, FormatReader) and issubclass(RawWriter, FormatWriter)
    assert issubclass(RawImporter, CimtblImporter) and issubclass(RawExporter, FormatExporter)
```

The expected strings above are illustrative; take real ones from your fixture. Add a byte-identical round-trip
test where the format's formatting is fully determined by the schema.

## Pitfalls

1. **Hand-coded format strings.** They drift from the schema. Fix the annotations instead.
2. **Defaults.** Leave missing optional fields unset so `ifabsent` applies; don't pass `None` explicitly unless the
   format really has an empty value.
3. **Unit conversion in the reader or writer.** Neither converts; values stay in the native unit.
4. **Hard-coded field order.** Read it from the `order` annotations.
5. **Vague errors.** Say what, where and why: ``f"{path}:{line_number}: bus {name}: base kV {token!r} is not a
   number"``.
6. **Iterating `model.graph[cls]`.** It yields identifier strings; use `iter_all()` / `list_by_class()`.

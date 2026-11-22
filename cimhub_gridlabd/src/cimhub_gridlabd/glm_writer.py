"""``GlmModel`` -> a GridLAB-D ``.glm`` deck that ``GlmReader`` and GridLAB-D both read
(``GLM_REWRITE_PLAN.md`` section 8.2, ``docs/EXPORT_MAPPING.md#x0-framework-writer-nodes-and-the-swing``).

The deck is the model's ``clock`` block, its ``#set`` globals, one ``module`` block per module, its ``class``
blocks (``class player { double value; }``), then one ``object <class> { ... }`` per record in ``WRITE_ORDER`` (each
class after the classes it names), the records of a class in name order. A property is the slot's GLM name and its
value; an unset slot is not written, unless the model holds an expression for it (``<player>.value*K``), written as
is. Each player's tape (``GlmModel.tapes``) is written to its ``file`` beside the deck, one ``time,value`` row per
line. Values:

- a number to ``FLOAT_DIGITS`` significant digits, in the slot's schema unit (GLM's fixed units; no unit text);
- a complex value rectangular, ``a+bj`` (skill ``conductor-geometry``: no leading ``+``, the imaginary sign always
  written);
- a boolean ``TRUE``/``FALSE``;
- any text (a name, a reference, a keyword) double-quoted, which GridLAB-D reads for keywords too.

A model holding a class not in ``WRITE_ORDER`` raises, so nothing is dropped.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from linkml_runtime.utils.enumerations import EnumDefinitionImpl

from cimhub_core.base import FormatWriter
from cimhub_gridlabd import glm_schema
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.schema import gridlabd as schema

#: enough for a value that went through a unit conversion (1e-16 relative noise is dropped)
FLOAT_DIGITS = 15

#: Classes in definition order: catalogs, configurations, nodes, links, then the devices parented to nodes.
WRITE_ORDER = (
    schema.Player,  # before the loads whose bases read it
    schema.OverheadLineConductor, schema.UndergroundLineConductor, schema.TriplexLineConductor,
    schema.LineSpacing, schema.LineConfiguration, schema.TriplexLineConfiguration,
    schema.TransformerConfiguration, schema.RegulatorConfiguration,
    schema.Substation, schema.Node, schema.Meter, schema.TriplexNode, schema.TriplexMeter,
    schema.OverheadLine, schema.UndergroundLine, schema.TriplexLine,
    schema.Switch, schema.Fuse, schema.Recloser, schema.Sectionalizer, schema.SeriesReactor,
    schema.Transformer, schema.Regulator,
    schema.Load, schema.TriplexLoad, schema.Capacitor,
    schema.Inverter, schema.Solar, schema.Battery,
)

#: GlmObject slots that are object bookkeeping, not properties (``name`` is written first, the others never set)
_FIRST = "name"


def format_float(value: float) -> str:
    """``value`` to ``FLOAT_DIGITS`` significant digits, the shortest form (``60``, ``0.0018``, ``1e-05``)."""
    return f"{value:.{FLOAT_DIGITS}g}"


def format_complex(value: schema.Complex) -> str:
    """``a+bj``: the real part unsigned when positive, the imaginary sign always written."""
    real, imag = float(value.real or 0.0), float(value.imag or 0.0)
    sign = "-" if imag < 0 else "+"
    return f"{format_float(real)}{sign}{format_float(abs(imag))}j"


def format_value(value) -> str:
    """One property value as GLM text (module docstring)."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, schema.Complex):
        return format_complex(value)
    if isinstance(value, (int, float)):
        return str(value) if isinstance(value, int) else format_float(value)
    if isinstance(value, EnumDefinitionImpl):
        value = value.code.text
    elif hasattr(value, "text"):  # a linkml PermissibleValue
        value = value.text
    text = str(value)
    if '"' in text:
        raise ValueError(f"GLM text {text!r} holds a double quote, which GLM cannot quote")
    return f'"{text}"'


class GlmWriter(FormatWriter):
    """Write a ``GlmModel`` as one ``.glm`` file (``destination``)."""

    def write(self, model: GlmModel, destination: str) -> None:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.deck(model), encoding="utf-8")
        for player in model.list_by_class(schema.Player):
            (path.parent / player.file).write_text(tape_text(model.tapes[str(player.name)]), encoding="utf-8")

    def deck(self, model: GlmModel) -> str:
        """The whole deck as text."""
        unknown = sorted(cls.__name__ for cls in model.graph if cls not in WRITE_ORDER and model.count(cls))
        if unknown:
            raise ValueError(f"GlmWriter: no write order for {unknown}")
        blocks = [_settings_block("clock", model.clock)] if model.clock else []
        blocks += [f"#set {name}={value}" for name, value in model.globals.items()]
        blocks += [f"#define {name}={value}" for name, value in model.defines.items()]
        blocks += [_settings_block(f"module {name}", settings) for name, settings in model.modules.items()]
        blocks += [_class_block(name, properties) for name, properties in model.classes.items()]
        players = {str(player.name) for player in model.list_by_class(schema.Player)}
        if players != set(model.tapes):
            raise ValueError(f"GlmWriter: players {sorted(players)} and tapes {sorted(model.tapes)} differ")
        for cls in WRITE_ORDER:
            records = sorted(model.list_by_class(cls), key=lambda record: str(record.name))
            blocks += [self.serialize(record, model.expressions) for record in records]
        return "\n".join(blocks) + "\n"

    def serialize(self, obj, expressions: dict | None = None) -> str:
        """One ``object <class> { ... }`` block: ``name`` first, then every set slot in schema order, an unset slot
        with an expression in ``expressions`` (``(name, slot) -> text``) as that text."""
        info = glm_schema.slots(type(obj))
        expressions = expressions or {}
        lines = [f"object {obj.class_name} {{", f"  name {format_value(obj.name)};"]
        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)
            if field.name == _FIRST:
                continue
            if value is None:
                text = expressions.get((str(obj.name), field.name))
                if text is not None:
                    lines.append(f"  {info[field.name].native_name} {text};")
                continue
            lines.append(f"  {info[field.name].native_name} {format_value(value)};")
        lines.append("}")
        return "\n".join(lines)


def tape_text(rows: list[tuple[str, str]]) -> str:
    """A player file: one ``time,value`` row per line."""
    return "".join(f"{time},{value}\n" for time, value in rows)


def _class_block(name: str, properties: dict[str, str]) -> str:
    """``class player { double value; }``: each property's type, then its name."""
    body = "".join(f"  {kind} {prop};\n" for prop, kind in properties.items())
    return f"class {name} {{\n{body}}}"


def _settings_block(header: str, settings: dict[str, str]) -> str:
    """``header { name value; ... }``; values are written as given (the exporter's settings are GLM text)."""
    if not settings:
        return f"{header};"
    body = "".join(f"  {name} {value};\n" for name, value in settings.items())
    return f"{header} {{\n{body}}}"

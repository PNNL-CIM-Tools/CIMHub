"""OpenDSS format serializer.

Converts LinkML-generated dataclass instances into OpenDSS command strings
that can be passed to ``opendssdirect.Text.Command()``.
"""
from __future__ import annotations

import math
import re
from dataclasses import fields, is_dataclass
from enum import IntEnum

from cimhub_core import GraphModel
from cimhub_core.base import FormatWriter
from cimhub_core.serialization import get_schema_annotations


# Regex to extract trailing integer from a meaning URI like
# "https://gridappsd.github.io/dss-graph/LoadModel.4"
_MEANING_INT_RE = re.compile(r'\.(\d+)$')

# Characters OpenDSS cannot carry inside an object name or a reference to one.
# A space ends the token, so "Cable_2P_1C_2GA_CU BSD" is parsed as a name plus a
# stray property and raises "Invalid inline math entry"; the bracket, quote, and
# brace characters are array/expression delimiters.  Utility source data really
# does contain these -- one Portland cable catalog entry is named
# "3P_1C_500KCM_CU-<NULL>" in the CYME file -- so sanitizing is not optional.
#
# Applied in the writer rather than in the ~20 converter modules because a name
# is written in three places (the "new Class.NAME" prefix, a nested-dataclass
# reference, and strings the converters build such as bus1= and
# SwitchedObj=f"Line.{name}").  One rule here keeps a definition and every
# reference to it spelled the same way; sanitizing per-converter would not.
_DSS_UNSAFE_RE = re.compile(r'[\s"\'<>\[\]{}(),=~|]+')


def dss_safe_name(name: str) -> str:
    """Return *name* with characters OpenDSS cannot parse replaced by "_".

    Idempotent, and collision-free for the names seen in practice because the
    replacement is one-for-one on each run of unsafe characters rather than a
    truncation.  Names differing only in an unsafe character would collide; that
    is a data defect worth surfacing loudly, not silently renaming around.
    """
    return _DSS_UNSAFE_RE.sub('_', name)


class DssWriter(FormatWriter):
    """Serialize LinkML-generated OpenDSS dataclasses to DSS command strings.

    Produces strings like::

        new Load.myload bus1=bus123.1.2.3 kV=12.47 kW=100.0

    Field ordering and DSS property names are driven entirely by the YAML
    schema annotations (``order`` and ``dss_name``).  No hardcoded name maps.
    """

    # ------------------------------------------------------------------
    # FormatWriter interface
    # ------------------------------------------------------------------

    def write(self, model: GraphModel, destination: str) -> None:
        """Write every object in *model* to *destination* as DSS commands.

        Args:
            model: GraphModel of OpenDSS schema dataclasses.
            destination: Path to the output .dss file.
        """
        with open(destination, 'w') as f:
            for obj in model.iter_all():
                f.write(self.serialize(obj) + '\n')

    def serialize(self, obj) -> str:
        """Serialize a single LinkML dataclass to a DSS ``new`` command."""
        class_name = obj.__class__.__name__
        name = getattr(obj, 'name', None)
        parts = [f'new {class_name}.{dss_safe_name(str(name))}']

        schema_annots = get_schema_annotations(type(obj))

        # Sort fields by annotated order; fields without order go last
        ordered = sorted(
            (f for f in fields(obj) if f.name != 'name'),
            key=lambda f: 0 if f.name == 'phases' else schema_annots.get(f.name, {}).get('order', 9999),
        )

        for f in ordered:
            value = getattr(obj, f.name)
            if value is None:
                continue

            field_annots = schema_annots.get(f.name, {})
            dss_name = field_annots.get('dss_name', f.name)
            formatted = self._format_value(value, field_annots)

            if formatted is not None:
                parts.append(f'{dss_name}={formatted}')

        return ' '.join(parts)

    # ------------------------------------------------------------------
    # DSS-specific value formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_value(value, field_annots: dict | None = None) -> str | None:
        """Format a Python value into DSS syntax.

        Returns None if the value should be skipped (empty list, etc.).
        """
        field_annots = field_annots or {}

        # Boolean: must come before int since bool subclasses int
        if isinstance(value, bool):
            return 'Yes' if value else 'No'

        # IntEnum (e.g. old-style LoadModel)
        if isinstance(value, IntEnum):
            return str(value.value)

        # LinkML EnumDefinitionImpl — has .code (PermissibleValue) and .meaning
        if hasattr(value, 'code') and hasattr(value, 'meaning'):
            pv = value.code
            meaning = getattr(pv, 'meaning', None)
            if meaning:
                m = _MEANING_INT_RE.search(str(meaning))
                if m:
                    return m.group(1)
            return str(pv.text)

        # LinkML PermissibleValue used directly
        if hasattr(value, 'text') and hasattr(value, 'meaning'):
            meaning = getattr(value, 'meaning', None)
            if meaning:
                m = _MEANING_INT_RE.search(str(meaning))
                if m:
                    return m.group(1)
            return str(value.text)

        # List / multivalued
        if isinstance(value, (list, tuple)):
            if not value:
                return None
            if field_annots.get('dss_format') == 'matrix':
                return DssWriter._format_matrix(list(value))
            # Members are often object names (wires=[...], conns=[...]), so
            # they need the same sanitizing a bare name reference gets.
            return '[' + ' '.join(
                dss_safe_name(v) if isinstance(v, str) else str(v) for v in value
            ) + ']'

        # Nested dataclass -> reference by name
        if is_dataclass(value) and not isinstance(value, type):
            return dss_safe_name(str(getattr(value, 'name', value)))

        # Strings reach here as bus references, wire/spacing names, and
        # "Line.<name>" control targets, so they need the same sanitizing the
        # definitions got -- otherwise a reference stops matching its object.
        #
        # Matrix fields are excluded by annotation, not by type: some converters
        # (per_length_impedance) hand back an already-formatted "[a |b c]" string
        # rather than a list, and sanitizing that ate the brackets and row
        # separators -- silently zeroing every line impedance in the model.
        if isinstance(value, str) and field_annots.get('dss_format') != 'matrix':
            return dss_safe_name(value)

        return str(value)

    @staticmethod
    def _format_matrix(values: list) -> str:
        """Format a lower-triangle list as DSS matrix syntax.

        Input: flat lower-triangle [l11, l21, l22, l31, l32, l33]
        Output: [l11 |l21 l22 |l31 l32 l33]
        """
        n = int((-1 + math.sqrt(1 + 8 * len(values))) / 2)
        parts = []
        idx = 0
        for row in range(1, n + 1):
            row_vals = [f'{values[idx + col]:.6g}' for col in range(row)]
            parts.append(' '.join(row_vals))
            idx += row
        return '[' + ' |'.join(parts) + ']'

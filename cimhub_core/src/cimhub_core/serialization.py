"""Annotation-aware serialization utilities for format-specific writers.

This module provides helpers for FormatWriter implementations to leverage
LinkML schema annotations for bulletproof round-trip serialization.

The key challenge: gen-python doesn't propagate LinkML annotations into
dataclass field metadata. Solution: load the original YAML schema at runtime
and cache the annotation metadata.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import fields, is_dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Type

import yaml

__all__ = [
    "AnnotationSerializer",
    "get_schema_annotations",
    "format_by_spec",
]


# ---------------------------------------------------------------------------
# Schema annotation cache
# ---------------------------------------------------------------------------

@lru_cache(maxsize=128)
def get_schema_annotations(schema_class: Type) -> dict[str, dict]:
    """Load LinkML annotations for a dataclass from its YAML schema.

    Args:
        schema_class: A LinkML-generated dataclass type.

    Returns:
        Dictionary mapping field names to their annotation dicts, e.g.::

            {
                'bus1': {'order': 1, 'format': {...}, 'dss_name': 'bus1', 'unit': 'kV'},
                'length': {'order': 4, 'format': {...}, 'serialize_if': {...}},
            }

        Also extracts top-level field properties like 'unit', 'range', 'required'.

    Note:
        This function caches results. The schema YAML path is discovered by
        introspecting the module's ``__file__`` attribute and looking for a
        sibling ``schema/`` directory.
    """
    # Try to find the schema YAML file
    module_name = schema_class.__module__
    try:
        module_obj = sys.modules[module_name]
        module_file = Path(module_obj.__file__)
    except (AttributeError, TypeError, KeyError):
        return {}

    # Look for schema directory (common patterns)
    schema_dir = None
    for candidate in [
        module_file.parent / 'schema',
        module_file.parent.parent / 'schema',
        module_file.parent / 'linkml',
        module_file.parent,  # Check module's own directory (for raw, OpenDSS, etc.)
    ]:
        if candidate.exists():
            schema_dir = candidate
            break

    if not schema_dir:
        return {}

    # Find the class definition in YAML files
    class_name = schema_class.__name__
    annotations = {}

    # Search for class definition (could be in main.yaml or classes/*.yaml)
    for yaml_file in schema_dir.rglob('*.yaml'):
        try:
            with open(yaml_file) as f:
                schema = yaml.safe_load(f)

            if not schema or 'classes' not in schema:
                continue

            if class_name in schema['classes']:
                class_def = schema['classes'][class_name]
                if 'attributes' in class_def:
                    for field_name, field_def in class_def['attributes'].items():
                        # Start with annotations if present
                        field_annotations = {}
                        if 'annotations' in field_def:
                            field_annotations = dict(field_def['annotations'])

                        # Also extract useful top-level properties
                        # that aren't part of annotations but are useful metadata
                        for prop in ['unit', 'range', 'required', 'ifabsent', 'identifier',
                                     'minimum_value', 'maximum_value', 'multivalued',
                                     'description']:
                            if prop in field_def:
                                field_annotations[prop] = field_def[prop]

                        if field_annotations:
                            annotations[field_name] = field_annotations
                break
        except Exception:
            continue

    return annotations


# ---------------------------------------------------------------------------
# Annotation-driven serialization
# ---------------------------------------------------------------------------

class AnnotationSerializer:
    """Serialize LinkML dataclasses using schema annotations.

    This class implements format-agnostic serialization driven by annotations
    in the LinkML schema. It's designed to be used by FormatWriter subclasses.

    Example::

        class RawWriter(FormatWriter):
            def serialize(self, obj) -> str:
                serializer = AnnotationSerializer(separator=',')
                return serializer.serialize(obj)
    """

    def __init__(
        self,
        separator: str = ',',
        skip_none: bool = True,
        skip_defaults: bool = False,
    ):
        """Initialize serializer with format-specific settings.

        Args:
            separator: Default separator between fields (if not in annotations).
            skip_none: Skip fields with None values.
            skip_defaults: Skip fields at their default values (from ifabsent).
        """
        self.separator = separator
        self.skip_none = skip_none
        self.skip_defaults = skip_defaults

    def serialize(self, obj: Any) -> str:
        """Serialize a LinkML dataclass instance using its schema annotations.

        Supports:
        - Single-line records (default)
        - Multi-line records (using line_number annotation)
        - Conditional fields (using serialize_if annotation)

        Args:
            obj: A LinkML-generated dataclass instance.

        Returns:
            Formatted string representation (may contain newlines for multi-line records).
        """
        if not is_dataclass(obj):
            raise TypeError(f"Expected dataclass, got {type(obj)}")

        # Get annotations from schema
        annotations = get_schema_annotations(type(obj))

        # Check if this is a multi-line record
        has_line_numbers = any('line_number' in annot for annot in annotations.values())

        if has_line_numbers:
            return self._serialize_multiline(obj, annotations)
        else:
            return self._serialize_single_line(obj, annotations)

    def _serialize_single_line(self, obj: Any, annotations: dict) -> str:
        """Serialize a single-line record."""
        # Collect (order, field_name, field_obj, annotations)
        ordered_fields = []
        for field in fields(obj):
            field_annot = annotations.get(field.name, {})
            order = field_annot.get('order', 9999)  # unordered fields go last
            ordered_fields.append((order, field.name, field, field_annot))

        # Sort by order
        ordered_fields.sort(key=lambda x: x[0])

        # Build output
        parts = []
        for order, field_name, field_obj, field_annot in ordered_fields:
            value = getattr(obj, field_name)

            # Check if we should serialize this field
            if not self._should_serialize(obj, value, field_obj, field_annot):
                continue

            # Format the value
            formatted = self._format_value(value, field_annot)

            # Get separator (check both nested 'format' dict and direct annotation)
            sep = field_annot.get('separator')
            if sep is None:
                sep = field_annot.get('format', {}).get('separator', self.separator)

            parts.append(formatted + sep)

        # Remove trailing separator from last field
        if parts:
            result = ''.join(parts)
            # Strip last separator if present
            if parts[-1]:
                last_sep_len = len(parts[-1]) - len(parts[-1].rstrip(self.separator + ' \t'))
                if last_sep_len > 0:
                    # Find what separator was used
                    last_added = parts[-1]
                    for potential_sep in [self.separator, ',', ' ', '']:
                        if last_added.endswith(potential_sep):
                            result = result[:-len(potential_sep)] if potential_sep else result
                            break
            return result

        return ''

    def _serialize_multiline(self, obj: Any, annotations: dict) -> str:
        """Serialize a multi-line record using line_number annotations."""
        # Group fields by line number
        lines_dict = defaultdict(list)

        for field in fields(obj):
            field_annot = annotations.get(field.name, {})
            line_num = field_annot.get('line_number', 1)  # default to line 1
            order = field_annot.get('order', 9999)
            lines_dict[line_num].append((order, field.name, field, field_annot))

        # Serialize each line
        output_lines = []
        for line_num in sorted(lines_dict.keys()):
            # Sort fields by order within the line
            line_fields = sorted(lines_dict[line_num], key=lambda x: x[0])

            # Build the line
            parts = []
            for order, field_name, field_obj, field_annot in line_fields:
                value = getattr(obj, field_name)

                # Check if we should serialize this field
                if not self._should_serialize(obj, value, field_obj, field_annot):
                    continue

                # Format the value
                formatted = self._format_value(value, field_annot)

                # Get separator
                sep = field_annot.get('separator')
                if sep is None:
                    sep = field_annot.get('format', {}).get('separator', self.separator)

                parts.append(formatted + sep)

            # Remove trailing separator from last field in line
            if parts:
                line_result = ''.join(parts)
                # Strip last separator
                if parts[-1]:
                    last_added = parts[-1]
                    for potential_sep in [self.separator, ',', ' ', '']:
                        if last_added.endswith(potential_sep):
                            line_result = line_result[:-len(potential_sep)] if potential_sep else line_result
                            break
                output_lines.append(line_result)

        return '\n'.join(output_lines)

    def _should_serialize(
        self,
        obj: Any,
        value: Any,
        field_obj,
        annotations: dict,
    ) -> bool:
        """Determine if a field should be serialized based on rules.

        Args:
            obj: The parent dataclass instance (for custom expression evaluation)
            value: The field value
            field_obj: The dataclass field object
            annotations: The field annotations dict

        Returns:
            True if field should be serialized, False otherwise
        """
        # Check None
        if value is None and self.skip_none:
            return False

        # Check serialize_if annotation
        if 'serialize_if' in annotations:
            serialize_if = annotations['serialize_if']

            # Handle both string and dict formats
            if isinstance(serialize_if, str):
                condition = serialize_if
            else:
                condition = serialize_if.get('condition', 'always')

            if condition == 'always':
                return True
            elif condition == 'not_null':
                return value is not None
            elif condition == 'not_default':
                # Compare to default value
                default_expr = field_obj.metadata.get('ifabsent')
                if default_expr:
                    # Parse ifabsent expressions like "float(1.0)" or "int(3)"
                    default = self._parse_ifabsent(default_expr)
                    return value != default
                return True
            elif isinstance(condition, str) and condition.startswith('custom:'):
                # Extract expression after "custom:" prefix and evaluate
                expression = condition[7:]  # Remove "custom:" prefix
                return self._eval_condition(obj, expression)
            elif condition == 'custom':
                # Dict format with 'custom' type - get expression
                expression = serialize_if.get('expression', 'True') if isinstance(serialize_if, dict) else 'True'
                return self._eval_condition(obj, expression)

        return True

    def _eval_condition(self, obj: Any, expression: str) -> bool:
        """Evaluate a custom conditional expression.

        Args:
            obj: The dataclass instance providing field values
            expression: Python expression to evaluate (e.g., "n1 != 0", "k != 0")

        Returns:
            Boolean result of expression evaluation

        Note:
            This uses eval() with a restricted namespace containing only the
            object's field values. Be cautious with user-provided expressions.
        """
        try:
            # Build namespace from object fields
            namespace = {}
            for field in fields(obj):
                namespace[field.name] = getattr(obj, field.name, None)

            # Evaluate expression
            result = eval(expression, {"__builtins__": {}}, namespace)
            return bool(result)
        except Exception:
            # If evaluation fails, default to True (serialize the field)
            return True

    @staticmethod
    def _parse_ifabsent(expr: str) -> Any:
        """Parse LinkML ifabsent expression like 'float(1.0)' or 'int(3)'."""
        if not isinstance(expr, str):
            return expr

        # Match patterns like "float(1.0)", "int(3)", "true", "false", etc.
        if expr == 'true':
            return True
        elif expr == 'false':
            return False
        elif expr.startswith('float(') and expr.endswith(')'):
            return float(expr[6:-1])
        elif expr.startswith('int(') and expr.endswith(')'):
            return int(expr[4:-1])
        elif expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]

        return None

    def _format_value(self, value: Any, annotations: dict) -> str:
        """Format a value according to its format specification."""
        # Handle both nested 'format' dict and flattened annotations
        if 'format' in annotations:
            return format_by_spec(value, annotations['format'])
        else:
            # Flattened format - pass annotations directly
            return format_by_spec(value, annotations)

        # Fallback to simple string conversion
        return str(value) if value is not None else ''


# ---------------------------------------------------------------------------
# Value formatting
# ---------------------------------------------------------------------------

def format_by_spec(value: Any, format_spec: dict) -> str:
    """Format a value according to a format specification dict.

    Args:
        value: The value to format.
        format_spec: Dict with keys like 'value_type', 'precision', 'width', 'quote', etc.

    Returns:
        Formatted string.

    Example::

        format_by_spec(
            3.14159,
            {'value_type': 'float', 'precision': 2, 'width': 8, 'align': 'right'}
        )
        # Returns: '    3.14'
    """
    # Check if this is a multivalued field (list)
    is_multivalued = format_spec.get('multivalued', False)
    if is_multivalued and isinstance(value, list):
        # Format each item in the list and join with separator
        separator = format_spec.get('separator', ',')
        # Create a single-value format spec by removing multivalued flag
        single_spec = {k: v for k, v in format_spec.items() if k != 'multivalued'}
        formatted_items = [format_by_spec(item, single_spec) for item in value]
        return separator.join(formatted_items)

    # Handle both 'value_type' and 'type' keys for compatibility
    ftype = format_spec.get('value_type') or format_spec.get('type', 'string')
    precision = format_spec.get('precision')
    width = format_spec.get('width')
    align = format_spec.get('align', 'left')
    quote = format_spec.get('quote', False)
    quote_char = format_spec.get('quote_char', "'")

    # Format based on type
    if value is None:
        formatted = ''
    elif ftype == 'float':
        if precision is not None:
            formatted = f"{float(value):.{precision}f}"
        else:
            formatted = str(float(value))
    elif ftype == 'int':
        formatted = f"{int(value):d}"
    elif ftype == 'bool':
        as_int = format_spec.get('bool_as_int', True)
        if as_int:
            formatted = str(int(value))
        else:
            formatted = str(value)
    elif ftype == 'string':
        formatted = str(value)
    else:
        formatted = str(value)

    # Apply width and alignment
    if width:
        if align == 'right':
            formatted = formatted.rjust(width)
        elif align == 'center':
            formatted = formatted.center(width)
        else:  # left
            formatted = formatted.ljust(width)

    # Apply quoting
    if quote:
        formatted = f"{quote_char}{formatted}{quote_char}"

    return formatted


# ---------------------------------------------------------------------------
# Utilities for manual serialization
# ---------------------------------------------------------------------------

def get_field_order(obj: Any) -> list[str]:
    """Get field names in their annotated order.

    Args:
        obj: A LinkML dataclass instance.

    Returns:
        List of field names sorted by 'order' annotation, with unordered
        fields at the end in definition order.
    """
    annotations = get_schema_annotations(type(obj))

    ordered = []
    for field in fields(obj):
        order = annotations.get(field.name, {}).get('order', 9999)
        ordered.append((order, field.name))

    ordered.sort(key=lambda x: x[0])
    return [name for _, name in ordered]


def get_native_name(obj: Any, field_name: str) -> str:
    """Get the native format name for a field (from dss_name annotation, etc.).

    Args:
        obj: A LinkML dataclass instance.
        field_name: Python field name.

    Returns:
        Native format name (e.g., "%R" for pct_R in raw).
    """
    annotations = get_schema_annotations(type(obj))
    field_annot = annotations.get(field_name, {})

    # Check for various annotation keys
    for key in ['native_name', 'dss_name', 'raw_name']:
        if key in field_annot:
            return field_annot[key]

    return field_name

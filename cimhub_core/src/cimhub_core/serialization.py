"""A native class's LinkML slot annotations, read from its schema YAML.

gen-python does not carry LinkML annotations into the dataclass fields, so readers, writers and mappers that need
them (``order``, a native name, a ``<fmt>_default``) load the YAML at run time. Each spoke formats its own records
from these annotations: DSS ``key=value`` (``dss_writer``), RAW positional lines (``record_layout``), GLM objects
(``glm_schema``, which indexes by GLM type name).
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Type

import yaml

__all__ = ["get_schema_annotations"]


# ---------------------------------------------------------------------------
# Schema annotation cache
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _load_yaml(path: Path):
    """One schema YAML file, parsed once per process: ``get_schema_annotations`` searches every file of a schema
    for each class it is asked about, and a large schema (GLM: 79 files) took seconds per class to re-parse."""
    with open(path) as f:
        return yaml.safe_load(f)


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
        schema = _load_yaml(yaml_file)

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

    return annotations

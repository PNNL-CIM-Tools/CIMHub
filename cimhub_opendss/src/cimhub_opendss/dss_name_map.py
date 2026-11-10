"""YAML-driven DSS-name-to-Python-field mapping and enum resolution.

gen-python does NOT propagate LinkML annotations (like ``dss_name``) into the
generated dataclass code.  This module loads the original YAML schemas at
runtime to build case-insensitive lookup tables that map DSS native property
names (``%R``, ``class``, ``%mean``) to Python field names (``pct_R``,
``load_class``, ``pct_mean``), plus enum member resolution.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, fields as dc_fields, is_dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, get_args, get_origin

import yaml

_log = logging.getLogger(__name__)

__all__ = [
    "DssClassMap",
    "get_class_map",
    "build_type_registry",
]

# ---------------------------------------------------------------------------
# Schema directory discovery
# ---------------------------------------------------------------------------

_SCHEMA_DIR: Optional[Path] = None


def _get_schema_dir() -> Path:
    """Locate the ``schema/linkml`` directory relative to opendss_schema.py."""
    global _SCHEMA_DIR
    if _SCHEMA_DIR is not None:
        return _SCHEMA_DIR

    import cimhub_opendss.schema.opendss_schema as mod

    schema_py = Path(mod.__file__)
    candidate = schema_py.parent / "linkml"
    if candidate.is_dir():
        _SCHEMA_DIR = candidate
        return _SCHEMA_DIR

    raise FileNotFoundError(
        f"Cannot find schema/linkml directory relative to {schema_py}"
    )


# ---------------------------------------------------------------------------
# YAML loading (cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=64)
def _load_yaml(yaml_path: Path) -> dict:
    try:
        with open(yaml_path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError:
        _log.debug("Skipping malformed YAML: %s", yaml_path)
        return {}


def _find_class_yaml(class_name: str) -> Optional[dict]:
    """Search YAML files for the definition of *class_name*."""
    schema_dir = _get_schema_dir()
    for yaml_file in schema_dir.rglob("*.yaml"):
        data = _load_yaml(yaml_file)
        if "classes" in data and class_name in data["classes"]:
            return data["classes"][class_name]
    return None


@lru_cache(maxsize=1)
def _load_common_enums() -> dict:
    """Load the common_enums.yaml and return the ``enums`` dict."""
    schema_dir = _get_schema_dir()
    enum_path = schema_dir / "common_enums.yaml"
    if enum_path.exists():
        data = _load_yaml(enum_path)
        return data.get("enums", {})
    return {}


# ---------------------------------------------------------------------------
# DssClassMap
# ---------------------------------------------------------------------------

@dataclass
class DssClassMap:
    """Lookup tables for one schema class."""

    schema_class: type
    dss_type_name: str  # lowered class_name, e.g. "load"

    # lowered DSS property name -> Python field name
    param_to_field: dict[str, str]

    # field_name -> set of names that are list-valued
    multivalued: set[str]

    # field_name -> {lowered-dss-value -> enum member}
    enum_value_maps: dict[str, dict[str, Any]]

    def field_for(self, param: str) -> str:
        """The field a DSS property names: an exact (case-insensitive) match, else the first property, in
        DSS order, that starts with ``param``. DSS accepts abbreviations that way (``ppm`` is
        ``ppm_antifloat``, ``Vmin`` is ``Vminpu``); the schema's field order is the DSS property order."""
        key = param.lower()
        if key in self.param_to_field:
            return self.param_to_field[key]
        for name, field_name in self.param_to_field.items():
            if name.startswith(key):
                return field_name
        raise ValueError(f"unknown property {param!r} on {self.schema_class.__name__}")


def _resolve_enum_class(range_name: str) -> Optional[type]:
    """Given a LinkML range like 'ConnectionType', return the Python enum."""
    import cimhub_opendss.schema.opendss_schema as mod

    cls = getattr(mod, range_name, None)
    if cls is not None and hasattr(cls, "_defn"):
        # It's an EnumDefinitionImpl subclass
        return cls
    return None


def _build_enum_value_map(enum_class: type, enum_yaml_name: str) -> dict[str, Any]:
    """Build {lowered_value -> enum_member} for an enum.

    Sources of mapping keys:
    1. Member name lowered  (e.g. ``"wye"``)
    2. Aliases lowered      (e.g. ``"y"``, ``"ln"``)
    3. ``dss_value`` annotation lowered (e.g. ``"1"`` for LoadModel)
    4. Numeric suffix from ``meaning`` (e.g. ``dss:LoadModel.1`` -> ``"1"``)
    """
    value_map: dict[str, Any] = {}

    # Get permissible values from YAML for aliases / dss_value
    yaml_enums = _load_common_enums()
    yaml_def = yaml_enums.get(enum_yaml_name, {})
    yaml_values = yaml_def.get("permissible_values", {})

    # Iterate over the Python enum members
    for member_name in dir(enum_class):
        member = getattr(enum_class, member_name)
        # Skip non-member attributes
        if not hasattr(member, "text"):
            continue
        text = member.text
        if text is None:
            continue

        # 1. Member name lowered
        value_map[text.lower()] = member

        # 2-4. From YAML definition
        yaml_val = yaml_values.get(text, {})
        if isinstance(yaml_val, dict):
            # Aliases
            for alias in yaml_val.get("aliases", []):
                value_map[str(alias).lower()] = member

            # dss_value annotation
            annotations = yaml_val.get("annotations", {})
            if "dss_value" in annotations:
                value_map[str(annotations["dss_value"]).lower()] = member

            # Meaning suffix  (e.g. "dss:LoadModel.1" -> "1")
            meaning = yaml_val.get("meaning", "")
            if meaning and "." in meaning:
                suffix = meaning.rsplit(".", 1)[1]
                value_map[suffix.lower()] = member

    return value_map


def _is_multivalued_type(field_type) -> bool:
    """Return True if the type annotation indicates a list/multivalued field."""
    origin = get_origin(field_type)
    if origin is list:
        return True
    # Handle Optional[Union[float, list[float]]]  and  Optional[list[float]]
    if origin is type(None):
        return False
    args = get_args(field_type)
    for arg in args:
        if get_origin(arg) is list:
            return True
        if arg is list:
            return True
        # Recurse one level for Union
        inner_args = get_args(arg)
        for ia in inner_args:
            if get_origin(ia) is list or ia is list:
                return True
    return False


def build_class_map(schema_class: type) -> DssClassMap:
    """Build lookup tables for a single schema class."""
    class_name = getattr(schema_class, "class_name", schema_class.__name__)
    dss_type_name = class_name.lower()

    param_to_field: dict[str, str] = {}
    multivalued: set[str] = set()
    enum_value_maps: dict[str, dict[str, Any]] = {}

    # ---- 1. Load YAML annotations for dss_name overrides ----
    yaml_class_def = _find_class_yaml(class_name)
    yaml_attrs: dict[str, dict] = {}
    if yaml_class_def:
        yaml_attrs = yaml_class_def.get("attributes", {})

    # ---- 2. Walk dataclass fields ----
    if not is_dataclass(schema_class):
        return DssClassMap(schema_class, dss_type_name, param_to_field,
                           multivalued, enum_value_maps)

    for fld in dc_fields(schema_class):
        fname = fld.name

        # Always register the python field name (lowered) as a key
        param_to_field[fname.lower()] = fname
        if fname == "bus1":
            param_to_field["bus"] = "bus1"

        # Check YAML for annotations
        yaml_attr = yaml_attrs.get(fname, {})
        yaml_annotations = yaml_attr.get("annotations", {})

        # dss_name override
        dss_name = yaml_annotations.get("dss_name")
        if dss_name:
            param_to_field[str(dss_name).lower()] = fname

        # For pct_ fields, also add the %-prefixed form
        if fname.startswith("pct_"):
            pct_form = "%" + fname[4:]
            param_to_field[pct_form.lower()] = fname

        # Detect multivalued
        yaml_multivalued = yaml_attr.get("multivalued", False)
        if yaml_multivalued or _is_multivalued_type(fld.type):
            multivalued.add(fname)

        # Detect enum fields and build value maps
        yaml_range = yaml_attr.get("range", "")
        enum_cls = _resolve_enum_class(yaml_range) if yaml_range else None
        if enum_cls is not None:
            enum_value_maps[fname] = _build_enum_value_map(enum_cls, yaml_range)

    return DssClassMap(schema_class, dss_type_name, param_to_field,
                       multivalued, enum_value_maps)


@lru_cache(maxsize=128)
def get_class_map(schema_class: type) -> DssClassMap:
    """Cached wrapper around :func:`build_class_map`."""
    return build_class_map(schema_class)


# ---------------------------------------------------------------------------
# Type registry — maps lowered DSS type names to schema classes
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def build_type_registry() -> dict[str, type]:
    """Return ``{lowered_dss_type: schema_class}`` for all classes in the schema.

    Introspects ``opendss_schema`` to find all ``YAMLRoot`` subclasses.
    Adds known aliases like ``"circuit" -> Vsource``.
    """
    import cimhub_opendss.schema.opendss_schema as mod
    from linkml_runtime.utils.yamlutils import YAMLRoot

    registry: dict[str, type] = {}
    for attr_name in dir(mod):
        obj = getattr(mod, attr_name)
        if (
            isinstance(obj, type)
            and issubclass(obj, YAMLRoot)
            and obj is not YAMLRoot
            and hasattr(obj, "class_name")
        ):
            class_name = getattr(obj, "class_name", attr_name)
            registry[class_name.lower()] = obj

    # Known aliases
    vsource = registry.get("vsource")
    if vsource:
        registry["circuit"] = vsource

    # Handle underscore variants (e.g., "tcc_curve")
    tcc = registry.get("tcc_curve")
    if tcc:
        registry["tcccurve"] = tcc
        registry["tcc curve"] = tcc

    return registry

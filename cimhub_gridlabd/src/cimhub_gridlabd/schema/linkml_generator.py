"""
LinkML Schema Generator for GridLAB-D

Generates modular LinkML YAML schemas from parsed C++ class definitions.
Every object class without a parent inherits ``glm_object`` (types/common.yaml): the header properties
GridLAB-D gives every object (name, parent, groupid, ...), which no class publishes.
"""

from __future__ import annotations

import json
import re
import yaml
import keyword
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

_DOXYGEN_COMMAND = re.compile(r"\\([A-Za-z]+)")
_ESCAPED_CHARACTER = re.compile(r"\\(\S)")

#: The header properties of every GridLAB-D object (core/object.c); ``name`` is the model-wide identifier.
_HEADER_SLOTS = {
    "name": "The object's name; unique across the model.",
    "parent": "The parent object's name. A child node is solved as its parent's bus; a nested object block sets it "
              "to the enclosing object.",
    "groupid": "Free-text group label.",
    "latitude": "Latitude, as written (decimal degrees or GridLAB-D's 37N26:12 form).",
    "longitude": "Longitude, as written.",
    "in_svc": "Timestamp the object enters service.",
    "out_svc": "Timestamp the object leaves service.",
    "rank": "Solver rank.",
    "flags": "Core object flags.",
}


def _header_slot(name: str, description: str) -> dict:
    slot = {"range": "string"}
    if name == "name":
        slot.update(identifier=True, required=True)
    slot["description"] = description
    slot["annotations"] = {"order": 0, "value_type": "string", "native_name": name}
    return slot


GLM_OBJECT_CLASS = {
    "abstract": True,
    "description": "The header properties GridLAB-D gives every object (core/object.c), whatever its class. They are "
                   "not published by the class, so the C++ scrape does not see them. name is the identifier: "
                   "GridLAB-D names are unique across the whole model; an unnamed object is called <class>:<id>.",
    "attributes": {name: _header_slot(name, description) for name, description in _HEADER_SLOTS.items()},
}


def _doxygen_at(text: str) -> str:
    """Doxygen commands in their ``@cmd`` form (``\\p phases`` -> ``@p phases``): the same markup, but no
    backslash, which gen-python would copy into a docstring as an escape sequence. LaTeX commands inside
    ``@f$`` formulas (``\\frac``) take the ``@`` form too, and an escaped character (``\\_``) is kept as itself;
    descriptions are documentation only."""
    return _ESCAPED_CHARACTER.sub(r"\1", _DOXYGEN_COMMAND.sub(r"@\1", text))


class LinkMLGenerator:
    """Generate LinkML schemas from parsed GridLAB-D classes"""

    # Python keywords that need to be renamed
    PYTHON_KEYWORDS = set(keyword.kwlist)

    def __init__(self, output_dir: Path, module_name: str = "powerflow"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.module_name = module_name

        # Track enums to generate in types/common.yaml
        self.enums = {}

        # Track which classes are configurations vs instances
        self.configurations = set()
        self.instances = set()

    @staticmethod
    def sanitize_property_name(name: str) -> str:
        """
        Sanitize property name to be Python-safe.
        - Replaces dots with underscores (rating.summer.continuous → rating_summer_continuous)
        - Removes/replaces invalid characters (parentheses, commas, etc.)
        - Renames Python keywords by appending '_node' for from/to, or '_prop' for others.
        """
        import re

        # First, replace dots with underscores
        safe_name = name.replace('.', '_')

        # Remove or replace invalid characters (keep only alphanumeric and underscores)
        # Replace runs of invalid characters with single underscore
        safe_name = re.sub(r'[^a-zA-Z0-9_]+', '_', safe_name)

        # Remove leading/trailing underscores
        safe_name = safe_name.strip('_')

        # Ensure it doesn't start with a digit
        if safe_name and safe_name[0].isdigit():
            safe_name = f'prop_{safe_name}'

        # Then check if it's a Python keyword
        if safe_name in LinkMLGenerator.PYTHON_KEYWORDS:
            # Special handling for common cases
            if safe_name == 'from':
                return 'from_node'
            elif safe_name == 'to':
                return 'to_node'
            elif safe_name == 'class':
                return 'class_name'
            elif safe_name == 'type':
                return 'type_name'
            else:
                return f'{safe_name}_prop'

        return safe_name

    def generate_schemas(self, parsed_json_path: Path):
        """Generate complete LinkML schema structure"""
        _log.info(f"Loading parsed classes from: {parsed_json_path}")

        with open(parsed_json_path) as f:
            parsed_classes = json.load(f)

        _log.info(f"Generating schemas for {len(parsed_classes)} classes")

        # Store available class names for validation
        self.available_classes = set(parsed_classes.keys())

        # Categorize classes
        self._categorize_classes(parsed_classes)

        # Create module directory
        module_dir = self.output_dir / self.module_name
        module_dir.mkdir(exist_ok=True)

        # Create types directory
        types_dir = self.output_dir / "types"
        types_dir.mkdir(exist_ok=True)

        # Generate individual class files
        for class_name, class_data in parsed_classes.items():
            self._generate_class_file(class_name, class_data, module_dir)

        # Generate types/common.yaml
        self._generate_common_types(types_dir)

        # Generate main.yaml
        self._generate_main_schema(parsed_classes)

        _log.info(f"\n{'='*60}")
        _log.info(f"Schema generation complete!")
        _log.info(f"{'='*60}")
        _log.info(f"Output directory: {self.output_dir}")
        _log.info(f"  - main.yaml")
        _log.info(f"  - {self.module_name}/*.yaml ({len(parsed_classes)} files)")
        _log.info(f"  - types/common.yaml")

    def _categorize_classes(self, parsed_classes: Dict):
        """Categorize classes as configurations or instances"""
        for class_name, class_data in parsed_classes.items():
            name_lower = class_name.lower()

            # Configuration patterns
            if any(pattern in name_lower for pattern in [
                'configuration', 'conductor', 'spacing', 'library'
            ]):
                self.configurations.add(class_name)
            # Utility/dump classes
            elif any(pattern in name_lower for pattern in [
                'dump', 'check', 'tracker', 'metrics', 'emissions', 'restoration'
            ]):
                pass  # Neither config nor instance
            # Everything else is likely an instance
            else:
                self.instances.add(class_name)

    def _generate_class_file(self, class_name: str, class_data: dict, module_dir: Path):
        """Generate LinkML YAML file for a single class"""

        schema = {
            'id': f"https://gridlabd.org/schema/glm/{self.module_name}/{class_name}",
            'name': class_name.lower(),
            'description': f"GridLAB-D {class_name} class",
            'imports': ['linkml:types'],
            'prefixes': {
                'linkml': 'https://w3id.org/linkml/',
                'glm': 'https://gridlabd.org/schema/glm/',
            },
            'default_prefix': 'glm',
            'default_range': 'string',
            'classes': {}
        }

        # Every class needs the common types: glm_object (directly or through its parent), enums, Complex
        schema['imports'].append('../types/common')

        # Generate class definition
        class_def = self._generate_class_definition(class_name, class_data)
        schema['classes'][class_name] = class_def

        # Write to file
        output_file = module_dir / f"{class_name}.yaml"
        with open(output_file, 'w') as f:
            yaml.dump(schema, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        _log.info(f"  ✓ Generated: {output_file.name}")

    def _generate_class_definition(self, class_name: str, class_data: dict) -> dict:
        """Generate LinkML class definition with attributes"""

        class_def = {}

        # Add description
        description = self._format_description(class_name, class_data)
        if description:
            class_def['description'] = description

        # Add inheritance (only if parent exists in this module); a root class inherits the object header
        class_def['is_a'] = 'glm_object'
        if class_data.get('parent_class'):
            parent_class = class_data['parent_class']
            if parent_class in self.available_classes:
                class_def['is_a'] = parent_class
            else:
                # Parent class not in this module - add as comment in description
                description = class_def.get('description', '')
                description += f"\n\nNote: Inherits from {parent_class} (not in {self.module_name} module)"
                class_def['description'] = description

        # Add attributes
        if class_data.get('properties'):
            class_def['attributes'] = {}

            for i, prop in enumerate(class_data['properties'], start=1):
                # Sanitize property name for Python safety
                original_name = prop['name']
                safe_name = self.sanitize_property_name(original_name)

                attr_def = self._generate_attribute(prop, order=i, safe_name=safe_name)
                class_def['attributes'][safe_name] = attr_def

                # Collect enum for later generation (skip invalid names)
                if prop.get('enum_values'):
                    enum_name = prop['linkml_range']
                    # Skip enums with names that conflict with basic types or classes
                    invalid_names = {'float', 'string', 'integer', 'boolean', 'Complex', 'double', 'int'}
                    if enum_name not in invalid_names:
                        self.enums[enum_name] = prop['enum_values']

        return class_def

    def _format_description(self, class_name: str, class_data: dict) -> str:
        """Format class description with metadata"""
        lines = []

        # Add doc comment if available
        if class_data.get('doc_comment'):
            # Take first paragraph only
            doc = class_data['doc_comment'].split('\n\n')[0]
            lines.append(_doxygen_at(doc.strip()))
        else:
            lines.append(f"GridLAB-D {class_name} class")

        # Add inheritance info
        if class_data.get('parent_class'):
            lines.append(f"\nInherits from: {class_data['parent_class']}")

        # Add categorization
        if class_name in self.configurations:
            lines.append("\nType: Configuration (physical asset template)")
        elif class_name in self.instances:
            lines.append("\nType: Instance (network topology element)")

        return '\n'.join(lines)

    def _generate_attribute(self, prop: dict, order: int, safe_name: str) -> dict:
        """Generate LinkML attribute definition with annotations"""

        # Get range - if it's an enum type that wasn't collected, fall back to string
        linkml_range = prop['linkml_range']
        if linkml_range and linkml_range[0].isupper() and linkml_range not in ['Complex']:
            # It's likely an enum - check if we have it
            if linkml_range not in self.enums:
                # Enum wasn't collected - fall back to string
                linkml_range = 'string'

        attr = {
            'range': linkml_range,
            'required': prop.get('required', False)
        }

        # Add description if available
        if prop.get('description'):
            attr['description'] = _doxygen_at(prop['description'])

        # Add unit if available (must be structured with ucum_code)
        if prop.get('unit'):
            attr['unit'] = {
                'ucum_code': prop['unit']
            }

        # Add default value for optional properties
        if not prop.get('required'):
            # Don't add ifabsent for now - can be added later
            pass

        # Add serialization annotations
        annotations = {
            'order': order,
            'value_type': self._get_serialization_type(prop['cpp_type']),
        }

        # Add precision for floats
        if prop['cpp_type'] == 'PT_double':
            annotations['precision'] = 6

        # Add native name (original C++ name with unit for roundtrip serialization)
        # This is CRITICAL for handling Python keywords like 'from'/'to'
        original_name = prop['name']
        if prop.get('unit'):
            native_name = f"{original_name}[{prop['unit']}]"
        else:
            native_name = original_name

        annotations['native_name'] = native_name

        # If we renamed the property (Python keyword), note it
        if safe_name != original_name:
            _log.debug(f"  Renamed '{original_name}' → '{safe_name}' (Python keyword)")

        attr['annotations'] = annotations

        return attr

    def _get_serialization_type(self, cpp_type: str) -> str:
        """Map C++ type to serialization value_type"""
        type_map = {
            'PT_double': 'float',
            'PT_int32': 'int',
            'PT_int64': 'int',
            'PT_char1024': 'string',
            'PT_char256': 'string',
            'PT_char32': 'string',
            'PT_object': 'string',
            'PT_complex': 'complex',
            'PT_bool': 'bool',
            'PT_enumeration': 'string',
            'PT_set': 'string',
            'PT_timestamp': 'string',
        }
        return type_map.get(cpp_type, 'string')

    def _generate_common_types(self, types_dir: Path):
        """Generate or update types/common.yaml with shared types and enums.

        If the file already exists, merges new enums into the existing file
        without removing previously defined enums.
        """
        output_file = types_dir / "common.yaml"

        if output_file.exists():
            with open(output_file) as f:
                schema = yaml.safe_load(f)
            if 'enums' not in schema:
                schema['enums'] = {}
        else:
            schema = {
                'id': 'https://gridlabd.org/schema/glm/types/common',
                'name': 'common_types',
                'description': 'Common types and enumerations for GridLAB-D GLM schema',
                'imports': ['linkml:types'],
                'prefixes': {
                    'linkml': 'https://w3id.org/linkml/',
                    'glm': 'https://gridlabd.org/schema/glm/',
                },
                'default_prefix': 'glm',
                'classes': {},
                'enums': {}
            }

            # Add Complex type
            schema['classes']['Complex'] = {
                'description': 'Complex number with real and imaginary components',
                'attributes': {
                    'real': {
                        'range': 'float',
                        'required': True,
                        'description': 'Real component'
                    },
                    'imag': {
                        'range': 'float',
                        'required': True,
                        'description': 'Imaginary component'
                    }
                }
            }

        schema['classes'].setdefault('glm_object', GLM_OBJECT_CLASS)

        # Merge collected enums (new enums override existing ones with same name)
        for enum_name, enum_values in self.enums.items():
            schema['enums'][enum_name] = {
                'description': f'{enum_name} enumeration',
                'permissible_values': {}
            }

            for kw, value in enum_values.items():
                schema['enums'][enum_name]['permissible_values'][kw] = {
                    'description': f'{kw} option',
                    'meaning': f'glm:{value}'
                }

        # Write to file
        with open(output_file, 'w') as f:
            yaml.dump(schema, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        _log.info(f"  ✓ Generated: types/common.yaml ({len(schema['enums'])} enums)")

    def _generate_main_schema(self, parsed_classes: Dict):
        """Generate or update main.yaml that imports all modules.

        If main.yaml already exists, appends new module imports without
        overwriting existing ones.  Otherwise creates a fresh file.
        """
        output_file = self.output_dir / "main.yaml"

        if output_file.exists():
            # Load existing main.yaml and append new module imports
            with open(output_file) as f:
                schema = yaml.safe_load(f)
            existing_imports = set(schema.get('imports', []))
            for class_name in sorted(parsed_classes.keys()):
                imp = f'{self.module_name}/{class_name}'
                if imp not in existing_imports:
                    schema['imports'].append(imp)
            _log.info(f"  ✓ Updated: main.yaml (added {self.module_name} imports)")
        else:
            schema = {
                'id': 'https://gridlabd.org/schema/glm',
                'name': 'gridlabd_glm',
                'title': 'GridLAB-D GLM File Format Schema',
                'description': self._get_main_description(parsed_classes),
                'version': '1.0.0',
                'license': 'https://opensource.org/licenses/BSD-3-Clause',
                'prefixes': {
                    'linkml': 'https://w3id.org/linkml/',
                    'glm': 'https://gridlabd.org/schema/glm/',
                    'schema': 'http://schema.org/',
                    'xsd': 'http://www.w3.org/2001/XMLSchema#',
                },
                'default_prefix': 'glm',
                'default_range': 'string',
                'imports': ['linkml:types', 'types/common']
            }
            for class_name in sorted(parsed_classes.keys()):
                schema['imports'].append(f'{self.module_name}/{class_name}')
            _log.info(f"  ✓ Generated: main.yaml")

        with open(output_file, 'w') as f:
            yaml.dump(schema, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def _get_main_description(self, parsed_classes: Dict) -> str:
        """Generate description for main schema"""
        return f"""Complete LinkML schema for GridLAB-D GLM (GridLAB-D Model) file format.

This schema defines the structure of GridLAB-D configuration files including
modules, objects, and their properties.

Generated from C++ source code with {len(parsed_classes)} classes from the {self.module_name} module.

Features:
- Complete inheritance chains
- Property annotations for serialization
- Physical units (ft, VA, W, etc.)
- Enumeration definitions
- Documentation from source code

Follows the CIMHub architecture for round-trip conversion with CIM."""


def main():
    """Generate LinkML schemas from parsed classes"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate LinkML schemas from parsed GridLAB-D classes')
    parser.add_argument('--input', type=Path, required=True,
                        help='Input JSON file from property_parser.py')
    parser.add_argument('--output', type=Path,
                        help='Output directory for LinkML schemas (default: schema/linkml)')
    parser.add_argument('--module', type=str, default='powerflow',
                        help='GridLAB-D module name (default: powerflow)')

    args = parser.parse_args()

    if not args.output:
        args.output = Path('schema/linkml')

    generator = LinkMLGenerator(args.output, module_name=args.module)
    generator.generate_schemas(args.input)

    _log.info(f"\n{'='*60}")
    _log.info("Next steps:")
    _log.info("  1. Validate schema:")
    _log.info(f"     linkml-validate {args.output}/main.yaml")
    _log.info("  2. Generate Python dataclasses (gridlabd.py):")
    _log.info("     scripts/gen-schema.sh gridlabd")
    _log.info("  3. Generate documentation:")
    _log.info(f"     gen-markdown {args.output}/main.yaml -d docs/")
    _log.info(f"{'='*60}")


if __name__ == '__main__':
    main()

"""
GridLAB-D C++ Source Parser

Extracts class definitions from GridLAB-D C++ source files.
Uses hybrid approach: Python for extraction, LLM for parsing complex blocks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)


@dataclass
class PropertyDef:
    """Property definition extracted from gl_publish_variable"""
    name: str
    cpp_type: str          # PT_double, PT_object, PT_complex, etc.
    linkml_range: str      # float, string, Complex, etc.
    unit: Optional[str]    # Extracted from [unit] notation
    description: str
    required: bool = False
    enum_values: Dict[str, int] = None  # For PT_KEYWORD enumerations

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ClassBlock:
    """Extracted class metadata from C++ file"""
    name: str
    parent_class: Optional[str]  # From class X : public Y or PT_INHERIT
    module: str                  # powerflow, residential, etc.
    publish_block: str          # Raw gl_publish_variable block for LLM
    doc_comment: str            # Extracted from /** */ blocks
    source_file: Path
    header_file: Optional[Path] = None

    def to_dict(self):
        d = asdict(self)
        d['source_file'] = str(self.source_file)
        d['header_file'] = str(self.header_file) if self.header_file else None
        return d


class GridLABDCppExtractor:
    """
    Extract metadata blocks from GridLAB-D C++ source files.
    Does NOT parse property details - sends blocks to LLM for that.
    """

    def __init__(self, gridlabd_source_root: Path):
        self.source_root = Path(gridlabd_source_root)
        _log.info(f"Initialized C++ extractor with root: {self.source_root}")

    def extract_module(self, module_name: str) -> Dict[str, ClassBlock]:
        """Extract all class blocks from a module directory"""
        module_dir = self.source_root / module_name
        if not module_dir.exists():
            _log.error(f"Module directory not found: {module_dir}")
            return {}

        _log.info(f"Processing module: {module_name}")
        classes = {}

        cpp_files = list(module_dir.glob("*.cpp"))
        _log.info(f"Found {len(cpp_files)} C++ files")

        for cpp_file in cpp_files:
            try:
                class_block = self.extract_class_file(cpp_file, module_name)
                if class_block:
                    classes[class_block.name] = class_block
                    _log.info(f"  ✓ Extracted: {class_block.name}")
            except Exception as e:
                _log.error(f"  ✗ Error processing {cpp_file.name}: {e}")

        _log.info(f"Extracted {len(classes)} classes from {module_name}")
        return classes

    def extract_class_file(self, cpp_file: Path, module: str) -> Optional[ClassBlock]:
        """Extract class block from a single .cpp file"""
        content = cpp_file.read_text(encoding='utf-8', errors='ignore')

        # 1. Find class name from gl_register_class
        class_name = self._extract_class_name(content)
        if not class_name:
            return None

        # 2. Extract gl_publish_variable block
        publish_block = self._extract_publish_block(content)
        if not publish_block:
            _log.debug(f"No publish block in {cpp_file.name}")
            return None

        # 3. Extract parent class from PT_INHERIT
        parent_class = self._extract_parent_from_inherit(publish_block)

        # If no PT_INHERIT, try to find from header file
        if not parent_class:
            parent_class = self._extract_parent_from_header(cpp_file)

        # 4. Extract documentation comment
        doc_comment = self._extract_doc_comment(content)

        # 5. Find corresponding header file
        header_file = cpp_file.with_suffix('.h')
        if not header_file.exists():
            header_file = None

        return ClassBlock(
            name=class_name,
            parent_class=parent_class,
            module=module,
            publish_block=publish_block,
            doc_comment=doc_comment,
            source_file=cpp_file,
            header_file=header_file
        )

    def _extract_class_name(self, content: str) -> Optional[str]:
        """Extract class name from gl_register_class call"""
        # Pattern: gl_register_class(mod,"class_name",sizeof(...),...)
        pattern = r'gl_register_class\s*\(\s*\w+\s*,\s*"(\w+)"'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        return None

    def _extract_publish_block(self, content: str) -> Optional[str]:
        """Extract the full gl_publish_variable(..., nullptr) block"""
        # Find start of block
        start_pattern = r'gl_publish_variable\s*\(\s*oclass\s*,'
        start_match = re.search(start_pattern, content)
        if not start_match:
            return None

        start_pos = start_match.start()

        # Find end (nullptr followed by closing paren), balancing parens but
        # SKIPPING string literals — GridLAB-D descriptions such as
        # "Secondary series impedance (only used when ...)" contain unbalanced
        # parens that otherwise throw off the depth count and silently drop the
        # whole class (e.g. transformer_configuration).
        depth = 0
        in_block = False
        in_string = False
        escaped = False
        block_start = start_pos

        for i in range(start_pos, len(content)):
            ch = content[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == '\\':
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == '(':
                depth += 1
                in_block = True
            elif ch == ')':
                depth -= 1
                if depth == 0 and in_block:
                    block = content[block_start:i + 1]
                    return block if 'nullptr' in block else None

        return None

    def _extract_parent_from_inherit(self, publish_block: str) -> Optional[str]:
        """Extract parent class from PT_INHERIT in publish block"""
        # Pattern: PT_INHERIT, "parent_name"
        pattern = r'PT_INHERIT\s*,\s*"(\w+)"'
        match = re.search(pattern, publish_block)
        if match:
            return match.group(1)
        return None

    def _extract_parent_from_header(self, cpp_file: Path) -> Optional[str]:
        """Extract parent class from header file: class X : public Y"""
        header_file = cpp_file.with_suffix('.h')
        if not header_file.exists():
            return None

        try:
            content = header_file.read_text(encoding='utf-8', errors='ignore')
            # Pattern: class class_name : public parent_class
            # More permissive to handle various formatting
            pattern = r'class\s+(\w+)\s*:\s*public\s+(\w+)'
            match = re.search(pattern, content)
            if match:
                return match.group(2)
        except Exception as e:
            _log.debug(f"Could not read header {header_file}: {e}")

        return None

    def _extract_doc_comment(self, content: str) -> str:
        """Extract /** */ documentation comment from file header"""
        # Find the first /** ... */ block (usually at top of file)
        pattern = r'/\*\*(.*?)\*/'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            # Clean up the comment
            comment = match.group(1)
            # Remove leading * from each line
            lines = []
            for line in comment.split('\n'):
                line = line.strip()
                if line.startswith('*'):
                    line = line[1:].strip()
                if line and not line.startswith('$Id'):
                    lines.append(line)
            return '\n'.join(lines)
        return ""


def main():
    """Extract class blocks from powerflow module"""
    import argparse

    parser = argparse.ArgumentParser(description='Extract GridLAB-D class metadata from C++')
    parser.add_argument('--source', type=Path, required=True,
                        help='Path to GridLAB-D source root (contains powerflow/, residential/, etc.)')
    parser.add_argument('--module', type=str, default='powerflow',
                        help='Module to parse (default: powerflow)')
    parser.add_argument('--output', type=Path,
                        help='Output JSON file (default: extracted_classes.json)')

    args = parser.parse_args()

    if not args.output:
        args.output = Path(f"extracted_{args.module}_classes.json")

    extractor = GridLABDCppExtractor(args.source)
    classes = extractor.extract_module(args.module)

    # Convert to JSON-serializable format
    output = {
        class_name: block.to_dict()
        for class_name, block in classes.items()
    }

    # Write output
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)

    _log.info(f"\n{'='*60}")
    _log.info(f"Extraction complete!")
    _log.info(f"{'='*60}")
    _log.info(f"Classes extracted: {len(classes)}")
    _log.info(f"Output written to: {args.output}")
    _log.info(f"\nNext step: Parse property blocks with LLM")


if __name__ == '__main__':
    main()

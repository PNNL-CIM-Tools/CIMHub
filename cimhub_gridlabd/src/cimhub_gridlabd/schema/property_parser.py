"""Property Block Parser — token-oriented.

Takes the ``gl_publish_variable`` blocks extracted by ``cpp_parser.py`` and
parses them into structured property definitions.

The parse is **token-oriented**, not line-oriented.  GridLAB-D's sources are
clang-formatted, so a single declaration wraps across several lines and several
``PT_`` tokens share one line::

    PT_KEYWORD, "N", (gld::set)PHASE_N, PT_enumeration, "switchA",
    PADDR(switchA_state), PT_DESCRIPTION,

An earlier line-oriented parser tested ``line.startswith('PT_')`` and so
misclassified ``switchA`` (declared on a line starting with ``PT_KEYWORD``) as
an enum keyword — silently dropping 417 published properties across 51 classes,
enumerations hit hardest.  This parser instead tokenizes the whole block on
commas at paren-depth 0 and walks the token stream as a state machine, so wrap
points are irrelevant.

It **fails loudly**: a token that cannot be classified raises, rather than being
swallowed per-class as the old parser did.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)


class PublishBlockParseError(ValueError):
    """A token in a publish block could not be classified — a parser defect."""


@dataclass
class ParsedProperty:
    """Structured property definition"""
    name: str
    cpp_type: str
    linkml_range: str
    unit: Optional[str] = None
    description: Optional[str] = None
    required: bool = False
    enum_values: Optional[Dict[str, str]] = None  # keyword -> value

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ParsedClass:
    """Complete parsed class with properties"""
    name: str
    parent_class: Optional[str]
    module: str
    doc_comment: str
    properties: List[ParsedProperty]
    source_file: str
    header_file: Optional[str]

    def to_dict(self):
        d = asdict(self)
        d['properties'] = [p.to_dict() for p in self.properties]
        return d


# ---------------------------------------------------------------------------
# Token-oriented extraction (shared with the schema guard tests)
# ---------------------------------------------------------------------------

# A double-quoted C string literal, honouring backslash escapes.
_STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"')

# name + optional [unit] suffix, e.g. "capacitor_A[VAr]" -> ("capacitor_A", "VAr")
_NAME_UNIT_RE = re.compile(r'^(.*?)\[(.*?)\]$')

# Every gl_publish_variable PT_ type we map. PT_KEYWORD / PT_DESCRIPTION /
# PT_INHERIT are structural markers, not property types, and are handled
# explicitly in the walk.
_PT_TYPE_RANGE = {
    'PT_double': 'float',
    'PT_double_units': 'float',
    'PT_int16': 'integer',
    'PT_int32': 'integer',
    'PT_int64': 'integer',
    'PT_char1024': 'string',
    'PT_char256': 'string',
    'PT_char32': 'string',
    'PT_char8': 'string',
    'PT_object': 'string',      # object reference by name
    'PT_complex': 'Complex',    # custom value type
    'PT_bool': 'boolean',
    'PT_enumeration': 'string',  # becomes a typed enum
    'PT_set': 'string',          # phase sets etc. — also enum-like
    'PT_timestamp': 'string',
    'PT_loadshape': 'string',
    'PT_enduse': 'string',
    'PT_random': 'string',
    'PT_method': 'string',
    'PT_double_array': 'string',
    'PT_complex_array': 'string',
}

# Enumerated types carry PT_KEYWORD triples that define their domain.
_ENUM_PT_TYPES = {'PT_enumeration', 'PT_set'}

# Structural markers that are not property declarations.
_STRUCTURAL = {'PT_INHERIT', 'PT_DESCRIPTION', 'PT_KEYWORD'}


def _is_string(tok: str) -> bool:
    return bool(_STRING_RE.fullmatch(tok))


def _unquote(tok: str) -> str:
    return tok[1:-1] if _is_string(tok) else tok


def _strip_comments(block: str) -> str:
    """Remove C/C++ comments and preprocessor lines from a publish block.

    GridLAB-D publish blocks are peppered with ``//`` line comments, ``/* */``
    blocks, and the occasional ``#ifdef``/``#endif`` — all noise between real
    declarations.  Stripping them before tokenizing keeps a comment from being
    mistaken for an unclassifiable token.  String literals are preserved so a
    ``//`` inside a description (a URL, say) is not clipped.
    """
    out: List[str] = []
    i = 0
    n = len(block)
    while i < n:
        c = block[i]
        if c == '"':
            m = _STRING_RE.match(block, i)
            if m:
                out.append(m.group(0))
                i = m.end()
                continue
            out.append(c)
            i += 1
            continue
        if c == '/' and i + 1 < n and block[i + 1] == '/':
            j = block.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == '/' and i + 1 < n and block[i + 1] == '*':
            j = block.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '#' and (i == 0 or block[i - 1] == '\n'):
            j = block.find('\n', i)
            i = n if j < 0 else j
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def strip_publish_call(block: str) -> str:
    """Return the argument list inside ``gl_publish_variable(...)``.

    Accepts either the full ``gl_publish_variable(oclass, ...nullptr)`` call
    (as ``cpp_parser`` extracts) or a bare argument list.  Trims the leading
    ``oclass`` and the trailing ``nullptr``, and strips C/C++ comments.
    """
    b = _strip_comments(block).strip()
    m = re.search(r'gl_publish_variable\s*\(', b)
    if m:
        # Slice to the matching close paren, skipping string literals — a
        # description like "... (only used ...)" carries unbalanced parens.
        start = m.end()
        depth = 1
        i = start
        while i < len(b):
            c = b[i]
            if c == '"':
                sm = _STRING_RE.match(b, i)
                if sm:
                    i = sm.end()
                    continue
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    b = b[start:i]
                    break
            i += 1
    b = b.strip()
    # drop a leading "oclass," argument
    b = re.sub(r'^\s*oclass\s*,', '', b, count=1).strip()
    # drop a trailing nullptr / NULL argument
    b = re.sub(r',?\s*(nullptr|NULL)\s*,?\s*$', '', b).strip()
    return b


def tokenize(block: str) -> List[str]:
    """Split a publish argument list into comma-separated tokens.

    Commas inside string literals and inside parens (``PADDR(a)``,
    ``(gld::set)PHASE_A``) do not split.  Each string literal is emitted as its
    own token, quotes preserved — so two adjacent literals (C implicit
    concatenation across lines) become two tokens, which the ``PT_DESCRIPTION``
    consumer rejoins.
    """
    tokens: List[str] = []
    buf: List[str] = []
    depth = 0
    i = 0
    n = len(block)

    def _flush():
        tok = ''.join(buf).strip()
        if tok:
            tokens.append(tok)
        buf.clear()

    while i < n:
        c = block[i]
        if c == '"':
            m = _STRING_RE.match(block, i)
            if m:
                _flush()                 # end any pending non-string token
                tokens.append(m.group(0))  # the literal stands alone
                i = m.end()
                continue
            buf.append(c)  # unterminated quote — keep the char, let it fail loudly later
            i += 1
            continue
        if c == '(':
            depth += 1
            buf.append(c)
        elif c == ')':
            depth -= 1
            buf.append(c)
        elif c == ',' and depth == 0:
            _flush()
        else:
            buf.append(c)
        i += 1
    _flush()
    return tokens


def _looks_like_value(tok: str) -> bool:
    """True for tokens that are legitimate stray values, not misparses.

    These appear between declarations and carry no property meaning:
    ``PADDR(field)``, C casts and their operands (``(gld::set)PHASE_A``,
    ``(enumeration)OPEN``, ``PHASE_N``), numeric literals, and ``PT_ACCESS`` /
    flag tokens.  Anything else that is not a known PT_ type is a real
    surprise and must fail loudly.
    """
    if tok.startswith('PADDR(') or tok.startswith('PT_ACCESS'):
        return True
    if tok.startswith('PA_') or tok.startswith('PT_'):
        # PT_ tokens not in our maps (flags like PT_ACCESS, PT_SIZE) — tolerate
        return True
    # a cast or bare identifier / enum operand: (cast)IDENT, IDENT, 0x..., digits
    if re.fullmatch(r'\(?[\w:]+\)?[\w:.|+\- ]*', tok):
        return True
    return False


def extract_properties(block: str, *, class_name: str = "?", source: str = "?"):
    """Parse a publish block into (properties, parent_class).

    Args:
        block: the ``gl_publish_variable`` call or its bare argument list.
        class_name / source: identity for loud error messages.

    Returns:
        ``(List[ParsedProperty], Optional[str])`` — the parent from PT_INHERIT.

    Raises:
        PublishBlockParseError: a token could not be classified.
    """
    tokens = tokenize(strip_publish_call(block))
    props: List[ParsedProperty] = []
    parent: Optional[str] = None
    cur: Optional[ParsedProperty] = None
    enum_order: List[str] = []

    def _close_enum():
        if cur is not None and cur.cpp_type in _ENUM_PT_TYPES and enum_order:
            cur.enum_values = {kw: i for i, kw in enumerate(enum_order)}

    idx = 0
    N = len(tokens)
    while idx < N:
        tok = tokens[idx]

        if tok == 'PT_INHERIT':
            if idx + 1 < N and _is_string(tokens[idx + 1]):
                parent = _unquote(tokens[idx + 1])
                idx += 2
                continue
            idx += 1
            continue

        if tok == 'PT_DESCRIPTION':
            # consume the following implicitly-concatenated string literals
            j = idx + 1
            parts: List[str] = []
            while j < N and _is_string(tokens[j]):
                parts.append(_unquote(tokens[j]))
                j += 1
            if cur is not None and parts:
                cur.description = ''.join(parts)
            idx = j
            continue

        if tok == 'PT_KEYWORD':
            # PT_KEYWORD, "NAME", value  — accumulate onto the open enum property
            if idx + 1 < N and _is_string(tokens[idx + 1]):
                enum_order.append(_unquote(tokens[idx + 1]))
                idx += 3  # KEYWORD, name, value
                continue
            idx += 1
            continue

        if tok in _PT_TYPE_RANGE:
            # new property: PT_type, "name[unit]", PADDR(field)
            if not (idx + 1 < N and _is_string(tokens[idx + 1])):
                # a PT_ type with no name — malformed source, but not fatal
                idx += 1
                continue
            _close_enum()
            enum_order = []

            name_raw = _unquote(tokens[idx + 1])
            unit = None
            name = name_raw
            mb = _NAME_UNIT_RE.match(name_raw)
            if mb:
                name, unit = mb.group(1), mb.group(2)

            linkml_range = _PT_TYPE_RANGE[tok]
            # Only PT_enumeration becomes a typed (single-valued) LinkML enum.
            # PT_set is a bitwise combination — GLM writes e.g. phases="ABCN",
            # which no single permissible value matches; forcing it into an enum
            # makes the generated dataclass reject every real object on read.
            # Keep PT_set as a plain string (its keywords still accumulate below
            # for documentation, but the range stays string).
            if tok == 'PT_enumeration':
                linkml_range = ''.join(w.capitalize() for w in name.split('_'))

            cur = ParsedProperty(
                name=name,
                cpp_type=tok,
                linkml_range=linkml_range,
                unit=unit,
                description=None,
                required=False,
            )
            props.append(cur)
            idx += 2
            continue

        # not a marker, not a PT_ type — either a legitimate stray value or a
        # genuine surprise we must not hide.
        if _looks_like_value(tok):
            idx += 1
            continue

        raise PublishBlockParseError(
            f"{class_name} ({source}): unclassifiable token {tok!r} "
            f"at position {idx} of publish block"
        )

    _close_enum()
    return props, parent


class PropertyBlockParser:
    """Parse gl_publish_variable blocks into ParsedClass records."""

    def parse_extracted_file(self, extracted_json_path: Path) -> Dict[str, ParsedClass]:
        """Parse all classes from an extracted JSON file (from cpp_parser.py)."""
        _log.info(f"Loading extracted classes from: {extracted_json_path}")

        with open(extracted_json_path) as f:
            extracted_data = json.load(f)

        parsed_classes: Dict[str, ParsedClass] = {}
        total = len(extracted_data)

        for i, (class_name, class_data) in enumerate(extracted_data.items(), 1):
            _log.info(f"[{i}/{total}] Parsing {class_name}...")
            parsed = self.parse_class_block(class_data)
            parsed_classes[class_name] = parsed
            _log.info(f"  ✓ {len(parsed.properties)} properties")

        _log.info(f"\nParsed {len(parsed_classes)}/{total} classes")
        return parsed_classes

    def parse_class_block(self, class_data: dict) -> ParsedClass:
        """Parse a single class block."""
        properties, inherited_parent = extract_properties(
            class_data['publish_block'],
            class_name=class_data.get('name', '?'),
            source=str(class_data.get('source_file', '?')),
        )
        # PT_INHERIT in the block is the authority; fall back to the header-derived
        # parent that cpp_parser recorded.
        parent = inherited_parent or class_data.get('parent_class')

        return ParsedClass(
            name=class_data['name'],
            parent_class=parent,
            module=class_data['module'],
            doc_comment=class_data.get('doc_comment', ''),
            properties=properties,
            source_file=class_data['source_file'],
            header_file=class_data.get('header_file'),
        )


def main():
    """Parse extracted class blocks"""
    import argparse

    parser = argparse.ArgumentParser(description='Parse GridLAB-D property blocks')
    parser.add_argument('--input', type=Path, required=True,
                        help='Input JSON file from cpp_parser.py')
    parser.add_argument('--output', type=Path,
                        help='Output JSON file (default: parsed_classes.json)')

    args = parser.parse_args()

    if not args.output:
        args.output = Path(args.input.stem.replace('extracted', 'parsed') + '.json')

    parser_obj = PropertyBlockParser()
    parsed_classes = parser_obj.parse_extracted_file(args.input)

    output = {
        class_name: parsed_class.to_dict()
        for class_name, parsed_class in parsed_classes.items()
    }

    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)

    _log.info(f"\n{'='*60}")
    _log.info(f"Parsing complete!")
    _log.info(f"{'='*60}")
    _log.info(f"Classes parsed: {len(parsed_classes)}")
    _log.info(f"Output written to: {args.output}")
    _log.info(f"\nNext step: Generate LinkML schemas")


if __name__ == '__main__':
    main()

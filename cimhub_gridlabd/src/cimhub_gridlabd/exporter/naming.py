"""GLM names for exported objects (``EXPORT_MAPPING.md#names``, decision X1).

The text comes from the shared switch (``cimhub_core.names``: CIM ``name``, ``mRID`` or ``uri()``), sanitized for
GridLAB-D (``glm_safe_name``). GLM names are global, so there is one namespace: two objects that land on one name
raise, because GridLAB-D would refuse the deck or link the wrong object.
"""

from __future__ import annotations

import re

from cimhub_core.names import export_name, resolve_name_source

#: A ``.`` makes GridLAB-D read ``object.property``; ``:`` is its ``class:id`` form; the rest end or break a
#: quoted token. Everything else is allowed inside quotes (relax_naming_rules), checked in GridLAB-D 6.0.
_GLM_UNSAFE_RE = re.compile(r"""[\s.:"';{}$]+""")


def glm_safe_name(text: str) -> str:
    """``text`` with each run of characters GridLAB-D cannot take in a name replaced by ``_``."""
    return _GLM_UNSAFE_RE.sub("_", text)


class Names:
    """Every name written to one deck."""

    def __init__(self, source: str | None = None):
        self.source = resolve_name_source(source)
        self._taken: dict[str, tuple[str, str]] = {}  # name -> (mRID, suffix)

    def name(self, obj, *, suffix: str = "", drop: str = "") -> str:
        """``obj``'s GLM name; ``suffix`` (``_star``) names one of several GLM objects made from it, ``drop`` is an
        ending its text must have and loses (a regulator's units ``<base>_<phase>`` written as one, ``<base>``)."""
        text = export_name(obj, self.source)
        if drop:
            if not text.endswith(drop):
                raise ValueError(f"{type(obj).__name__} {obj.mRID!r}: {text!r} does not end in {drop!r}")
            text = text[:-len(drop)]
        return self._claim(glm_safe_name(text + suffix), obj, f"-{drop}{suffix}" if drop else suffix)

    def _claim(self, name: str, obj, suffix: str) -> str:
        owner = (obj.mRID, suffix)
        taken = self._taken.setdefault(name, owner)
        if taken != owner:
            raise ValueError(f"{type(obj).__name__} {obj.mRID!r} and {taken[0]!r} are both named {name!r} in GLM "
                             f"(name source {self.source!r})")
        return name

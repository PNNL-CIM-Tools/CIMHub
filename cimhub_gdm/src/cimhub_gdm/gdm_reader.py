"""Load a GDM `DistributionSystem` from its JSON file.

GDM provides the deserialization; this keeps callers out of `gdm.*`. It is the only
module in the spoke that touches the filesystem.
"""

from __future__ import annotations

from gdm.systems.distribution import DistributionSystem


def read_gdm(path: str) -> DistributionSystem:
    """Load a GDM DistributionSystem from a JSON file."""
    return DistributionSystem.from_json(path)

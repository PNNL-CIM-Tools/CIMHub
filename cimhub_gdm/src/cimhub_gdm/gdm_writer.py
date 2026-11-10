"""Write a GDM `DistributionSystem` to its JSON file.

GDM provides the serialization; this keeps callers out of `gdm.*`. With `gdm_reader.py`, it is the only module in
the spoke that touches the filesystem.
"""

from __future__ import annotations

from gdm.systems.distribution import DistributionSystem


def write_gdm(system: DistributionSystem, path: str) -> None:
    """Write ``system`` to the JSON file ``path``, replacing it if it exists (``read_gdm`` reads it back)."""
    system.to_json(path, overwrite=True)

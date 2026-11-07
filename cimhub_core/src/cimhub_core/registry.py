"""Decorator-based converter registry.

Each sub-package creates its own ``ConverterRegistry`` instance and
registers converter functions against LinkML schema classes::

    from cimhub_core import ConverterRegistry

    registry = ConverterRegistry()

    @registry.register(schema.Load)
    def convert_load(load_obj, network):
        ...

    # Dispatch at conversion time:
    converter = registry.get(schema.Load)
    converter(load_obj, network)
"""

from __future__ import annotations

__all__ = ["ConverterRegistry"]


class ConverterRegistry:
    """Map LinkML schema classes to converter functions.

    One instance per format direction (e.g. ``psm_importer_registry``,
    ``dss_exporter_registry``).
    """

    def __init__(self) -> None:
        self._registry: dict[type, callable] = {}

    # -- Registration -------------------------------------------------------

    def register(self, cls: type):
        """Decorator that registers the decorated function for *cls*."""
        def decorator(func):
            self._registry[cls] = func
            return func
        return decorator

    # -- Lookup -------------------------------------------------------------

    def get(self, cls: type):
        """Return the converter function for *cls*.

        Raises:
            KeyError: If no converter has been registered for *cls*.
        """
        return self._registry.get(cls)

    def classes(self):
        """Return all registered schema classes."""
        return self._registry.keys()

    # -- Dunder support -----------------------------------------------------

    def __contains__(self, cls: type) -> bool:
        return cls in self._registry

    def __iter__(self):
        return iter(self._registry)

    def __len__(self) -> int:
        return len(self._registry)

    def __repr__(self) -> str:
        names = [cls.__name__ for cls in self._registry]
        return f"ConverterRegistry({names})"

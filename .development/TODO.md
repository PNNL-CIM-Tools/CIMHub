# TODO

Deferred work that is decided but not scheduled. Upstream asks go in `UPSTREAM_REQUESTS.md` instead.

- **Inverter reactive capability (DSS PVSystem, M38).** Below cutout the engine clamps a |kvar| above kVA to
  kvarMax; the importer raises instead. Once the CIM side models reactive capability (kvarMax, kvarMaxAbs,
  a capability curve), map the clamp instead of raising.

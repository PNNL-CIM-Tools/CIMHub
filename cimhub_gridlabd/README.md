# cimhub_gridlabd

GridLAB-D (`.glm`) to and from CIM (cim18v17). Import goes through `.cimtbl` artifacts: `GlmReader` reads a `.glm` into the native
LinkML dataclasses, the mappers write one `.cimtbl` document per GLM class, and cimtables builds the CIM from that
text. Export (`GlmExporter`, `cim_to_glm`) reads CIM through the core getters and writes a `.glm` with `GlmWriter`.
Plan: `.development/GLM_REWRITE_PLAN.md`; specs: `docs/CIMTBL_MAPPING.md` (import), `docs/EXPORT_MAPPING.md` (export).

```bash
pip install --pre cimhub-gridlabd      # also installs cimhub-core
```

Python 3.11 or later. Version 2.1 is in alpha.

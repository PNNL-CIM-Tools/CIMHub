# cimhub_gridlabd

GridLAB-D (`.glm`) to and from CIM (cim18v17). Import goes through `.cimtbl` artifacts: `GlmReader` reads a `.glm` into the native
LinkML dataclasses, the mappers write one `.cimtbl` document per GLM class, and cimtables builds the CIM from that
text. Export (`GlmExporter`, `cim_to_glm`) reads CIM through the core getters and writes a `.glm` with `GlmWriter`.
Plan: `.development/GLM_REWRITE_PLAN.md`; specs: `docs/CIMTBL_MAPPING.md` (import), `docs/EXPORT_MAPPING.md` (export).

```bash
pip install --pre cimhub-gridlabd      # also installs cimhub-core
```

Python 3.11 or later. Version 2.1 is in alpha.

## Documentation

- [Documentation](https://pnnl-cim-tools.github.io/CIMHub/gridlabd/): user guide, conversion reference, developer docs and the LinkML schema reference
- [GridLAB-D to `.cimtbl` mapping spec](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gridlabd/docs/CIMTBL_MAPPING.md)
- [CIM to GridLAB-D export spec](https://github.com/PNNL-CIM-Tools/CIMHub/blob/main/cimhub_gridlabd/docs/EXPORT_MAPPING.md)

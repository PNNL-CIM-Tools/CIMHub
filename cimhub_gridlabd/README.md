# cimhub_gridlabd

GridLAB-D (`.glm`) to CIM (cim18v17) through `.cimtbl` artifacts: `GlmReader` reads a `.glm` into the native
LinkML dataclasses, the mappers write one `.cimtbl` document per GLM class, and cimtables builds the CIM from that
text. Plan: `.development/GLM_REWRITE_PLAN.md`; mapping spec: `docs/CIMTBL_MAPPING.md`.

```bash
pip install --pre cimhub-gridlabd      # also installs cimhub-core
```

Python 3.11 or later. Version 2.1 is in alpha. There is no CIM to GLM exporter yet.

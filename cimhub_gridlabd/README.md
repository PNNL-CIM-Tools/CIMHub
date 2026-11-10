# cimhub_gridlabd

GridLAB-D (`.glm`) to CIM (cim18v17) through `.cimtbl` artifacts: `GlmReader` reads a `.glm` into the native
LinkML dataclasses, the mappers write one `.cimtbl` document per GLM class, and cimtables builds the CIM from that
text. Plan: `.development/GLM_REWRITE_PLAN.md`; mapping spec: `docs/CIMTBL_MAPPING.md`.

# Phase 2 — Coordinate and Grid Core Status

Status: implementation complete on `agent/phase-2-coordinate-grid-core`; engineer review required before Phase 3

## Completed backlog

- [x] P2-001 package skeleton and dependency-direction test
- [x] P2-002 strict Unit, Length, Point2D, Point3D and tolerance value objects
- [x] P2-003 CoordinateSystem2D and invertible/composable AffineTransform2D
- [x] P2-004 one-, two- and three-plus-point calibration with residual reporting
- [x] P2-005 storeys and physical levels, including footing, split and roof levels
- [x] P2-006 orthogonal, rotated and offset GridLine2D/GridIntersection/GridSystem models plus an in-memory GridManager application service
- [x] P2-007 central source-quality tolerance profiles and deterministic snapping/node merging
- [x] P2-008 ephemeral stable-entity ↔ Canvas-item projection map
- [x] P2-009 legacy Canvas/CAD coordinate characterisation and round-trip tests
- [x] P2-010 ADR-001, migration notes and this completion report

## Explicit exclusions preserved

Phase 2 does not implement:

- SQLite/R-Tree engineering dataset persistence;
- stable revision/audit schema;
- PDF/DXF/IFC production round trip;
- architectural semantic recognition;
- structural load-path generation;
- finite-element analysis;
- Australian Standards calculations;
- structural drawing generation.

## Assumptions requiring later confirmation

- tolerance values are provisional software defaults;
- no real legacy client project fixture was available;
- the initial project coordinate system is millimetres, X right, Y up, Z up;
- Tkinter remains during controlled migration;
- Python 3.10+ on Windows and macOS is the initial runtime target for the pure domain core.

## Phase 3 entry gate

Before Phase 3 persistence implementation, Aaron should review:

1. ADR-001 coordinate and tolerance policy;
2. real legacy `.dieselpdf.json` fixtures and expected measurements;
3. identity/revision/review-status roles for ADR-002;
4. project packaging choice: one `.diesel.db` plus artefact folder versus a project directory bundle.

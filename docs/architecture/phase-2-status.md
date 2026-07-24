# Phase 2 — Coordinate and Grid Core Status

Status: implementation and engineering-policy refinements complete on `agent/phase-2-coordinate-grid-core`; final PR review required before Phase 3

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

## Engineering review refinements completed

- [x] permanent origin policy based on Grid, survey control, building corner or explicit datum
- [x] shared project X/Y across all storeys
- [x] project-relative Z to AHD or survey-RL mapping
- [x] separate RMS calibration target and maximum rejection limit
- [x] explicit calibration pass, warning and reject outcomes
- [x] zoom-aware 8-pixel pointer snapping with a project-distance cap
- [x] separate automatic merge, suggested merge and keep-separate bands
- [x] DPI and drawing-scale-derived raster tolerance profiles
- [x] separate manual typed and manual pointer profiles
- [x] prototype-default status recorded in each tolerance profile
- [x] regression tests for all policy refinements

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

## Assumptions and deferred evidence

- tolerance values remain configurable prototype software defaults pending real-project calibration;
- no real legacy client project fixture was available;
- the project coordinate system is millimetres, X right, Y up and Z up;
- the project origin is an approved stable engineering datum, not a PDF or Canvas origin;
- all storeys share project X/Y;
- Tkinter remains during controlled migration;
- Python 3.10+ on Windows and macOS is the initial runtime target for the pure domain core.

## Definition of Phase 2 complete

Phase 2 is complete when:

1. all Phase 2 domain and application tests pass;
2. GitHub Actions compiles the application and runs the complete repository test suite;
3. ADR-001 records the engineering review conditions;
4. PR #6 contains the final implementation and remains isolated from `main` until review;
5. the lack of real legacy project fixtures is recorded as deferred evidence rather than silently treated as complete production migration validation.

## Phase 3 entry gate

Before Phase 3 persistence implementation, Aaron should review or provide:

1. final PR #6 diff and CI status;
2. at least one real de-identified legacy `.dieselpdf.json` fixture when available;
3. identity, revision and review-status roles for ADR-002;
4. project packaging choice: one `.diesel.db` plus artefact folder versus a project directory bundle.

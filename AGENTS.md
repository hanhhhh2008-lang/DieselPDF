# DieselPDF Codex Engineering Instructions

## Mission

Develop DieselPDF into an engineer-in-the-loop platform that accepts architectural PDF, DXF, DWG or IFC inputs and progressively generates coordinated preliminary structural drawings, finite-element analysis data, Australian Standards design checks and automated QA outputs.

The engineering owner and final reviewer is Aaron Han, a NSW structural, forensic and remedial engineer.

## Current authorised scope

Phase 1 is complete on Draft PR #4. Aaron expressly authorised Phase 2 on 22 July 2026.

Phase 2 is limited to the coordinate and grid core:

- pure domain package skeleton;
- strict units and points;
- coordinate systems and affine transforms;
- one-, two- and three-plus-point calibration with residuals;
- storeys and physical levels;
- grids, grid intersections and an in-memory GridManager;
- centralized tolerance and snapping services;
- ephemeral Canvas projection mapping;
- legacy coordinate characterisation tests;
- ADR and migration documentation.

Do not begin Phase 3 persistence, semantic recognition, structural topology, FEA, Australian Standards design checks or drawing generation without Aaron's next approval. Do not rewrite the Tkinter UI or modify `main` directly.

Work on a dedicated branch or worktree. Read all files under `docs/project-bible/`, the Phase 1 architecture documents and GitHub Issue #2 before changing architecture.

## Non-negotiable architecture rules

1. The Diesel engineering dataset is the single source of truth.
2. Tkinter Canvas, PDF, DXF, DWG, IFC and FEA models are adapters or views around that dataset.
3. Permanent geometry is stored in project coordinates, normally millimetres with X right, Y up and Z by storey or level.
4. Every geometric entity and semantic object has a stable ID, source traceability, schema version, revision and review status.
5. Raw extracted geometry and engineering semantic objects remain separate but linked.
6. AI may propose classifications and structural arrangements but may not silently become final geometry or the final design calculation engine.
7. Generic FEA and Australian Standards design checks are separate deterministic layers.
8. All calculations are reproducible, unit-aware, versioned and traceable to inputs, assumptions, code edition and clauses.
9. Existing `.dieselpdf.json` projects require a tested, immutable migration path.
10. All generated drawings remain `PRELIMINARY — NOT FOR CONSTRUCTION — ENGINEER REVIEW REQUIRED` until Aaron approves final issue.

## Engineering basis

Use current project-adopted Australian Standards and NCC requirements. Future modules may include AS/NZS 1170, AS 4055, AS 1684.2, AS 1720.1, AS 2870, AS 3600, AS 4100, AS 3700, current AS 4773 provisions, AS/NZS 4600 and AS/NZS 1664 as applicable.

Cite clauses wherever practicable, show calculations, state assumptions and identify critical missing information. Do not claim equivalence to SpaceGass or ETABS without documented benchmark evidence.

## Phase 2 completion gate

Before Phase 2 is considered complete:

- all Phase 2 tests pass;
- domain dependency-direction tests pass;
- legacy Canvas/project formulas are characterised;
- ADR-001 and migration notes are present;
- a completion report lists assumptions and Phase 3 blockers;
- Aaron reviews the Phase 2 PR before Phase 3 begins.

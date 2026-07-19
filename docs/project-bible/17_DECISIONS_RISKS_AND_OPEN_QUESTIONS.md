# Decisions, Risks and Open Questions

## Current provisional decisions

These decisions are provisional until Phase 1 verification and Aaron's approval.

### D-001 — Dataset as source of truth

Use the Diesel engineering dataset, not Tkinter Canvas, PDF or CAD, as the permanent project model.

### D-002 — Separate raw geometry and semantics

Preserve imported geometry independently from architectural and structural interpretation.

### D-003 — Stable identity and provenance

Every entity and engineering object requires stable IDs, source links, schema version, revision and review state.

### D-004 — Project coordinates

Use project millimetres and explicit reversible transforms among PDF, CAD, sheet, Canvas, storey and solver coordinates.

### D-005 — Modular migration

Use a strangler migration around the current prototype rather than an immediate full rewrite.

### D-006 — Neutral FEA model

Keep a solver-independent AnalysisModel and result schema. Do not bind project data to PyNite, OpenSees or any other backend.

### D-007 — Tiered solvers

Evaluate a lightweight transparent frame solver for initial residential work and a separate advanced backend for nonlinear, shell and dynamic work.

### D-008 — Separate Australian design layer

Generic FEA actions feed deterministic Australian Standards modules. Solver output is not code compliance.

### D-009 — AI as proposal

AI recognition and layout generation produce confidence-scored proposals requiring deterministic checks and engineer approval.

### D-010 — Controlled initial scope

Begin with conventional NSW Class 1 and Class 10 residential projects and route unusual conditions to manual engineering.

## Principal risks

### R-001 — Incorrect source geometry

A PDF may contain vector paths that are clipped, duplicated, transformed, flattened or not drawn to scale.

Mitigation:

- preserve source coordinates and transforms;
- reconcile dimensions;
- show confidence and calibration QA;
- require geometry approval.

### R-002 — Monolithic code migration

Refactoring the current application may break working markup and export behaviour.

Mitigation:

- characterisation tests;
- adapter wrappers;
- one object category at a time;
- legacy importer and rollback;
- no uncontrolled rewrite.

### R-003 — Solver misuse

A capable FEA engine can produce plausible but incorrect results from bad restraints, axes, releases, meshes or nonlinear settings.

Mitigation:

- neutral validation rules;
- visual model diagnostics;
- benchmark suite;
- restricted validated capability declarations;
- engineer approval.

### R-004 — False engineering confidence

Users may treat generated drawings as certified.

Mitigation:

- mandatory preliminary status;
- approval gates;
- issue permissions;
- unresolved-risk banners;
- audit trail.

### R-005 — Australian code scope

Simplified provisions may be applied outside scope or standards may change.

Mitigation:

- explicit scope gates;
- code edition records;
- clause-linked modules;
- current adoption verification before formal issue;
- manual route for out-of-scope cases.

### R-006 — Licensing

PDF, CAD, BIM and solver dependencies may impose obligations incompatible with commercial distribution.

Mitigation:

- Phase 1 legal/licence inventory;
- isolate optional tools;
- avoid copying incompatible code;
- preserve attribution and notices;
- obtain legal advice before commercial release.

### R-007 — Data and client confidentiality

Architectural and structural projects contain sensitive client data.

Mitigation:

- local-first processing;
- explicit cloud opt-in;
- access control and encryption where required;
- redact training datasets;
- do not train external models on client data without authority.

### R-008 — AI training-data mismatch

Public floorplan datasets may not represent Australian drawing conventions.

Mitigation:

- use deterministic vector extraction first;
- curate Australian project examples with permission;
- measure confidence calibration;
- engineer corrections and local regression tests.

### R-009 — Vendor and platform deployment

A solver or CAD adapter may work on one platform but be impractical on Windows or macOS.

Mitigation:

- deployment scoring in Phase 1;
- isolated subprocess or container adapters;
- optional advanced backends;
- continuous tests on both target platforms.

### R-010 — Uncontrolled assumptions

The system may fill missing loads, materials, restraints or soil properties with defaults.

Mitigation:

- unknown remains unknown;
- assumptions register;
- sensitivity checks;
- issue blockers for critical missing inputs;
- engineer confirmation.

## Open architecture questions for Phase 1

1. Retain Tkinter through Phase 4 or introduce a new UI framework earlier?
2. Use one SQLite file with embedded project assets or a project folder with a manifest and database?
3. Which geometry representation best preserves CAD curves while supporting Shapely operations?
4. Which stable-ID metadata survives the required DXF/DWG workflows most reliably?
5. Should GeoParquet be a first-class export in early phases or deferred until dataset scale requires it?
6. Is PyNite sufficiently validated and performant for the intended Tier 1 scope?
7. Is OpenSeesPy or XC the better advanced structural backend for deployment and support?
8. Are shell analyses necessary for the initial product or should they remain external?
9. How should proprietary timber, truss and fastener data be stored and versioned?
10. What company drafting template and detail library should define the first output style?
11. What minimum historical project set is representative enough for pilot validation?
12. What quantitative acceptance thresholds should apply to geometry, FEA and drawing review time?

## Decisions requiring Aaron's approval after Phase 1

- target architecture and migration strategy;
- initial project database packaging;
- Tier 1 and advanced FEA solver selections;
- initial supported building and structural scope;
- company drafting standard;
- first Australian Standards modules;
- benchmark projects and tolerances;
- cloud versus local processing policy;
- Phase 2 acceptance criteria.
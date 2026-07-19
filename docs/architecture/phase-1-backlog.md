# Phase 1 Backlog and Phase 2 Entry Gate

Status: Phase 1 documentation complete; implementation items are not authorised until Aaron approves the architecture

## Phase 1 completion checklist

- [x] current-state repository and function audit
- [x] technology options comparison
- [x] target architecture and dependency rules
- [x] neutral AnalysisModel and ResultSet definition
- [x] scored seven-solver comparison
- [x] tiered solver recommendation
- [x] legacy .dieselpdf.json migration strategy
- [x] test/verification plan including closed-form and SpaceGass comparison
- [x] risk register
- [x] decision log
- [x] engineering-input checklist
- [x] Phase 1 close-out code review and focused regression tests
- [x] bounded intersection snapping and atomic legacy-project saves
- [x] no Phase 2 production code or UI rewrite

## P0 — Aaron review required before Phase 2

| ID | Decision/input | Required evidence or answer | Blocks |
|---|---|---|---|
| P1-001 | code baseline | choose origin/agent/codex-project-handoff/main or the open interaction PR branch | all implementation |
| P1-002 | missing context | provide CODEX_HANDOFF.md and missing Project Bible chapters, or approve Phase 1 documents/Issue #2 as their replacement | durable handoff |
| P1-003 | initial building eligibility | confirm NSW Class 1/10, storeys, materials, roof/floor/footing systems and exclusions | domain scope |
| P1-004 | project coordinate convention | origin/datum policy, X/Y/Z convention, rotation, storey and level practice | Phase 2 |
| P1-005 | tolerance policy | native CAD, vector PDF, raster PDF, grid snap, node merge and round-trip tolerances | Phase 2 tests |
| P1-006 | legacy fixtures | provide representative .dieselpdf.json plus PDFs and expected screenshots/measurements | migration acceptance |
| P1-007 | review states/roles | define who proposes, reviews, approves, rejects and supersedes geometry/model/results/drawings | schema |
| P1-008 | PyMuPDF strategy | AGPL-compatible product or commercial Artifex licence | PDF packaging |
| P1-009 | DWG requirement | decide initial release need and ODA membership budget | DWG adapter |
| P1-010 | solver pilot | approve PyNite as a benchmark pilot, not pre-approved production engine | Phase 7 planning |
| P1-011 | SpaceGass benchmark suite | de-identified models, version/settings, result exports and tolerances | solver validation |
| P1-012 | advanced solver policy | approve research shortlist and GPL/commercial-licence constraints | later shell/nonlinear work |
| P1-013 | design-code editions | adopted NCC/AS editions, amendments, clause-access/licensing and office calculation conventions | Phase 8 |
| P1-014 | deployment targets | Windows/macOS versions, x64/Apple Silicon, offline requirements, installer/update expectations | packaging |
| P1-015 | preliminary/final issue policy | wording, placement, approval evidence and who may remove preliminary status | drawing workflow |
| P1-016 | data retention/privacy | source drawings, solver artefacts, audit events, backups and de-identification | persistence |

## Proposed Phase 2 backlog — coordinate and grid core

These items are planned only. Do not start until P0 approval.

| ID | Item | Acceptance evidence | Dependencies |
|---|---|---|---|
| P2-001 | establish package skeleton and dependency-direction test | domain imports no UI/vendor modules | P1-001 |
| P2-002 | implement strict Unit, Point and tolerance value objects | unit property tests and invalid-input rejection | P1-004/005 |
| P2-003 | implement CoordinateSystem and affine Transform schemas | forward/inverse/composition tests | P1-004 |
| P2-004 | implement PDF-page ↔ project calibration records | one-, two- and three-point fixtures with residual reporting | P2-003 |
| P2-005 | implement storeys and physical levels | split-level and roof/footing level tests | P1-003/004 |
| P2-006 | implement Grid and GridIntersection domain models | orthogonal/rotated/offset grid tests | P2-002/003 |
| P2-007 | implement centralized snapping/tolerance service | source-quality profiles and deterministic snapping tests | P1-005 |
| P2-008 | build ephemeral CanvasProjection map | stable entity ↔ Canvas selection without Canvas persistence | P2-002/003 |
| P2-009 | add legacy coordinate characterization tests | current branch and selected baseline reproduce expected positions | P1-001/006 |
| P2-010 | document Phase 2 ADRs and migration notes | Aaron-approved ADR-001 and test report | preceding items |

Phase 2 explicitly excludes the engineering dataset database implementation beyond interfaces, semantic extraction, structural topology, production FEA, Australian Standards checks and structural drawing generation.

## Future programme backlog

### Phase 3 — engineering dataset

- SQLite schema/migrations and R-Tree;
- UUID identity, revisions, audit events and review states;
- raw/semantic objects and relationships;
- cross-selection dataset UI;
- immutable legacy importer and reconciliation report.

### Phase 4 — PDF/CAD/IFC round trip

- versioned adapter contracts and capability manifests;
- exact curves, styles, clips, blocks, dimensions and layouts;
- stable IDs/XDATA/external handle matching;
- source hash and revision-diff reports;
- licensed DWG bridge if approved;
- golden round-trip drift suite.

### Phase 5 — architectural semantic extraction

- deterministic wall/opening/room/slab/roof/grid proposals;
- source-quality tolerance profiles;
- AI proposal records with provenance/confidence;
- overlay correction workflow and recognition metrics.

### Phase 6 — structural topology

- structural objects and connection/support semantics;
- load-path relationship graph;
- option generation and scoring;
- unsupported/ambiguous topology QA;
- engineer approval of topology before analysis.

### Phase 7 — deterministic analysis adapter

- freeze AnalysisModel/ResultSet schemas;
- PyNite pilot adapter and capability manifest;
- closed-form benchmark suite;
- SpaceGass comparison and discrepancy register;
- advanced Kratos/Code_Aster/OpenSeesPy spikes if authorised;
- solver subprocess isolation and reproducibility manifest.

### Phase 8 — Australian design-code layer

- approved edition/clauses register;
- deterministic actions/combinations;
- member/system checks by validated scope;
- calculation records, assumptions and clause traceability;
- independent hand-calculation regression suite.

### Phase 9 — structural drawing generation

- revisioned DrawingView, schedules, annotation and details;
- vector PDF and editable DXF/DWG;
- preliminary banner and issue-state enforcement;
- sheet coordination, scale and layer QA.

### Phase 10 — validation and engineering QA

- completed-project benchmark corpus;
- regression and correction capture;
- load-path, clash, stale-result and drawing QA;
- capability release gates and documented failure envelopes.

## Required engineering input in detail

### Geometry and drafting

- office origin/datum convention and preferred global axes;
- expected grids, labels, bubbles, offsets and multi-storey copying;
- drawing scales, sheet sizes, title-block practice and preliminary marking;
- acceptable geometric drift by source type;
- how to handle architect revisions, superseded sheets and split levels.

### Structural scope

- exact first-release building typologies and hard exclusions;
- permitted timber/steel/masonry/concrete systems;
- member releases, offsets, bearing assumptions and connection idealizations;
- load-path conventions and when manual topology is mandatory;
- footing/geotechnical prerequisites and Class P policy;
- whether first release requires P-Delta, modal or only linear static analysis.

### Actions and design

- adopted NCC and Australian Standards editions/amendments;
- office dead/live/wind action assumptions and load combinations;
- material/section libraries and proprietary product data policy;
- serviceability criteria, deflection limits and robustness rules;
- calculation template, rounding and clause-citation requirements.

### Validation

- SpaceGass version, solver settings and export format;
- at least one simple hand-check model per required element/analysis type;
- representative completed residential projects and known corrections;
- pre-approved numerical/result tolerances;
- reviewer names and sign-off evidence for each capability.

### Product and compliance

- commercial/open-source distribution intent;
- third-party licence and ODA budget;
- supported operating systems and offline/cloud policy;
- data retention, client confidentiality and de-identification rules;
- authority required to move from preliminary to final issue in a later phase.

## Definition of ready for Phase 2

Phase 2 is ready only when:

1. all P0 items are answered or explicitly deferred with a non-blocking rationale;
2. D-008 through D-022 are approved, amended or rejected;
3. R-001, R-002, R-003, R-004, R-018 and R-019 have accepted treatments;
4. a dedicated Phase 2 branch is named from the selected baseline;
5. legacy and coordinate fixtures are available;
6. Aaron explicitly authorises Phase 2.

Until then, stop at these Phase 1 review documents.

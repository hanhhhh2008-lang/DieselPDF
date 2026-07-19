# Phase 1 Target Architecture

Status: proposed for Aaron Han's approval
Scope: architecture only; this document does not implement Phase 2

## Architecture decision

DieselPDF will use a modular monolith with a ports-and-adapters boundary. The Diesel engineering dataset is the only source of truth. Tkinter Canvas, PDF, DXF, DWG, IFC, AI services and FEA solvers consume or propose changes through application services; none owns permanent geometry or engineering decisions.

~~~text
Tkinter UI now / replaceable UI later
        |
   commands + queries
        v
Application services and approval policies
        |
        v
Domain model: documents, geometry, architecture, structure,
relationships, actions, analysis, design, drawings and QA
        |
        v
Repositories + revision service
        |
        v
SQLite / R-Tree / immutable source artefacts

External adapters:
PDF | DXF | DWG | IFC | solver subprocesses | AI proposals | reports
~~~

## Non-negotiable dependency rules

1. domain modules import no Tkinter, PyMuPDF, ezdxf, IfcOpenShell or solver package;
2. UI sends commands and renders query results; it does not persist Canvas IDs as geometry;
3. adapters translate at boundaries and return typed results plus warnings;
4. persistence implements repository interfaces declared by the application/domain layer;
5. FEA adapters consume a frozen AnalysisModel revision and return a ResultSet;
6. Australian Standards modules consume neutral actions/results and never depend on a solver-native object;
7. AI output remains a Proposal until an auditable engineer approval command accepts it;
8. every export identifies the source dataset revision and approval state.

## Recommended repository structure

~~~text
dieselpdf/
  app/
    commands/
    queries/
    policies/
  domain/
    common/
    units/
    geometry/
    documents/
    architecture/
    structure/
    relationships/
    actions/
    analysis/
    design/
    drawings/
    qa/
  persistence/
    sqlite/
    migrations/
    repositories/
  adapters/
    pdf/
    dxf/
    dwg/
    ifc/
    fea/
    ai/
    reports/
  ui/
    tkinter/
  schemas/
  tests/
    unit/
    integration/
    contract/
    benchmarks/
    regression/
    golden/
~~~

The existing DieselPDF.pyw remains the composition root during the strangler migration, but new domain logic must enter these packages rather than enlarge the monolith.

## Canonical domain conventions

### Identity, revision and provenance

Every entity/object uses a stable UUID, schema_version, created_revision_id, current_revision_id and review_status. A revision records actor, timestamp, reason, parent revision and changed fields. Imported items additionally record:

- source_document_id and source_page_id;
- source_external_id/handle/GlobalId where available;
- source_method and adapter version;
- source file SHA-256;
- original page-local geometry;
- transform chain used to place it in project coordinates;
- confidence and review history.

Stable identity survives display changes and ordinary geometry edits. Split, merge and replacement operations create explicit lineage relationships.

### Geometry

Canonical project coordinates are millimetres, X right, Y up, Z up. Every coordinate tuple is associated with a coordinate_system_id. Preserve exact parameterization for lines, arcs, circles, ellipses, Bezier curves and splines. Derived tessellation records its chord/angle tolerance and is never substituted for the exact source.

Use typed geometry unions such as Point2D, LineSegment2D, Polyline2D, Polygon2D, Arc2D, Ellipse2D, Bezier2D, Spline2D and their 3D equivalents where justified. Units are not inferred from field names.

### Transforms

A Transform record contains:

~~~text
transform_id
schema_version
source_coordinate_system_id
target_coordinate_system_id
dimension
matrix
source_unit
target_unit
method
control_points
residuals
tolerance
provenance
review_status
revision_id
~~~

Transforms are composable and invertible where mathematically possible. Calibration retains both original page geometry and transform so recalibration is reversible.

### Raw and semantic separation

RawEntity records what was imported/drawn. SemanticObject attaches an architectural or engineering meaning to one or more entities. Typed Relationship records connect objects. A semantic object can be corrected without destroying its source evidence.

## Application services

Use explicit transactional commands:

- ImportSourceDocument
- CalibratePage
- CreateCoordinateSystem
- CreateOrUpdateGrid
- CreateRawEntity
- ProposeSemanticObject
- AcceptOrRejectProposal
- CreateStructuralObject
- ApproveStructuralTopology
- BuildAnalysisModel
- RunAnalysis
- RecordDesignCheck
- GenerateDrawingView
- ApprovePreliminaryIssue
- ExportRevision

Every command validates preconditions, writes one transaction, records an audit event and returns stable IDs plus QA warnings. Queries return immutable read models for Canvas and dataset panels.

## Persistence design

Use a .diesel.db SQLite file as the primary project store:

- normalized records for projects, documents, pages, coordinate systems, transforms, storeys, levels, grids, layers and styles;
- raw entities with discriminated geometry payloads and optional normalized vertices;
- semantic objects and object-entity links;
- typed relationships;
- actions, load cases, combinations, analysis-model snapshots and result manifests;
- design checks, drawing views, schedules and QA flags;
- revisions and append-only audit events;
- R-Tree tables for raw and semantic bounding boxes;
- content-addressed external artefacts for large immutable inputs/results, referenced by hash.

SQLite transactions protect domain changes. Migrations are forward-only and tested against fixtures. Opening a newer unsupported schema is read-only/fail-safe. Source files and analysis results are immutable once referenced by an approved revision.

## Neutral AnalysisModel

The neutral schema prevents application code from depending on PyNite, OpenSeesPy, Kratos or another backend. It is a frozen, hashable analysis input with SI-compatible dimensional metadata and full source traceability.

### Root

~~~yaml
analysis_model_id: UUID
schema_version: semver
project_id: UUID
source_revision_id: UUID
model_revision: integer
name: string
purpose: residential_frame | slab | wall | nonlinear | dynamic | other
dimension: 2D | 3D
coordinate_system_id: UUID
unit_system:
  length: mm
  force: N
  mass: kg
  time: s
gravity_vector: [gx, gy, gz]
assumptions: [Assumption]
nodes: [AnalysisNode]
materials: [Material]
sections: [Section]
elements: [AnalysisElement]
constraints: [Constraint]
supports: [Support]
springs: [Spring]
connections: [Connection]
load_cases: [LoadCase]
load_combinations: [LoadCombination]
analysis_cases: [AnalysisCase]
stages: [ConstructionStage]
requested_outputs: [OutputRequest]
validation_profile_id: UUID
provenance: Provenance
content_hash: sha256
review_status: draft | reviewed | approved_for_analysis | superseded
~~~

### Nodes and local axes

AnalysisNode contains stable node_id, project point [x,y,z], six-DOF declaration, optional mass/inertia, merge provenance, source object IDs and review status. Nodes are never merged solely by a solver tolerance; the model builder records each merge decision.

Every 1D/2D element has an explicit right-handed local-axis definition or orientation reference. Solver adapters must document and test their axis permutation and sign convention.

### Materials and sections

Material records a neutral category, density and only the mechanical properties needed by the requested analysis. Nonlinear behaviour uses a typed ConstitutiveModel with parameters, units, source/test reference and validity range. It does not store solver command strings.

Section preserves a geometric/material definition and separately stores derived A, Iy, Iz, J, shear areas and principal axes with calculation provenance. Solver-specific approximations are adapter settings, not changes to the section truth.

### Elements

AnalysisElement is a discriminated union:

- truss;
- frame/beam-column;
- cable/tension-only link;
- spring/link;
- plate;
- shell;
- membrane;
- solid, deferred until justified;
- rigid link/diaphragm constraint.

Common fields include element_id, node_ids, local_axis, formulation_intent, material_id, section_id or thickness, releases, offsets, activation stage, source_object_ids and result recovery requests. Formulation intent describes engineering behaviour; adapters map it to a validated solver formulation and report any unsupported or approximated field.

### Supports, springs and connections

Supports define restraint or prescribed displacement per DOF in the model coordinate system. Springs define stiffness/damping per DOF and may be two-way, tension-only, compression-only or nonlinear with an explicit law. Connections define releases, eccentricities, rigid zones and component links. Zero stiffness is not used as a synonym for release.

### Loads and combinations

A LoadCase identifies action category, source, application revision and self-weight policy. Typed loads include nodal, member point, member distributed, area/pressure, temperature, imposed displacement, acceleration and mass.

A LoadCombination is algebra only: case factors and combination purpose. Australian Standards rules that generate factors/combinations live in the separate design-code layer and record code edition/clauses. The neutral FEA model receives the approved combination set.

### Analysis cases

AnalysisCase declares:

- linear static;
- second-order/P-Delta;
- eigen/modal;
- response spectrum;
- transient dynamic;
- nonlinear static/pushover;
- nonlinear transient;
- buckling/eigenvalue;
- staged construction.

It also declares solver-neutral convergence tolerances, step/time controls, damping intent, geometric nonlinearity and result acceptance rules. Adapters reject unsupported cases rather than silently downgrading them.

### Stages and outputs

ConstructionStage describes ordered activation/deactivation of elements, supports, loads and initial state transfer. OutputRequest lists required displacements, reactions, element end forces, section forces/stresses, eigen data, convergence history and equilibrium checks.

### ResultSet

ResultSet stores:

~~~text
result_set_id
analysis_model_id
analysis_model_hash
adapter_name_and_version
solver_name_and_version
solver_binary_hash
platform
run_configuration
started_at / completed_at
status
warnings
convergence_history
nodal_results
element_results
modal_results
equilibrium_summary
energy_summary where applicable
raw_output_artifact_hashes
benchmark_profile
review_status
~~~

Solver-native files remain attached artefacts; neutral results used by design checks are normalized and sign-convention tested.

## Solver process boundary

Each solver runs in an isolated working directory through a SolverAdapter contract:

1. validate model support;
2. translate the frozen model;
3. write a manifest and hashes;
4. run with resource/time limits in a subprocess or container;
5. capture stdout, stderr, exit status and solver version;
6. parse results;
7. run equilibrium and completeness checks;
8. return ResultSet or a structured failure;
9. retain artefacts according to policy;
10. never write directly to the project database from the solver process.

The adapter contract supports multiple solvers and independent comparison without changing domain objects.

## Australian design-code boundary

Generic FEA produces actions, displacements and stresses. The Australian design-code layer:

- calculates actions and combinations under the approved project editions;
- performs member/system checks;
- cites inputs, assumptions, edition and clauses;
- consumes neutral ResultSet data;
- produces DesignCheck records with pass/fail/not-applicable/not-assessed;
- never relies on a solver's bundled foreign code-check module.

No check is approved merely because the solver converged.

## UI migration

Tkinter remains during migration:

1. introduce an EntityRepository and CanvasProjection map;
2. create new line/measurement entities through commands, then render them;
3. keep Canvas item ID ↔ stable entity ID only as ephemeral UI mapping;
4. query properties from domain read models;
5. convert selection/move/resize into commands in project coordinates;
6. migrate layers, text and polygons;
7. route imports/exports through adapters;
8. remove legacy Canvas serialization only after golden migration and regression tests pass.

The interaction PR's per-page scale and smoke tests should be retained if Aaron selects that branch, but page scale becomes a Transform rather than permanent geometry.

## Legacy migration and rollback

Use LegacyDieselJsonImporter described in the current-state audit. Migration always creates a new database and report; it never overwrites .dieselpdf.json. Deterministic IDs make reruns idempotent. A compatibility renderer compares legacy and dataset projections. If a blocking discrepancy occurs, the database is marked migration_failed and the original continues to open in legacy mode.

## Review and approval state machine

Minimum states:

~~~text
unreviewed → proposed → engineer_reviewed → approved
                    ↘ rejected
approved → superseded
~~~

Geometry, topology, AnalysisModel, ResultSet, DesignCheck and drawing issue each have separate approvals. Approval of one does not imply approval of the next. Critical unknowns block downstream gates.

Every generated drawing displays:

PRELIMINARY — NOT FOR CONSTRUCTION — ENGINEER REVIEW REQUIRED

until an explicitly designed final-issue gate is approved in a later phase.

## Verification architecture

### Geometry and adapters

- property-based transform/inverse tests;
- tolerance and degeneracy tests;
- golden PDF/DXF/IFC files;
- object, style, identity and coordinate reconciliation;
- repeated round-trip drift budgets;
- fuzz and malicious-file tests in isolated processes.

### Analysis

- hand/closed-form beams, trusses, springs, frames, plates and modal cases;
- patch tests and rigid-body/zero-energy checks where applicable;
- equilibrium, symmetry and unit-scaling invariants;
- mesh-convergence studies for 2D elements;
- solver-to-solver comparison for selected neutral models;
- approved SpaceGass comparison suite;
- locked solver/version/binary hashes and tolerances.

### Engineering workflow

- no analysis on an unapproved model revision;
- no design check against stale results;
- no drawing export without preliminary marking;
- reproducible audit report from source hash to sheet;
- explicit failure for missing/unsupported solver features.

## Phase 2 entry gates

No Phase 2 work begins until Aaron approves or resolves:

- implementation baseline branch;
- project coordinate and tolerance conventions;
- legacy fixture set and migration acceptance criteria;
- initial residential structural scope and exclusions;
- schema/review-state vocabulary;
- PyMuPDF, ODA and solver licence strategy;
- initial solver pilot and benchmark suite;
- current Australian Standards editions and permitted citation/content approach;
- Windows/macOS deployment targets;
- SpaceGass reference projects and comparison tolerances.

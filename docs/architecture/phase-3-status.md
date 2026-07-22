# Phase 3 — Engineering Dataset and Persistence Status

Status: implementation complete on `agent/phase-3-engineering-dataset`; stacked Draft PR and real-project migration pilot required before Phase 4

Date: 22 July 2026

## Completion audit

| Project Bible deliverable | Evidence |
|---|---|
| Pydantic domain schemas | Strict project, document, page, actor, revision, raw geometry, semantic object, relationship, review decision and audit-event models under `dieselpdf/domain/dataset` |
| SQLite database and migrations | Versioned migration runner and schema under `dieselpdf/persistence`; foreign keys, WAL and full synchronous writes enabled |
| R-Tree spatial indexing | `entity_rtree`, insert trigger, current-version spatial query and intersection/non-intersection tests |
| Stable IDs | UUID4 creation, deterministic UUID5 import identity, validation and type/project immutability tests |
| Revisions | Linear project revisions plus immutable entity, semantic-object and relationship version tables |
| Relationships | Typed durable relationships with endpoint existence checks |
| Dataset table and cross-selection | `DatasetTable`, `DatasetCanvasRenderer`, shared `CanvasProjectionMap` and end-to-end `EngineeringDatasetWindow` test |
| Legacy `.dieselpdf.json` importer | Immutable SHA-256-based importer, one entity per Canvas object, raw payload retention, explicit unmapped-field report and original-file hash verification |
| JSONL export/import | Atomic deterministic exchange preserving versions, approvals, audit events, import evidence and ID maps |

## Approval and audit controls

- AI and system actors cannot create engineer approval or rejection decisions.
- Engineer approval requires the engineer role plus explicit approval authority.
- A review action atomically appends the project revision, item version and
  decision; a rejected transition adds none of them.
- Revisions, versions, decisions, audit events, source documents/pages and
  import runs are protected by SQLite append-only triggers.
- Source-document and page references must resolve within the same project.

## Phase 3 gate

Project Bible gate: Canvas renders selected object classes from database
ownership, and old projects migrate without silent data loss.

Evidence:

- the dataset window renders database-owned point/line/polyline/polygon,
  rectangle, circle/ellipse, text and unresolved fallback records;
- selecting a dataset row highlights its Canvas projection;
- selecting a Canvas item selects the stable dataset record;
- the committed legacy fixture migrates 5 of 5 Canvas objects;
- unknown fields and unsupported object types are reported and retained;
- a JSONL round trip reproduces current records, revision history, engineer
  approval, source records and migration evidence;
- database integrity returns `ok` after migration and exchange.

## Validation baseline

- complete repository unittest suite under the local Tk display;
- legacy interaction/PDF smoke workflow: `dieselpdf-smoke-ok`;
- compileall for application, packages and tests;
- `git diff --check`;
- GitHub Actions configured for Phase 3 core on Windows, macOS and Linux plus
  the full UI/regression suite under Xvfb.

## Explicit Phase 4 exclusions

Phase 3 does not implement production PDF/DXF/DWG/IFC round trips, conflict-aware
re-import, semantic recognition, load paths, FEA, Australian Standards checks
or structural drawing generation.

## Required real-project pilot

No real client `.dieselpdf.json` project was found in this repository or the
local Documents tree. The synthetic fixture matches the current serializer and
proves object-count reconciliation, deterministic identity, raw-evidence
retention and the review gate. Before Phase 4 relies on migrated production
data, Aaron should run at least one representative real project through the
importer and review the generated report and geometry projection.

# DieselPDF Codex Engineering Instructions

## Mission

Develop DieselPDF into an engineer-in-the-loop platform that accepts architectural PDF, DXF, DWG or IFC inputs and progressively generates coordinated preliminary structural drawings, finite-element analysis data, Australian Standards design checks and automated QA outputs.

The engineering owner and final reviewer is Aaron Han, a NSW structural, forensic and remedial engineer.

## Current authorised scope

Phase 1 is complete on Draft PR #4. Phase 2 is complete on Draft PR #6. Aaron expressly authorised Phase 3 on 24 July 2026.

Phase 3 contains:

- Pydantic engineering dataset schemas;
- stable IDs, review states, revisions and audit events;
- SQLite migrations and R-Tree spatial indexing;
- Project Bundle packaging;
- raw entities, semantic objects, links and relationships;
- JSONL exchange;
- immutable legacy `.dieselpdf.json` import and reconciliation;
- database-owned Canvas rendering, dataset table and cross-selection.

Do not begin Phase 4 PDF/DXF/DWG/IFC production round trip, semantic recognition, structural topology, FEA, Australian Standards design checks or drawing generation without Aaron's next approval. Do not rewrite the Tkinter UI or modify `main` directly.

## Non-negotiable architecture rules

1. The Diesel engineering dataset is the single source of truth.
2. Tkinter Canvas, PDF, DXF, DWG, IFC and FEA models are adapters or views around that dataset.
3. Permanent geometry is stored in project coordinates, millimetres with X right, Y up and Z up.
4. Every durable entity and object has a stable UUID, provenance, schema version, revision and review status.
5. Raw extracted geometry and engineering semantic objects remain separate but linked.
6. AI output remains a proposal until role-authorised review and approval.
7. Generic FEA and Australian Standards design checks remain separate deterministic layers.
8. All writes use atomic revisions and auditable actors/reasons.
9. Existing `.dieselpdf.json` projects are immutable migration sources and unsupported data must be preserved losslessly.
10. All generated drawings remain `PRELIMINARY — NOT FOR CONSTRUCTION — ENGINEER REVIEW REQUIRED` until Aaron approves final issue.

## Engineering basis

Use current project-adopted Australian Standards and NCC requirements. Future modules may include AS/NZS 1170, AS 4055, AS 1684.2, AS 1720.1, AS 2870, AS 3600, AS 4100, AS 3700, current AS 4773 provisions, AS/NZS 4600 and AS/NZS 1664 as applicable.

Do not claim equivalence to SpaceGass or ETABS without documented benchmark evidence.

## Phase 3 completion gate

Phase 3 is implementation-complete when:

- all migrations and checksum tests pass;
- R-Tree and exact dataset queries pass;
- revision rollback and audit tests pass;
- database-owned Canvas render and cross-selection tests pass;
- JSONL stable-ID round trip passes;
- legacy import reconciles every source object without source modification;
- dependency-direction tests and complete repository CI pass;
- ADR-002, ADR-003, migration notes and status report are present.

Keep the Phase 3 PR in review state. Phase 4 remains blocked pending explicit approval and format/licensing decisions.
